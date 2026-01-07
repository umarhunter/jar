"""
Custom Prometheus Query Engine for LlamaIndex.
Translates natural language queries to PromQL and executes them.
"""
from typing import Any, Optional
from llama_index.core.query_engine import CustomQueryEngine
from llama_index.core.prompts import PromptTemplate
from llama_index.llms.openai import OpenAI
import json
import random
from datetime import datetime, timedelta


PROMQL_GENERATION_PROMPT = PromptTemplate(
    "You are an expert in Prometheus and PromQL.\n"
    "Given a natural language query about metrics, generate the appropriate PromQL query.\n"
    "Focus on these metric types:\n"
    "- CPU usage: cpu_usage_percent, node_cpu_seconds_total\n"
    "- Memory usage: memory_usage_percent, node_memory_MemAvailable_bytes\n"
    "- Request rate: http_requests_total, request_rate\n"
    "- Error rate: http_errors_total, error_rate\n"
    "- Response time: http_request_duration_seconds, response_time_ms\n\n"
    "Query: {query_str}\n\n"
    "Also extract the time window if mentioned (e.g., 'last 30 minutes', 'right now', 'past hour').\n"
    "Respond in JSON format with:\n"
    "{{\n"
    "  'promql': '<your PromQL query>',\n"
    "  'time_window': '<time window in minutes or 'current'>',\n"
    "  'metric_type': '<cpu|memory|requests|errors|latency>'\n"
    "}}\n\n"
    "Response:"
)


class PrometheusQueryEngine(CustomQueryEngine):
    """Custom query engine for Prometheus metrics."""
    
    llm: OpenAI
    mock_mode: bool = True  # For pilot, use mock data
    
    def __init__(self, llm: OpenAI, mock_mode: bool = True, **kwargs):
        super().__init__(llm=llm, mock_mode=mock_mode, **kwargs)
    
    def custom_query(self, query_str: str) -> Any:
        """Execute a query against Prometheus."""
        
        # Step 1: Generate PromQL from natural language
        prompt = PROMQL_GENERATION_PROMPT.format(query_str=query_str)
        response = self.llm.complete(prompt)
        
        try:
            # Parse the LLM response
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif response_text.startswith("```"):
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            query_info = json.loads(response_text)
            promql = query_info.get('promql', '')
            time_window = query_info.get('time_window', 'current')
            metric_type = query_info.get('metric_type', 'unknown')
            
        except (json.JSONDecodeError, ValueError, KeyError, AttributeError) as e:
            # Fallback if parsing fails
            promql = "up{}"
            time_window = 'current'
            metric_type = 'unknown'
        
        # Step 2: Execute the PromQL query (mock for pilot)
        if self.mock_mode:
            results = self._mock_prometheus_query(promql, metric_type, time_window)
        else:
            # Would call actual Prometheus API here
            results = self._query_prometheus_api(promql, time_window)
        
        # Step 3: Format results for the agent
        return {
            'query': query_str,
            'promql': promql,
            'time_window': time_window,
            'metric_type': metric_type,
            'results': results,
            'summary': self._generate_summary(results, metric_type)
        }
    
    def _mock_prometheus_query(self, promql: str, metric_type: str, time_window: str) -> dict:
        """Generate mock Prometheus data for pilot phase."""
        
        timestamp = datetime.now()
        
        if metric_type == 'cpu':
            return {
                'metric': 'cpu_usage_percent',
                'value': random.uniform(45.0, 85.0),
                'unit': '%',
                'timestamp': timestamp.isoformat()
            }
        elif metric_type == 'memory':
            return {
                'metric': 'memory_usage_percent',
                'value': random.uniform(60.0, 90.0),
                'unit': '%',
                'timestamp': timestamp.isoformat()
            }
        elif metric_type == 'requests':
            return {
                'metric': 'request_rate',
                'value': random.uniform(100.0, 500.0),
                'unit': 'req/s',
                'timestamp': timestamp.isoformat()
            }
        elif metric_type == 'errors':
            error_count = random.randint(0, 50)
            return {
                'metric': 'error_count',
                'value': error_count,
                'unit': 'errors',
                'timestamp': timestamp.isoformat(),
                'recent_errors': [
                    {'code': '401', 'count': error_count // 3, 'message': 'Unauthorized'},
                    {'code': '500', 'count': error_count // 3, 'message': 'Internal Server Error'},
                    {'code': '503', 'count': error_count // 3, 'message': 'Service Unavailable'}
                ] if error_count > 10 else []
            }
        elif metric_type == 'latency':
            return {
                'metric': 'response_time',
                'value': random.uniform(50.0, 600.0),
                'unit': 'ms',
                'timestamp': timestamp.isoformat()
            }
        else:
            return {
                'metric': 'general',
                'value': 1.0,
                'unit': '',
                'timestamp': timestamp.isoformat()
            }
    
    def _query_prometheus_api(self, promql: str, time_window: str) -> dict:
        """Query actual Prometheus API (not implemented in pilot)."""
        raise NotImplementedError("Actual Prometheus API integration not implemented in pilot phase")
    
    def _generate_summary(self, results: dict, metric_type: str) -> str:
        """Generate a human-readable summary of the results."""
        
        metric = results.get('metric', 'unknown')
        value = results.get('value', 0)
        unit = results.get('unit', '')
        
        if metric_type == 'cpu':
            if value > 80:
                return f"⚠️ High CPU usage detected: {value:.1f}{unit}"
            elif value > 60:
                return f"CPU usage is moderate: {value:.1f}{unit}"
            else:
                return f"✅ CPU usage is normal: {value:.1f}{unit}"
        
        elif metric_type == 'memory':
            if value > 85:
                return f"⚠️ High memory usage detected: {value:.1f}{unit}"
            elif value > 70:
                return f"Memory usage is moderate: {value:.1f}{unit}"
            else:
                return f"✅ Memory usage is normal: {value:.1f}{unit}"
        
        elif metric_type == 'errors':
            error_count = int(value)
            if error_count > 20:
                error_details = results.get('recent_errors', [])
                error_breakdown = ", ".join([f"{e['code']} ({e['count']})" for e in error_details])
                return f"⚠️ {error_count} errors detected. Breakdown: {error_breakdown}"
            elif error_count > 0:
                return f"Minor errors detected: {error_count} total"
            else:
                return f"✅ No errors detected"
        
        elif metric_type == 'latency':
            if value > 500:
                return f"⚠️ High response time: {value:.1f}{unit}"
            elif value > 300:
                return f"Response time is acceptable: {value:.1f}{unit}"
            else:
                return f"✅ Response time is good: {value:.1f}{unit}"
        
        else:
            return f"Metric {metric}: {value}{unit}"
