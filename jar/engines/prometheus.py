"""
Custom Prometheus Query Engine for LlamaIndex.
Translates natural language queries to PromQL and executes them.
"""
from typing import Any, Optional
from llama_index.core.query_engine import CustomQueryEngine
from llama_index.core import PromptTemplate
from llama_index.core.llms.llm import BaseLLM
import requests
import json
import os
from datetime import datetime, timedelta
from jar.engines.utils import parse_llm_json_response


PROMQL_GENERATION_PROMPT = PromptTemplate(
    "You are an expert in Prometheus and PromQL.\n"
    "Given a natural language query about metrics, generate the appropriate PromQL query.\n"
    "Available metrics in our system:\n"
    "- CPU usage: node_cpu_usage (gauge showing CPU percentage per instance)\n"
    "- Memory usage: node_memory_usage (gauge showing memory percentage per instance)\n"
    "- Request rate: http_requests_total (counter)\n"
    "- Error rate: http_errors_total (counter)\n"
    "- Response time: http_request_duration_seconds (gauge)\n\n"
    "Each metric has these labels: instance (service name), environment\n"
    "Query: {query_str}\n\n"
    "For queries about multiple applications/services, return the metric WITHOUT filters to get all instances.\n"
    "For queries about a specific service, add instance filter like: node_cpu_usage{{instance=\"user-service\"}}\n\n"
    "Also extract the time window if mentioned (e.g., 'last 30 minutes', 'right now', 'past hour').\n"
    "Respond ONLY with valid JSON using DOUBLE QUOTES:\n"
    "{{\n"
    "  \"promql\": \"<your PromQL query>\",\n"
    "  \"time_window\": \"<time window in minutes or 'current'>\",\n"
    "  \"metric_type\": \"<cpu|memory|requests|errors|latency>\"\n"
    "}}\n\n"
    "Response:"
)


class PrometheusQueryEngine(CustomQueryEngine):
    """Custom query engine for Prometheus metrics."""

    llm: BaseLLM
    prometheus_url: str = ""
    progress_callback: Any = None

    def __init__(self, llm: BaseLLM, prometheus_url: Optional[str] = None, progress_callback: Any = None, **kwargs):
        """
        Initialize Prometheus query engine.

        Args:
            llm: LLM instance (OpenAI, Ollama, or any LlamaIndex-compatible LLM)
            prometheus_url: URL of Prometheus server (default: http://localhost:9090 or env PROMETHEUS_URL)
            progress_callback: Optional callback for progress updates
        """
        if prometheus_url is None:
            prometheus_url = os.getenv('PROMETHEUS_URL', 'http://localhost:9090')

        super().__init__(llm=llm, prometheus_url=prometheus_url, progress_callback=progress_callback, **kwargs)

        # Test Prometheus connection
        try:
            response = requests.get(f"{prometheus_url}/api/v1/status/config", timeout=5)
            if response.status_code == 200:
                print(f"Connected to Prometheus at {prometheus_url}")
            else:
                raise ConnectionError(f"Prometheus returned status {response.status_code}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Prometheus at {prometheus_url}: {e}")
    
    def _emit_progress(self, step: str, message: str, reasoning: str = ""):
        """Emit progress update if callback is provided."""
        if self.progress_callback:
            self.progress_callback({
                'step': step,
                'message': message,
                'source': 'prometheus',
                'reasoning': reasoning
            })

    def custom_query(self, query_str: str) -> Any:
        """Execute a query against Prometheus."""

        self._emit_progress('query_start', 'Querying Prometheus metrics...',
                           'Translating natural language to PromQL')

        # Step 1: Generate PromQL from natural language
        prompt = PROMQL_GENERATION_PROMPT.format(query_str=query_str)
        response = self.llm.complete(prompt)

        self._emit_progress('promql_generated', 'Generated PromQL query',
                           'Received PromQL from language model')
        
        try:
            # Parse the LLM response
            response_text = parse_llm_json_response(response.text)
            query_info = json.loads(response_text)
            promql = query_info.get('promql', '')
            time_window = query_info.get('time_window', 'current')
            metric_type = query_info.get('metric_type', 'unknown')
            
        except (json.JSONDecodeError, ValueError, KeyError, AttributeError) as e:
            # Fallback if parsing fails - log the error for debugging
            print(f"Warning: Failed to parse PromQL generation response: {e}")
            print(f"Raw LLM response: {response_text[:200]}...")
            # Return error instead of misleading fallback data
            return {
                'query': query_str,
                'promql': 'PARSE_ERROR',
                'time_window': 'current',
                'metric_type': 'error',
                'results': {
                    'metric': 'parse_error',
                    'value': 0,
                    'unit': '',
                    'timestamp': datetime.now().isoformat(),
                    'error': f'Failed to parse LLM response: {e}'
                },
                'summary': f'Error: Could not generate valid PromQL query. {e}'
            }
        
        # Step 2: Execute the PromQL query
        self._emit_progress('executing_query', f'Executing PromQL: {promql[:50]}...',
                           'Querying Prometheus API')
        results = self._query_prometheus_api(promql, time_window)

        self._emit_progress('query_complete', 'Prometheus query complete',
                           'Successfully retrieved metrics data')

        # Step 3: Format results for the agent
        return {
            'query': query_str,
            'promql': promql,
            'time_window': time_window,
            'metric_type': metric_type,
            'results': results,
            'summary': self._generate_summary(results, metric_type)
        }
    
    def _query_prometheus_api(self, promql: str, time_window: str) -> dict:
        """Query actual Prometheus API using HTTP requests."""
        try:
            # Build the query URL
            url = f"{self.prometheus_url}/api/v1/query"
            params = {"query": promql}
            
            # Add time parameter if it's a range query
            if time_window != 'current':
                # For instant queries, we use the current time
                pass
            
            # Make the request
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") != "success":
                error_msg = data.get("error", "Unknown error")
                print(f"Warning: Prometheus query failed: {error_msg}")
                return {
                    'metric': 'error',
                    'value': 0,
                    'unit': '',
                    'timestamp': datetime.now().isoformat(),
                    'error': error_msg
                }
            
            results = data.get("data", {}).get("result", [])
            
            if not results:
                return {
                    'metric': 'no_data',
                    'value': 0,
                    'unit': '',
                    'timestamp': datetime.now().isoformat(),
                    'error': 'No data returned from Prometheus',
                    'all_results': []
                }
            
            # Parse ALL results (multiple applications/instances)
            all_metrics = []
            for metric_data in results:
                metric_labels = metric_data.get('metric', {})
                metric_name = metric_labels.get('__name__', 'unknown')
                value_data = metric_data.get('value', [None, '0'])
                
                # value_data is [timestamp, value]
                timestamp = datetime.fromtimestamp(float(value_data[0])) if value_data[0] else datetime.now()
                value = float(value_data[1]) if len(value_data) > 1 else 0.0
                
                instance = metric_labels.get('instance', 'unknown')
                
                all_metrics.append({
                    'metric': metric_name,
                    'value': value,
                    'instance': instance,
                    'timestamp': timestamp.isoformat(),
                    'labels': metric_labels
                })
            
            # Use the first metric for compatibility with existing code
            first_metric = all_metrics[0]
            metric_name = first_metric['metric']
            
            # Determine unit from metric name
            unit = ''
            if 'percent' in metric_name or 'usage' in metric_name:
                unit = '%'
            elif 'bytes' in metric_name:
                unit = 'B'
            elif 'seconds' in metric_name:
                unit = 's'
            elif 'total' in metric_name:
                unit = 'count'
            
            return {
                'metric': metric_name,
                'value': first_metric['value'],
                'unit': unit,
                'timestamp': first_metric['timestamp'],
                'labels': first_metric['labels'],
                'promql': promql,
                'all_results': all_metrics
            }
            
        except requests.RequestException as e:
            print(f"Warning: Error querying Prometheus API: {e}")
            return {
                'metric': 'error',
                'value': 0,
                'unit': '',
                'timestamp': datetime.now().isoformat(),
                'error': f'Request failed: {str(e)}'
            }
        except (ValueError, KeyError, IndexError) as e:
            print(f"Warning: Error parsing Prometheus response: {e}")
            return {
                'metric': 'error',
                'value': 0,
                'unit': '',
                'timestamp': datetime.now().isoformat(),
                'error': f'Parse error: {str(e)}'
            }
    
    def _generate_summary(self, results: dict, metric_type: str) -> str:
        """Generate a human-readable summary of the results."""
        
        metric = results.get('metric', 'unknown')
        value = results.get('value', 0)
        unit = results.get('unit', '')
        all_results = results.get('all_results', [])
        
        # If we have multiple applications, provide a comprehensive summary
        if len(all_results) > 1:
            summary_lines = []
            
            if metric_type == 'cpu':
                summary_lines.append(f"CPU usage across {len(all_results)} applications:")
                for app in all_results:
                    instance = app['instance']
                    app_value = app['value']
                    status = "🚨 HIGH" if app_value > 80 else "⚠️ MODERATE" if app_value > 60 else "✓ NORMAL"
                    summary_lines.append(f"  - {instance}: {app_value:.1f}{unit} ({status})")
                return "\n".join(summary_lines)
            
            elif metric_type == 'memory':
                summary_lines.append(f"Memory usage across {len(all_results)} applications:")
                for app in all_results:
                    instance = app['instance']
                    app_value = app['value']
                    status = "🚨 HIGH" if app_value > 85 else "⚠️ MODERATE" if app_value > 70 else "✓ NORMAL"
                    summary_lines.append(f"  - {instance}: {app_value:.1f}{unit} ({status})")
                return "\n".join(summary_lines)
            
            elif metric_type == 'latency':
                summary_lines.append(f"Response times across {len(all_results)} applications:")
                for app in all_results:
                    instance = app['instance']
                    app_value = app['value']
                    status = "🚨 HIGH" if app_value > 500 else "⚠️ MODERATE" if app_value > 300 else "✓ GOOD"
                    summary_lines.append(f"  - {instance}: {app_value:.1f}{unit} ({status})")
                return "\n".join(summary_lines)
            
            else:
                summary_lines.append(f"{metric} across {len(all_results)} applications:")
                for app in all_results:
                    instance = app['instance']
                    app_value = app['value']
                    summary_lines.append(f"  - {instance}: {app_value:.1f}{unit}")
                return "\n".join(summary_lines)
        
        # Single result summary (original logic)
        if metric_type == 'cpu':
            if value > 80:
                return f"High CPU usage detected: {value:.1f}{unit}"
            elif value > 60:
                return f"CPU usage is moderate: {value:.1f}{unit}"
            else:
                return f"CPU usage is normal: {value:.1f}{unit}"
        
        elif metric_type == 'memory':
            if value > 85:
                return f"High memory usage detected: {value:.1f}{unit}"
            elif value > 70:
                return f"Memory usage is moderate: {value:.1f}{unit}"
            else:
                return f"Memory usage is normal: {value:.1f}{unit}"
        
        elif metric_type == 'errors':
            error_count = int(value)
            if error_count > 20:
                error_details = results.get('recent_errors', [])
                error_breakdown = ", ".join([f"{e['code']} ({e['count']})" for e in error_details])
                return f"{error_count} errors detected. Breakdown: {error_breakdown}"
            elif error_count > 0:
                return f"Minor errors detected: {error_count} total"
            else:
                return f"No errors detected"
        
        elif metric_type == 'latency':
            if value > 500:
                return f"High response time: {value:.1f}{unit}"
            elif value > 300:
                return f"Response time is acceptable: {value:.1f}{unit}"
            else:
                return f"Response time is good: {value:.1f}{unit}"
        
        else:
            return f"Metric {metric}: {value}{unit}"
