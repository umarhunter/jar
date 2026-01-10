"""
Custom Elasticsearch Query Engine for LlamaIndex.
Translates natural language queries to Elasticsearch DSL and executes them.
"""
from typing import Any, Optional, List, Dict
from llama_index.core.query_engine import CustomQueryEngine
from llama_index.core.prompts import PromptTemplate
from llama_index.core.llms.llm import BaseLLM
import requests
import json
import os
from datetime import datetime, timedelta
from jar.engines.utils import parse_llm_json_response


ELASTICSEARCH_QUERY_PROMPT = PromptTemplate(
    "You are an expert in Elasticsearch and its Query DSL.\n"
    "Given a natural language query about application logs and errors, generate the appropriate Elasticsearch query.\n"
    "Focus on these query types:\n"
    "- Error logs: severity=error, level=ERROR\n"
    "- Application logs: filter by application name\n"
    "- Time-based queries: timestamp ranges\n"
    "- Log level filtering: INFO, WARN, ERROR, FATAL\n"
    "- Error traces and stack traces\n"
    "- Specific error messages or patterns\n\n"
    "Query: {query_str}\n\n"
    "Extract:\n"
    "- Time window: Convert to minutes. Examples:\n"
    "  * 'last 30 minutes' or 'past hour' -> number of minutes\n"
    "  * 'last 24 hours' or 'today' -> 1440\n"
    "  * 'last 7 days' or 'past week' -> 10080\n"
    "  * 'last 30 days' or 'past month' -> 43200\n"
    "  * 'all time' or no time mentioned -> 'all'\n"
    "- Log level filter (INFO, WARN, ERROR, FATAL)\n"
    "- Application name if mentioned (match: payment-gateway, user-service, notification-service, analytics-engine)\n"
    "- Search terms or error patterns\n\n"
    "Respond ONLY with valid JSON using DOUBLE QUOTES:\n"
    "{{\n"
    "  \"query_type\": \"<errors|logs|traces>\",\n"
    "  \"time_window\": \"<number of minutes as integer or 'all'>\",\n"
    "  \"log_level\": \"<INFO|WARN|ERROR|FATAL|ALL>\",\n"
    "  \"application\": \"<exact application name or 'all'>\",\n"
    "  \"search_terms\": [\"<term1>\", \"<term2>\"]\n"
    "}}\n\n"
    "Response:"
)


class ElasticsearchQueryEngine(CustomQueryEngine):
    """Custom query engine for Elasticsearch logs and traces."""

    llm: BaseLLM
    elasticsearch_host: str = ""
    index_pattern: str = "application_logs"
    progress_callback: Any = None

    def __init__(self, llm: BaseLLM,
                 elasticsearch_host: Optional[str] = None,
                 index_pattern: str = "application_logs",
                 progress_callback: Any = None, **kwargs):
        """
        Initialize Elasticsearch query engine.

        Args:
            llm: LLM instance (OpenAI, Ollama, or any LlamaIndex-compatible LLM)
            elasticsearch_host: Elasticsearch host (default: http://localhost:9200 or env ELASTICSEARCH_HOST)
            index_pattern: Index pattern to search (default: logs-*)
            progress_callback: Optional callback for progress updates
        """
        if elasticsearch_host is None:
            elasticsearch_host = os.getenv('ELASTICSEARCH_HOST', 'http://localhost:9200')

        super().__init__(llm=llm, elasticsearch_host=elasticsearch_host, index_pattern=index_pattern, progress_callback=progress_callback, **kwargs)

        # Test Elasticsearch connection
        try:
            response = requests.get(f"{elasticsearch_host}/_cluster/health", timeout=5)
            if response.status_code == 200:
                print(f"Connected to Elasticsearch at {elasticsearch_host}")
            else:
                raise ConnectionError(f"Elasticsearch returned status {response.status_code}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Elasticsearch at {elasticsearch_host}: {e}")

    def _emit_progress(self, step: str, message: str, reasoning: str = ""):
        """Emit progress update if callback is provided."""
        if self.progress_callback:
            self.progress_callback({
                'step': step,
                'message': message,
                'source': 'elasticsearch',
                'reasoning': reasoning
            })

    def custom_query(self, query_str: str) -> Any:
        """Execute a query against Elasticsearch."""

        self._emit_progress('query_start', 'Querying Elasticsearch logs...',
                           'Analyzing query and building Elasticsearch DSL')

        # Step 1: Parse natural language to Elasticsearch query parameters
        prompt = ELASTICSEARCH_QUERY_PROMPT.format(query_str=query_str)
        response = self.llm.complete(prompt)

        self._emit_progress('query_parsed', 'Query parameters extracted',
                           'Built Elasticsearch query structure')

        try:
            # Parse the LLM response
            response_text = parse_llm_json_response(response.text)
            query_info = json.loads(response_text)
            query_type = query_info.get('query_type', 'logs')
            time_window = query_info.get('time_window', '60')
            log_level = query_info.get('log_level', 'ALL')
            application = query_info.get('application', 'all')
            search_terms = query_info.get('search_terms', [])

        except (json.JSONDecodeError, ValueError, KeyError, AttributeError) as e:
            # Fallback if parsing fails
            print(f"Warning: Failed to parse Elasticsearch query response: {e}")
            print(f"Raw response: {response.text[:200]}")
            # Smart defaults based on query keywords
            query_type = 'errors' if 'error' in query_str.lower() else 'logs'
            
            # Try to extract time from query
            if '30 day' in query_str.lower() or 'month' in query_str.lower():
                time_window = '43200'  # 30 days
            elif '7 day' in query_str.lower() or 'week' in query_str.lower():
                time_window = '10080'  # 7 days
            elif '24 hour' in query_str.lower() or 'today' in query_str.lower() or 'day' in query_str.lower():
                time_window = '1440'  # 24 hours
            else:
                time_window = '60'
            
            log_level = 'ERROR' if 'error' in query_str.lower() else 'ALL'
            
            # Try to extract application name
            if 'payment' in query_str.lower():
                application = 'payment-gateway'
            elif 'user' in query_str.lower():
                application = 'user-service'
            elif 'notification' in query_str.lower():
                application = 'notification-service'
            elif 'analytics' in query_str.lower():
                application = 'analytics-engine'
            else:
                application = 'all'
            
            search_terms = []

        # Step 2: Execute the Elasticsearch query
        self._emit_progress('executing_query', f'Searching {log_level} logs...',
                           f'Querying Elasticsearch for {query_type}')
        results = self._query_elasticsearch_api(
            query_type, time_window, log_level, application, search_terms
        )

        self._emit_progress('query_complete', 'Elasticsearch query complete',
                           f'Found {results.get("total_logs", 0)} log entries')

        # Step 3: Format results for the agent
        return {
            'query': query_str,
            'query_type': query_type,
            'time_window': time_window,
            'log_level': log_level,
            'application': application,
            'results': results,
            'summary': self._generate_summary(results, query_type, log_level)
        }

    def _query_elasticsearch_api(
        self,
        query_type: str,
        time_window: str,
        log_level: str,
        application: str,
        search_terms: List[str]
    ) -> Dict:
        """Query actual Elasticsearch API using HTTP requests."""
        try:
            # Build Elasticsearch query
            query_body = {
                "size": 100,
                "query": {
                    "bool": {
                        "must": [],
                        "filter": []
                    }
                },
                "sort": [{"@timestamp": {"order": "desc"}}]
            }

            # Add time range filter
            if time_window and time_window != 'all':
                try:
                    minutes = int(time_window)
                    query_body["query"]["bool"]["filter"].append({
                        "range": {
                            "@timestamp": {
                                "gte": f"now-{minutes}m",
                                "lte": "now"
                            }
                        }
                    })
                except ValueError:
                    pass

            # Add log level filter
            if log_level and log_level != 'ALL':
                query_body["query"]["bool"]["must"].append({
                    "match": {"level": log_level}
                })

            # Add application filter
            if application and application != 'all':
                query_body["query"]["bool"]["must"].append({
                    "match": {"application": application}
                })

            # Add search terms
            if search_terms:
                for term in search_terms:
                    query_body["query"]["bool"]["must"].append({
                        "multi_match": {
                            "query": term,
                            "fields": ["message", "error.message", "error.type"]
                        }
                    })

            # Execute search via HTTP API
            url = f"{self.elasticsearch_host}/{self.index_pattern}/_search"
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=query_body, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()

            # Parse results
            hits = data.get('hits', {}).get('hits', [])
            total_logs = data.get('hits', {}).get('total', {}).get('value', 0)

            # Aggregate log levels
            log_counts = {"ERROR": 0, "WARN": 0, "INFO": 0}
            recent_errors = []
            applications_affected = set()

            for hit in hits:
                source = hit.get('_source', {})
                level = source.get('level', 'INFO')
                log_counts[level] = log_counts.get(level, 0) + 1

                app = source.get('application', 'unknown')
                applications_affected.add(app)

                # Collect error details
                if level == 'ERROR' and len(recent_errors) < 10:
                    recent_errors.append({
                        'timestamp': source.get('@timestamp', datetime.now().isoformat()),
                        'application': app,
                        'level': level,
                        'message': source.get('message', 'No message'),
                        'trace': source.get('error', {}).get('stack_trace', '')[:200]
                    })

            return {
                'total_logs': total_logs,
                'time_range': f'Last {time_window} minutes' if time_window != 'all' else 'All time',
                'log_counts': log_counts,
                'recent_errors': recent_errors,
                'traces': [],  # Would extract from span data if available
                'applications_affected': list(applications_affected),
                'timestamp': datetime.now().isoformat()
            }

        except requests.RequestException as e:
            print(f"Warning: Error querying Elasticsearch API: {e}")
            return {
                'total_logs': 0,
                'time_range': f'Last {time_window} minutes',
                'log_counts': {'ERROR': 0, 'WARN': 0, 'INFO': 0},
                'recent_errors': [],
                'traces': [],
                'applications_affected': [],
                'timestamp': datetime.now().isoformat(),
                'error': f'Request failed: {str(e)}'
            }
        except (ValueError, KeyError) as e:
            print(f"Warning: Error parsing Elasticsearch response: {e}")
            return {
                'total_logs': 0,
                'time_range': f'Last {time_window} minutes',
                'log_counts': {'ERROR': 0, 'WARN': 0, 'INFO': 0},
                'recent_errors': [],
                'traces': [],
                'applications_affected': [],
                'timestamp': datetime.now().isoformat(),
                'error': f'Parse error: {str(e)}'
            }

    def _generate_summary(self, results: Dict, query_type: str, log_level: str) -> str:
        """Generate a human-readable summary of the results."""

        total_logs = results.get('total_logs', 0)
        log_counts = results.get('log_counts', {})
        error_count = log_counts.get('ERROR', 0)
        warn_count = log_counts.get('WARN', 0)
        recent_errors = results.get('recent_errors', [])
        time_range = results.get('time_range', 'Unknown time range')

        summary_parts = []

        # Add time range
        summary_parts.append(f"{time_range}")

        # Add log counts
        summary_parts.append(f"Total logs: {total_logs}")

        # Error analysis
        if error_count > 0:
            summary_parts.append(f"{error_count} errors detected")

            # Add error breakdown
            if recent_errors:
                error_breakdown = {}
                for err in recent_errors[:5]:
                    msg = err.get('message', 'Unknown error')
                    error_breakdown[msg] = error_breakdown.get(msg, 0) + 1

                top_errors = sorted(error_breakdown.items(), key=lambda x: x[1], reverse=True)[:3]
                summary_parts.append("Top errors: " + ", ".join([f"{err[0]} ({err[1]}x)" for err in top_errors]))
        else:
            summary_parts.append("No errors detected")

        # Warning analysis
        if warn_count > 0:
            summary_parts.append(f"{warn_count} warnings")

        # Affected applications
        apps = results.get('applications_affected', [])
        if apps:
            summary_parts.append(f"Applications: {', '.join(apps)}")

        return " | ".join(summary_parts)
