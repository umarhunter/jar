"""
Script to populate dummy data into Prometheus, Elasticsearch, and Oracle databases
for testing the ObservabilityAgent.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
import json
from datetime import datetime, timedelta
import random
import time
from jar.database.models import create_sample_database

def populate_prometheus_metrics():
    """
    Push custom metrics to Prometheus using Pushgateway.
    Note: Requires Prometheus Pushgateway running on localhost:9091
    """
    print("\n" + "="*60)
    print("Populating Prometheus Metrics")
    print("="*60)

    pushgateway_url = "http://localhost:9091/metrics/job/test_metrics"

    # Define various metric scenarios
    scenarios = [
        {
            "name": "high_cpu",
            "metrics": """
# HELP node_cpu_usage CPU usage percentage
# TYPE node_cpu_usage gauge
node_cpu_usage{instance="user-service",environment="production"} 85.5
node_cpu_usage{instance="payment-gateway",environment="production"} 45.2
node_cpu_usage{instance="notification-service",environment="production"} 62.3
node_cpu_usage{instance="analytics-engine",environment="production"} 92.1
"""
        },
        {
            "name": "memory_usage",
            "metrics": """
# HELP node_memory_usage Memory usage percentage
# TYPE node_memory_usage gauge
node_memory_usage{instance="user-service",environment="production"} 78.3
node_memory_usage{instance="payment-gateway",environment="production"} 88.7
node_memory_usage{instance="notification-service",environment="production"} 55.1
node_memory_usage{instance="analytics-engine",environment="production"} 91.4
"""
        },
        {
            "name": "response_times",
            "metrics": """
# HELP http_request_duration_seconds HTTP request duration in seconds
# TYPE http_request_duration_seconds gauge
http_request_duration_seconds{instance="user-service",endpoint="/login"} 0.245
http_request_duration_seconds{instance="user-service",endpoint="/profile"} 0.123
http_request_duration_seconds{instance="payment-gateway",endpoint="/process"} 0.856
http_request_duration_seconds{instance="notification-service",endpoint="/send"} 0.312
"""
        },
        {
            "name": "error_rates",
            "metrics": """
# HELP http_errors_total Total HTTP errors
# TYPE http_errors_total counter
http_errors_total{instance="user-service",code="401"} 45
http_errors_total{instance="user-service",code="500"} 12
http_errors_total{instance="payment-gateway",code="401"} 156
http_errors_total{instance="payment-gateway",code="503"} 8
http_errors_total{instance="notification-service",code="500"} 23
"""
        },
        {
            "name": "request_rates",
            "metrics": """
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{instance="user-service",endpoint="/login"} 12456
http_requests_total{instance="user-service",endpoint="/profile"} 8923
http_requests_total{instance="payment-gateway",endpoint="/process"} 3421
http_requests_total{instance="notification-service",endpoint="/send"} 15672
"""
        }
    ]

    try:
        for scenario in scenarios:
            print(f"\nPushing {scenario['name']} metrics...")
            response = requests.post(
                pushgateway_url,
                data=scenario['metrics'],
                headers={'Content-Type': 'text/plain'}
            )
            if response.status_code == 200:
                print(f"✓ Successfully pushed {scenario['name']}")
            else:
                print(f"✗ Failed to push {scenario['name']}: {response.status_code}")
                print(f"  Response: {response.text}")

        print("\n✓ Prometheus metrics population complete!")
        print("\nNote: If you see errors, make sure Prometheus Pushgateway is running:")
        print("  Docker: docker run -d -p 9091:9091 prom/pushgateway")
        print("  Or configure prometheus.yml to scrape from your applications")

    except requests.RequestException as e:
        print(f"\n✗ Error connecting to Pushgateway: {e}")
        print("\nAlternative: You can manually add these metrics to prometheus.yml")
        print("or use a metrics exporter for your applications.")


def populate_elasticsearch_logs():
    """
    Push log entries to Elasticsearch for testing.
    """
    print("\n" + "="*60)
    print("Populating Elasticsearch Logs")
    print("="*60)

    elasticsearch_url = "http://localhost:9200"
    index_name = "application_logs"

    # Sample log entries with various scenarios
    log_entries = []
    now = datetime.now()

    applications = ['user-service', 'payment-gateway', 'notification-service', 'analytics-engine']
    log_levels = ['INFO', 'WARN', 'ERROR']

    # Generate normal INFO logs (spread across 30 days)
    for i in range(50):
        timestamp = now - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
        log_entries.append({
            "@timestamp": timestamp.isoformat(),
            "application": random.choice(applications),
            "level": "INFO",
            "message": random.choice([
                "Request processed successfully",
                "User authenticated",
                "Database query executed",
                "Cache hit",
                "API response sent"
            ]),
            "request_id": f"req-{random.randint(1000, 9999)}",
            "duration_ms": random.randint(50, 300)
        })

    # Generate WARNING logs
    warning_messages = [
        "Slow database query detected (>1s)",
        "Cache miss rate high (>30%)",
        "Connection pool near capacity",
        "Rate limit approaching threshold",
        "Deprecated API endpoint used"
    ]

    for i in range(20):
        timestamp = now - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
        log_entries.append({
            "@timestamp": timestamp.isoformat(),
            "application": random.choice(applications),
            "level": "WARN",
            "message": random.choice(warning_messages),
            "request_id": f"req-{random.randint(1000, 9999)}",
            "duration_ms": random.randint(500, 2000)
        })

    # Generate ERROR logs with stack traces
    error_scenarios = [
        {
            "message": "Database connection timeout",
            "error_type": "TimeoutError",
            "stack_trace": "at DatabasePool.connect(db.py:123)\nat QueryExecutor.run(query.py:45)"
        },
        {
            "message": "Authentication token expired",
            "error_type": "AuthenticationError",
            "stack_trace": "at TokenValidator.verify(auth.py:67)\nat Middleware.authenticate(middleware.py:34)"
        },
        {
            "message": "External API request failed",
            "error_type": "RequestException",
            "stack_trace": "at HTTPClient.post(client.py:89)\nat PaymentService.process(payment.py:156)"
        },
        {
            "message": "Null pointer exception in user profile",
            "error_type": "NullPointerError",
            "stack_trace": "at UserService.getProfile(user.py:234)\nat ProfileController.show(controller.py:78)"
        },
        {
            "message": "Message queue connection lost",
            "error_type": "ConnectionError",
            "stack_trace": "at RabbitMQClient.connect(mq.py:45)\nat NotificationService.send(notify.py:112)"
        }
    ]

    for i in range(30):
        timestamp = now - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
        error = random.choice(error_scenarios)
        # Make half of errors specifically for payment-gateway
        app = 'payment-gateway' if i % 2 == 0 else random.choice(applications)
        log_entries.append({
            "@timestamp": timestamp.isoformat(),
            "application": app,
            "level": "ERROR",
            "message": error["message"],
            "error": {
                "type": error["error_type"],
                "stack_trace": error["stack_trace"]
            },
            "request_id": f"req-{random.randint(1000, 9999)}",
            "user_id": random.randint(1000, 5000)
        })

    # Bulk insert logs
    try:
        print(f"\nInserting {len(log_entries)} log entries...")

        # Create index with proper mapping
        index_body = {
            "mappings": {
                "properties": {
                    "@timestamp": {"type": "date"},
                    "application": {"type": "keyword"},
                    "level": {"type": "keyword"},
                    "message": {"type": "text"},
                    "request_id": {"type": "keyword"},
                    "duration_ms": {"type": "integer"},
                    "error": {
                        "properties": {
                            "type": {"type": "keyword"},
                            "stack_trace": {"type": "text"}
                        }
                    }
                }
            }
        }

        # Create index
        response = requests.put(
            f"{elasticsearch_url}/{index_name}",
            json=index_body,
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code in [200, 400]:  # 400 if index already exists
            print(f"✓ Index {index_name} ready")

        # Bulk insert using _bulk API
        bulk_data = []
        for log in log_entries:
            bulk_data.append(json.dumps({"index": {"_index": index_name}}))
            bulk_data.append(json.dumps(log))

        bulk_body = "\n".join(bulk_data) + "\n"

        response = requests.post(
            f"{elasticsearch_url}/_bulk",
            data=bulk_body,
            headers={'Content-Type': 'application/x-ndjson'}
        )

        if response.status_code == 200:
            result = response.json()
            if result.get('errors'):
                print(f"✗ Some logs failed to insert")
                print(f"  {result}")
            else:
                print(f"✓ Successfully inserted {len(log_entries)} logs")

                # Print summary
                error_count = sum(1 for log in log_entries if log['level'] == 'ERROR')
                warn_count = sum(1 for log in log_entries if log['level'] == 'WARN')
                info_count = sum(1 for log in log_entries if log['level'] == 'INFO')

                print(f"\nLog summary:")
                print(f"  INFO:  {info_count}")
                print(f"  WARN:  {warn_count}")
                print(f"  ERROR: {error_count}")
        else:
            print(f"✗ Failed to insert logs: {response.status_code}")
            print(f"  Response: {response.text[:500]}")

        print("\n✓ Elasticsearch logs population complete!")

    except requests.RequestException as e:
        print(f"\n✗ Error connecting to Elasticsearch: {e}")
        print("\nMake sure Elasticsearch is running:")
        print("  Docker: docker run -d -p 9200:9200 -e 'discovery.type=single-node' docker.elastic.co/elasticsearch/elasticsearch:8.11.0")


def populate_oracle_database():
    """
    Populate Oracle database (SQLite) with sample data.
    This uses the existing create_sample_database function.
    """
    print("\n" + "="*60)
    print("Populating Oracle Database (SQLite)")
    print("="*60)

    try:
        engine = create_sample_database('oracle_pilot.db')
        print("✓ Oracle database populated successfully!")
        print("\nDatabase contains:")
        print("  - 4 applications")
        print("  - 12 performance thresholds")
        print("  - 4 historical incidents")

    except Exception as e:
        print(f"✗ Error populating Oracle database: {e}")


def main():
    """Run all population scripts."""
    print("\n" + "="*60)
    print("DUMMY DATA POPULATION SCRIPT")
    print("="*60)
    print("\nThis script will populate test data into:")
    print("  1. Oracle Database (SQLite)")
    print("  2. Prometheus (via Pushgateway)")
    print("  3. Elasticsearch")
    print("\n" + "="*60)

    # Populate Oracle (always works, local SQLite)
    populate_oracle_database()

    # Populate Elasticsearch
    populate_elasticsearch_logs()

    # Populate Prometheus
    populate_prometheus_metrics()

    print("\n" + "="*60)
    print("DATA POPULATION COMPLETE!")
    print("="*60)
    print("\nYou can now run test_agent.py to see the agent working with real data.")
    print("\nTest queries to try:")
    print("  - 'What is the CPU usage?'")
    print("  - 'Show me recent errors'")
    print("  - 'Which services have high memory usage?'")
    print("  - 'Are there any authentication errors?'")
    print("  - 'What is the response time for the payment gateway?'")
    print()


if __name__ == "__main__":
    main()
