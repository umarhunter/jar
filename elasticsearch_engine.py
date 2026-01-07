"""
Custom Elasticsearch Query Engine for LlamaIndex.
Translates natural language queries to Elasticsearch DSL and executes them.
"""
from typing import Any, Optional, List, Dict
from llama_index.core.query_engine import CustomQueryEngine
from llama_index.core.prompts import PromptTemplate
from llama_index.llms.openai import OpenAI
import requests
import json
import random
import os
from datetime import datetime, timedelta


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
    "- Time window (e.g., 'last 30 minutes', 'past hour', 'today')\n"
    "- Log level filter (INFO, WARN, ERROR, FATAL)\n"
    "- Application name if mentioned\n"
    "- Search terms or error patterns\n\n"
    "Respond in JSON format with:\n"
    "{{\n"
    "  'query_type': '<errors|logs|traces>',\n"
    "  'time_window': '<time window in minutes or 'all'>',\n"
    "  'log_level': '<INFO|WARN|ERROR|FATAL|ALL>',\n"
    "  'application': '<application name or 'all'>',\n"
    "  'search_terms': ['<term1>', '<term2>']\n"
    "}}\n\n"
    "Response:"
)


class ElasticsearchQueryEngine(CustomQueryEngine):
    """Custom query engine for Elasticsearch logs and traces."""

    llm: OpenAI
    mock_mode: bool = False  # Use real Elasticsearch by default
    elasticsearch_host: str = ""
    index_pattern: str = "logs-*"

    def __init__(self, llm: OpenAI, mock_mode: bool = False,
                 elasticsearch_host: Optional[str] = None,
                 index_pattern: str = "logs-*", **kwargs):
        """
        Initialize Elasticsearch query engine.

        Args:
            llm: OpenAI LLM instance
            mock_mode: If True, generate mock data instead of querying Elasticsearch
            elasticsearch_host: Elasticsearch host (default: http://elasticsearch:9200 or env ELASTICSEARCH_HOST)
            index_pattern: Index pattern to search (default: logs-*)
        """
        if elasticsearch_host is None:
            elasticsearch_host = os.getenv('ELASTICSEARCH_HOST', 'http://elasticsearch:9200')

        super().__init__(llm=llm, mock_mode=mock_mode, elasticsearch_host=elasticsearch_host, index_pattern=index_pattern, **kwargs)

        # Test Elasticsearch connection if not in mock mode
        if not mock_mode:
            try:
                response = requests.get(f"{elasticsearch_host}/_cluster/health", timeout=5)
                if response.status_code == 200:
                    print(f"Connected to Elasticsearch at {elasticsearch_host}")
                else:
                    print(f"Warning: Elasticsearch returned status {response.status_code}, falling back to mock mode")
                    self.mock_mode = True
            except Exception as e:
                print(f"Warning: Failed to connect to Elasticsearch at {elasticsearch_host}: {e}")
                print("Falling back to mock mode")
                self.mock_mode = True

    def custom_query(self, query_str: str) -> Any:
        """Execute a query against Elasticsearch."""

        # Step 1: Parse natural language to Elasticsearch query parameters
        prompt = ELASTICSEARCH_QUERY_PROMPT.format(query_str=query_str)
        response = self.llm.complete(prompt)

        try:
            # Parse the LLM response
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif response_text.startswith("```"):
                response_text = response_text.split("```")[1].split("```")[0].strip()

            query_info = json.loads(response_text)
            query_type = query_info.get('query_type', 'logs')
            time_window = query_info.get('time_window', '60')
            log_level = query_info.get('log_level', 'ALL')
            application = query_info.get('application', 'all')
            search_terms = query_info.get('search_terms', [])

        except (json.JSONDecodeError, ValueError, KeyError, AttributeError) as e:
            # Fallback if parsing fails
            print(f"Warning: Failed to parse Elasticsearch query response: {e}")
            query_type = 'logs'
            time_window = '60'
            log_level = 'ALL'
            application = 'all'
            search_terms = []

        # Step 2: Execute the Elasticsearch query (mock for pilot)
        if self.mock_mode:
            results = self._mock_elasticsearch_query(
                query_type, time_window, log_level, application, search_terms
            )
        else:
            # Would call actual Elasticsearch API here
            results = self._query_elasticsearch_api(
                query_type, time_window, log_level, application, search_terms
            )

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

    def _mock_elasticsearch_query(
        self,
        query_type: str,
        time_window: str,
        log_level: str,
        application: str,
        search_terms: List[str]
    ) -> Dict:
        """Generate mock Elasticsearch data for pilot phase."""

        timestamp = datetime.now()

        # Mock applications
        apps = ['user-service', 'payment-gateway', 'notification-service', 'analytics-engine']
        if application != 'all' and application in apps:
            apps = [application]

        # Generate mock log entries
        total_logs = random.randint(100, 1000)
        error_count = random.randint(5, 50) if log_level in ['ERROR', 'ALL'] else 0
        warn_count = random.randint(10, 100) if log_level in ['WARN', 'ALL'] else 0
        info_count = total_logs - error_count - warn_count if log_level == 'ALL' else total_logs

        # Generate mock error entries
        error_types = [
            'NullPointerException',
            'ConnectionTimeout',
            'DatabaseConnectionError',
            'AuthenticationFailure',
            'RateLimitExceeded',
            'InvalidRequestException'
        ]

        recent_errors = []
        if query_type == 'errors' or log_level == 'ERROR':
            for i in range(min(error_count, 10)):
                recent_errors.append({
                    'timestamp': (timestamp - timedelta(minutes=random.randint(1, int(time_window or 60)))).isoformat(),
                    'application': random.choice(apps),
                    'level': 'ERROR',
                    'message': random.choice(error_types),
                    'trace': f'at com.example.service.Handler.process(Handler.java:{random.randint(100, 500)})'
                })

        # Generate mock trace data
        traces = []
        if query_type == 'traces':
            for i in range(5):
                traces.append({
                    'trace_id': f'trace-{random.randint(10000, 99999)}',
                    'application': random.choice(apps),
                    'duration_ms': random.randint(100, 2000),
                    'error': random.choice([True, False]),
                    'timestamp': (timestamp - timedelta(minutes=random.randint(1, 30))).isoformat()
                })

        return {
            'total_logs': total_logs,
            'time_range': f'Last {time_window} minutes' if time_window != 'all' else 'All time',
            'log_counts': {
                'ERROR': error_count,
                'WARN': warn_count,
                'INFO': info_count
            },
            'recent_errors': sorted(recent_errors, key=lambda x: x['timestamp'], reverse=True),
            'traces': traces,
            'applications_affected': apps[:random.randint(1, len(apps))],
            'timestamp': timestamp.isoformat()
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
