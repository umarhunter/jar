"""
Script to populate dummy data into Prometheus, Elasticsearch, and Oracle databases
for testing the ObservabilityAgent.

Enhanced version with:
- Historical time-series data generation
- Pre-computed baselines for anomaly detection
- Traffic pattern analysis
- Availability statistics
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
import json
from datetime import datetime, timedelta
import random
import math
from typing import List, Dict, Optional
from jar.database.models import (
    create_sample_database, get_session, get_db_path,
    MetricBaseline, TrafficPattern, AvailabilityStats, MetricTimeSeries
)


# Application definitions with realistic baseline characteristics
APPLICATIONS = {
    'user-service': {
        'cpu_baseline': 45,
        'cpu_variance': 15,
        'memory_baseline': 60,
        'memory_variance': 10,
        'latency_baseline': 120,  # ms
        'latency_variance': 50,
        'request_rate_baseline': 500,  # requests/min
        'request_rate_variance': 200,
        'error_rate_baseline': 0.5,  # percent
        'error_rate_variance': 0.3,
        'availability_baseline': 99.9,
    },
    'payment-gateway': {
        'cpu_baseline': 35,
        'cpu_variance': 10,
        'memory_baseline': 55,
        'memory_variance': 8,
        'latency_baseline': 250,  # ms - payment processing is slower
        'latency_variance': 100,
        'request_rate_baseline': 150,
        'request_rate_variance': 50,
        'error_rate_baseline': 1.2,  # higher error rate due to auth failures
        'error_rate_variance': 0.8,
        'availability_baseline': 99.95,
    },
    'notification-service': {
        'cpu_baseline': 25,
        'cpu_variance': 12,
        'memory_baseline': 40,
        'memory_variance': 15,
        'latency_baseline': 80,
        'latency_variance': 30,
        'request_rate_baseline': 800,  # high volume
        'request_rate_variance': 400,
        'error_rate_baseline': 0.3,
        'error_rate_variance': 0.2,
        'availability_baseline': 99.8,
    },
    'analytics-engine': {
        'cpu_baseline': 70,  # CPU intensive
        'cpu_variance': 20,
        'memory_baseline': 75,
        'memory_variance': 12,
        'latency_baseline': 500,  # slow queries
        'latency_variance': 200,
        'request_rate_baseline': 100,
        'request_rate_variance': 50,
        'error_rate_baseline': 0.8,
        'error_rate_variance': 0.5,
        'availability_baseline': 99.5,
    },
}

# Traffic patterns: multipliers by hour (0-23) - simulates daily patterns
HOURLY_TRAFFIC_PATTERN = [
    0.3, 0.2, 0.15, 0.1, 0.1, 0.15,  # 00:00 - 05:00 (night, low traffic)
    0.3, 0.5, 0.8, 1.0, 1.1, 1.2,     # 06:00 - 11:00 (morning ramp up)
    1.0, 1.1, 1.2, 1.3, 1.2, 1.1,     # 12:00 - 17:00 (business hours peak)
    0.9, 0.8, 0.7, 0.5, 0.4, 0.35,    # 18:00 - 23:00 (evening wind down)
]

# Weekly pattern multipliers (0=Monday, 6=Sunday)
DAILY_TRAFFIC_PATTERN = [1.0, 1.1, 1.0, 1.05, 0.9, 0.5, 0.4]


def generate_metric_value(baseline: float, variance: float,
                          hour: int = 12, day_of_week: int = 2,
                          add_anomaly: bool = False) -> float:
    """Generate a realistic metric value with time-based patterns."""
    # Apply time-based patterns
    hourly_multiplier = HOURLY_TRAFFIC_PATTERN[hour]
    daily_multiplier = DAILY_TRAFFIC_PATTERN[day_of_week]

    # Base value with some randomness
    value = baseline * hourly_multiplier * daily_multiplier
    value += random.gauss(0, variance)

    # Occasionally add anomalies (spikes)
    if add_anomaly and random.random() < 0.02:  # 2% chance of anomaly
        value *= random.uniform(1.5, 2.5)

    return max(0, value)  # Ensure non-negative


def generate_historical_timeseries(days: int = 120) -> Dict[str, List[Dict]]:
    """Generate historical time series data for all applications and metrics."""
    print(f"\nGenerating {days} days of historical time series data...")

    timeseries = {}
    now = datetime.now()

    for app_name, app_config in APPLICATIONS.items():
        timeseries[app_name] = {
            'cpu': [],
            'memory': [],
            'latency': [],
            'request_volume': [],
            'error_rate': [],
        }

        # Generate data points every 5 minutes for the specified days
        # For efficiency, we'll sample every 15 minutes for older data
        for day_offset in range(days, 0, -1):
            # Use 15-min intervals for data older than 7 days, 5-min for recent
            interval = 15 if day_offset > 7 else 5

            for hour in range(24):
                for minute in range(0, 60, interval):
                    timestamp = now - timedelta(days=day_offset, hours=24-hour, minutes=60-minute)
                    day_of_week = timestamp.weekday()

                    # Add occasional anomalies
                    add_anomaly = random.random() < 0.01

                    # Generate each metric
                    timeseries[app_name]['cpu'].append({
                        'timestamp': timestamp,
                        'value': generate_metric_value(
                            app_config['cpu_baseline'],
                            app_config['cpu_variance'],
                            hour, day_of_week, add_anomaly
                        )
                    })

                    timeseries[app_name]['memory'].append({
                        'timestamp': timestamp,
                        'value': generate_metric_value(
                            app_config['memory_baseline'],
                            app_config['memory_variance'],
                            hour, day_of_week, add_anomaly
                        )
                    })

                    timeseries[app_name]['latency'].append({
                        'timestamp': timestamp,
                        'value': generate_metric_value(
                            app_config['latency_baseline'],
                            app_config['latency_variance'],
                            hour, day_of_week, add_anomaly
                        )
                    })

                    timeseries[app_name]['request_volume'].append({
                        'timestamp': timestamp,
                        'value': generate_metric_value(
                            app_config['request_rate_baseline'],
                            app_config['request_rate_variance'],
                            hour, day_of_week, add_anomaly
                        )
                    })

                    timeseries[app_name]['error_rate'].append({
                        'timestamp': timestamp,
                        'value': max(0, min(100, generate_metric_value(
                            app_config['error_rate_baseline'],
                            app_config['error_rate_variance'],
                            hour, day_of_week, add_anomaly
                        )))
                    })

        print(f"  Generated {len(timeseries[app_name]['cpu'])} data points for {app_name}")

    return timeseries


def compute_baselines(timeseries: Dict[str, List[Dict]], session) -> None:
    """Compute and store metric baselines from time series data."""
    print("\nComputing metric baselines...")

    now = datetime.now()

    # Clear existing baselines
    session.query(MetricBaseline).delete()

    for app_name, metrics in timeseries.items():
        for metric_name, data_points in metrics.items():
            if not data_points:
                continue

            # Filter data by time windows
            values_30d = [p['value'] for p in data_points
                         if (now - p['timestamp']).days <= 30]
            values_60d = [p['value'] for p in data_points
                         if (now - p['timestamp']).days <= 60]
            values_90d = [p['value'] for p in data_points
                         if (now - p['timestamp']).days <= 90]
            values_120d = [p['value'] for p in data_points]

            # Calculate statistics
            def calc_stats(values):
                if not values:
                    return 0, 0, 0, 0
                avg = sum(values) / len(values)
                variance = sum((x - avg) ** 2 for x in values) / len(values)
                stddev = math.sqrt(variance)
                return avg, stddev, min(values), max(values)

            avg_30d, stddev_30d, min_30d, max_30d = calc_stats(values_30d)
            avg_60d, _, _, _ = calc_stats(values_60d)
            avg_90d, _, _, _ = calc_stats(values_90d)
            avg_120d, _, _, _ = calc_stats(values_120d)

            # Get current value (most recent)
            current_value = data_points[-1]['value'] if data_points else 0

            # Determine unit
            unit_map = {
                'cpu': 'percent',
                'memory': 'percent',
                'latency': 'ms',
                'request_volume': 'req/min',
                'error_rate': 'percent',
            }

            baseline = MetricBaseline(
                application_name=app_name,
                metric_name=metric_name,
                avg_30d=avg_30d,
                avg_60d=avg_60d,
                avg_90d=avg_90d,
                avg_120d=avg_120d,
                stddev_30d=stddev_30d,
                min_30d=min_30d,
                max_30d=max_30d,
                current_value=current_value,
                unit=unit_map.get(metric_name, ''),
                last_updated=now
            )
            session.add(baseline)

        print(f"  Computed baselines for {app_name}")

    session.commit()
    print("  Baselines stored in database")


def compute_traffic_patterns(timeseries: Dict[str, List[Dict]], session) -> None:
    """Compute and store traffic patterns (peak hours, daily patterns)."""
    print("\nComputing traffic patterns...")

    now = datetime.now()

    # Clear existing patterns
    session.query(TrafficPattern).delete()

    for app_name, metrics in timeseries.items():
        # Focus on request_volume and latency for traffic patterns
        for metric_name in ['request_volume', 'latency']:
            data_points = metrics.get(metric_name, [])
            if not data_points:
                continue

            # Group by hour and day of week
            patterns = {}  # (hour, day_of_week) -> [values]

            for point in data_points:
                hour = point['timestamp'].hour
                day = point['timestamp'].weekday()
                key = (hour, day)

                if key not in patterns:
                    patterns[key] = []
                patterns[key].append(point['value'])

            # Calculate aggregates and identify peaks
            all_avgs = []
            pattern_records = []

            for (hour, day), values in patterns.items():
                avg_val = sum(values) / len(values)
                all_avgs.append(avg_val)
                pattern_records.append({
                    'hour': hour,
                    'day': day,
                    'avg': avg_val,
                    'min': min(values),
                    'max': max(values),
                    'count': len(values)
                })

            # Determine peak threshold (top 20% of averages)
            if all_avgs:
                sorted_avgs = sorted(all_avgs, reverse=True)
                peak_threshold = sorted_avgs[int(len(sorted_avgs) * 0.2)] if len(sorted_avgs) > 5 else sorted_avgs[0]
            else:
                peak_threshold = 0

            # Store patterns
            for record in pattern_records:
                pattern = TrafficPattern(
                    application_name=app_name,
                    metric_name=metric_name,
                    hour_of_day=record['hour'],
                    day_of_week=record['day'],
                    avg_value=record['avg'],
                    min_value=record['min'],
                    max_value=record['max'],
                    sample_count=record['count'],
                    is_peak=record['avg'] >= peak_threshold,
                    last_updated=now
                )
                session.add(pattern)

        print(f"  Computed traffic patterns for {app_name}")

    session.commit()
    print("  Traffic patterns stored in database")


def compute_availability_stats(timeseries: Dict[str, List[Dict]], session) -> None:
    """Compute and store availability statistics."""
    print("\nComputing availability statistics...")

    now = datetime.now()

    # Clear existing stats
    session.query(AvailabilityStats).delete()

    for app_name, metrics in timeseries.items():
        error_rates = metrics.get('error_rate', [])
        request_volumes = metrics.get('request_volume', [])

        # Filter by time windows
        def filter_by_days(data, days):
            return [p for p in data if (now - p['timestamp']).days <= days]

        errors_24h = filter_by_days(error_rates, 1)
        errors_7d = filter_by_days(error_rates, 7)
        errors_30d = filter_by_days(error_rates, 30)

        # Calculate error-free percentage (100 - avg_error_rate)
        def avg_error_free(error_data):
            if not error_data:
                return 100.0
            avg_error = sum(p['value'] for p in error_data) / len(error_data)
            return max(0, min(100, 100 - avg_error))

        # Simulate uptime based on error rates
        # High error rates indicate potential downtime
        def estimate_uptime(error_data, base_uptime=99.9):
            if not error_data:
                return base_uptime
            avg_error = sum(p['value'] for p in error_data) / len(error_data)
            # Higher error rates reduce uptime
            uptime = base_uptime - (avg_error * 0.1)
            return max(90, min(100, uptime))

        # Calculate success rates (inverse of error rate, weighted by volume)
        def calc_success_rate(error_data, volume_data):
            if not error_data or not volume_data:
                return 99.0
            # Match timestamps approximately
            total_requests = sum(p['value'] for p in volume_data)
            avg_error_rate = sum(p['value'] for p in error_data) / len(error_data)
            return max(0, min(100, 100 - avg_error_rate))

        app_config = APPLICATIONS.get(app_name, {})
        base_availability = app_config.get('availability_baseline', 99.9)

        stats = AvailabilityStats(
            application_name=app_name,
            uptime_percent_24h=estimate_uptime(errors_24h, base_availability),
            uptime_percent_7d=estimate_uptime(errors_7d, base_availability),
            uptime_percent_30d=estimate_uptime(errors_30d, base_availability),
            total_downtime_minutes_24h=(100 - estimate_uptime(errors_24h, base_availability)) * 14.4,  # 1440 min * pct
            total_downtime_minutes_7d=(100 - estimate_uptime(errors_7d, base_availability)) * 100.8,
            total_downtime_minutes_30d=(100 - estimate_uptime(errors_30d, base_availability)) * 432,
            error_free_percent_24h=avg_error_free(errors_24h),
            error_free_percent_7d=avg_error_free(errors_7d),
            error_free_percent_30d=avg_error_free(errors_30d),
            success_rate_24h=calc_success_rate(errors_24h, filter_by_days(request_volumes, 1)),
            success_rate_7d=calc_success_rate(errors_7d, filter_by_days(request_volumes, 7)),
            success_rate_30d=calc_success_rate(errors_30d, filter_by_days(request_volumes, 30)),
            last_updated=now
        )
        session.add(stats)
        print(f"  Computed availability for {app_name}")

    session.commit()
    print("  Availability stats stored in database")


def store_timeseries_sample(timeseries: Dict[str, List[Dict]], session, sample_rate: int = 10) -> None:
    """Store a sample of time series data for trend analysis (every Nth point)."""
    print(f"\nStoring time series sample (1 in {sample_rate} points)...")

    # Clear existing time series
    session.query(MetricTimeSeries).delete()

    count = 0
    for app_name, metrics in timeseries.items():
        for metric_name, data_points in metrics.items():
            for i, point in enumerate(data_points):
                if i % sample_rate == 0:  # Store every Nth point
                    ts = MetricTimeSeries(
                        application_name=app_name,
                        metric_name=metric_name,
                        timestamp=point['timestamp'],
                        value=point['value'],
                        environment='production'
                    )
                    session.add(ts)
                    count += 1

    session.commit()
    print(f"  Stored {count} time series data points")


def precompute_all_baselines(db_path: str = None, days: int = 120) -> Dict:
    """
    Main function to precompute all baselines.
    Can be called manually via API or script.

    Returns a summary of what was computed.
    """
    if db_path is None:
        db_path = get_db_path()

    print("\n" + "="*60)
    print("PRECOMPUTING BASELINES AND PATTERNS")
    print("="*60)

    session = get_session(db_path)

    try:
        # Generate historical data
        timeseries = generate_historical_timeseries(days)

        # Compute and store baselines
        compute_baselines(timeseries, session)

        # Compute and store traffic patterns
        compute_traffic_patterns(timeseries, session)

        # Compute and store availability stats
        compute_availability_stats(timeseries, session)

        # Store sampled time series for ad-hoc queries
        store_timeseries_sample(timeseries, session, sample_rate=10)

        summary = {
            'status': 'success',
            'days_processed': days,
            'applications': list(APPLICATIONS.keys()),
            'metrics': ['cpu', 'memory', 'latency', 'request_volume', 'error_rate'],
            'timestamp': datetime.now().isoformat()
        }

        print("\n" + "="*60)
        print("BASELINE PRECOMPUTATION COMPLETE")
        print("="*60)

        return summary

    except Exception as e:
        session.rollback()
        print(f"\nError during precomputation: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
    finally:
        session.close()


def populate_prometheus_metrics():
    """
    Push current metrics to Prometheus using Pushgateway.
    These represent the 'current' state that the agent queries.
    """
    print("\n" + "="*60)
    print("Populating Prometheus Metrics")
    print("="*60)

    pushgateway_url = os.getenv('PUSHGATEWAY_URL', 'http://localhost:9091')
    pushgateway_url = f"{pushgateway_url}/metrics/job/observability_metrics"

    now = datetime.now()
    hour = now.hour
    day_of_week = now.weekday()

    # Generate current metrics for each application
    metrics_text = []

    # CPU Usage
    metrics_text.append("# HELP node_cpu_usage Current CPU usage percentage")
    metrics_text.append("# TYPE node_cpu_usage gauge")
    for app_name, config in APPLICATIONS.items():
        value = generate_metric_value(config['cpu_baseline'], config['cpu_variance'], hour, day_of_week)
        metrics_text.append(f'node_cpu_usage{{instance="{app_name}",environment="production"}} {value:.2f}')

    # Memory Usage
    metrics_text.append("# HELP node_memory_usage Current memory usage percentage")
    metrics_text.append("# TYPE node_memory_usage gauge")
    for app_name, config in APPLICATIONS.items():
        value = generate_metric_value(config['memory_baseline'], config['memory_variance'], hour, day_of_week)
        metrics_text.append(f'node_memory_usage{{instance="{app_name}",environment="production"}} {value:.2f}')

    # Response Time / Latency
    metrics_text.append("# HELP http_request_duration_seconds HTTP request duration in seconds")
    metrics_text.append("# TYPE http_request_duration_seconds gauge")
    for app_name, config in APPLICATIONS.items():
        # Convert ms to seconds for Prometheus convention
        value_ms = generate_metric_value(config['latency_baseline'], config['latency_variance'], hour, day_of_week)
        value_sec = value_ms / 1000.0
        metrics_text.append(f'http_request_duration_seconds{{instance="{app_name}",environment="production"}} {value_sec:.4f}')

    # Request Rate (as counter, but we'll use gauge for simplicity in demo)
    metrics_text.append("# HELP http_requests_total Total HTTP requests per minute")
    metrics_text.append("# TYPE http_requests_total gauge")
    for app_name, config in APPLICATIONS.items():
        value = generate_metric_value(config['request_rate_baseline'], config['request_rate_variance'], hour, day_of_week)
        metrics_text.append(f'http_requests_total{{instance="{app_name}",environment="production"}} {value:.0f}')

    # Error Rate
    metrics_text.append("# HELP http_error_rate Current error rate percentage")
    metrics_text.append("# TYPE http_error_rate gauge")
    for app_name, config in APPLICATIONS.items():
        value = max(0, min(100, generate_metric_value(config['error_rate_baseline'], config['error_rate_variance'], hour, day_of_week)))
        metrics_text.append(f'http_error_rate{{instance="{app_name}",environment="production"}} {value:.2f}')

    # Error counts by type (for detailed error analysis)
    metrics_text.append("# HELP http_errors_total Total HTTP errors by code")
    metrics_text.append("# TYPE http_errors_total counter")
    error_codes = ['401', '500', '503']
    for app_name, config in APPLICATIONS.items():
        base_errors = config['error_rate_baseline'] * config['request_rate_baseline'] / 100
        for code in error_codes:
            # Distribute errors across codes
            multiplier = {'401': 0.5, '500': 0.3, '503': 0.2}[code]
            value = int(base_errors * multiplier * random.uniform(0.5, 1.5))
            metrics_text.append(f'http_errors_total{{instance="{app_name}",code="{code}",environment="production"}} {value}')

    # Availability (derived metric)
    metrics_text.append("# HELP service_availability Current service availability percentage")
    metrics_text.append("# TYPE service_availability gauge")
    for app_name, config in APPLICATIONS.items():
        # Availability = base - small random variance
        value = config['availability_baseline'] - random.uniform(0, 0.2)
        metrics_text.append(f'service_availability{{instance="{app_name}",environment="production"}} {value:.2f}')

    metrics_data = "\n".join(metrics_text) + "\n"

    try:
        response = requests.post(
            pushgateway_url,
            data=metrics_data,
            headers={'Content-Type': 'text/plain'},
            timeout=10
        )
        if response.status_code == 200:
            print(f"  Successfully pushed metrics to Pushgateway")
            print(f"  Metrics for: {', '.join(APPLICATIONS.keys())}")
        else:
            print(f"  Failed to push metrics: {response.status_code}")
            print(f"  Response: {response.text}")

    except requests.RequestException as e:
        print(f"\n  Error connecting to Pushgateway: {e}")
        print("\n  Make sure Pushgateway is running:")
        print("    docker-compose up -d pushgateway")

    print("\n  Prometheus metrics population complete!")


def populate_elasticsearch_logs():
    """Push log entries to Elasticsearch for testing."""
    print("\n" + "="*60)
    print("Populating Elasticsearch Logs")
    print("="*60)

    elasticsearch_url = os.getenv('ELASTICSEARCH_HOST', 'http://localhost:9200')
    index_name = "application_logs"

    log_entries = []
    now = datetime.now()

    applications = list(APPLICATIONS.keys())

    # Generate INFO logs (spread across 30 days)
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
                "API response sent",
                "Health check passed",
                "Connection established",
                "Task completed successfully"
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
        "Deprecated API endpoint used",
        "Memory usage above 80%",
        "Response time degraded",
        "Retry attempt for external service"
    ]

    for i in range(25):
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

    for i in range(35):
        timestamp = now - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
        error = random.choice(error_scenarios)
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

    try:
        print(f"\n  Inserting {len(log_entries)} log entries...")

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
                    "user_id": {"type": "integer"},
                    "error": {
                        "properties": {
                            "type": {"type": "keyword"},
                            "stack_trace": {"type": "text"}
                        }
                    }
                }
            }
        }

        # Delete existing index if exists
        requests.delete(f"{elasticsearch_url}/{index_name}", timeout=5)

        # Create index
        response = requests.put(
            f"{elasticsearch_url}/{index_name}",
            json=index_body,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        if response.status_code in [200, 201]:
            print(f"  Index {index_name} created")

        # Bulk insert using _bulk API
        bulk_data = []
        for log in log_entries:
            bulk_data.append(json.dumps({"index": {"_index": index_name}}))
            bulk_data.append(json.dumps(log))

        bulk_body = "\n".join(bulk_data) + "\n"

        response = requests.post(
            f"{elasticsearch_url}/_bulk",
            data=bulk_body,
            headers={'Content-Type': 'application/x-ndjson'},
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            if not result.get('errors'):
                print(f"  Successfully inserted {len(log_entries)} logs")

                error_count = sum(1 for log in log_entries if log['level'] == 'ERROR')
                warn_count = sum(1 for log in log_entries if log['level'] == 'WARN')
                info_count = sum(1 for log in log_entries if log['level'] == 'INFO')

                print(f"\n  Log summary:")
                print(f"    INFO:  {info_count}")
                print(f"    WARN:  {warn_count}")
                print(f"    ERROR: {error_count}")
            else:
                print(f"  Some logs failed to insert")
        else:
            print(f"  Failed to insert logs: {response.status_code}")

        print("\n  Elasticsearch logs population complete!")

    except requests.RequestException as e:
        print(f"\n  Error connecting to Elasticsearch: {e}")
        print("\n  Make sure Elasticsearch is running:")
        print("    docker-compose up -d elasticsearch")


def populate_oracle_database(db_path: str = None):
    """Populate Oracle database (SQLite) with sample data."""
    print("\n" + "="*60)
    print("Populating Oracle Database (SQLite)")
    print("="*60)

    if db_path is None:
        db_path = get_db_path()

    try:
        engine = create_sample_database(db_path)
        print("  Oracle database populated successfully!")
        print("\n  Database contains:")
        print("    - 4 applications")
        print("    - 12 performance thresholds")
        print("    - 4 historical incidents")

    except Exception as e:
        print(f"  Error populating Oracle database: {e}")


def main():
    """Run all population scripts."""
    print("\n" + "="*60)
    print("DUMMY DATA POPULATION SCRIPT (Enhanced)")
    print("="*60)
    print("\nThis script will populate test data into:")
    print("  1. Oracle Database (SQLite) - Base tables")
    print("  2. Oracle Database (SQLite) - Baselines & Patterns (precomputed)")
    print("  3. Prometheus (via Pushgateway) - Current metrics")
    print("  4. Elasticsearch - Application logs")
    print("\n" + "="*60)

    # Get database path
    db_path = get_db_path()

    # Populate Oracle base tables (always works, local SQLite)
    populate_oracle_database(db_path)

    # Precompute baselines (this is the new enhanced part)
    precompute_all_baselines(db_path, days=120)

    # Populate Elasticsearch
    populate_elasticsearch_logs()

    # Populate Prometheus (current metrics)
    populate_prometheus_metrics()

    print("\n" + "="*60)
    print("DATA POPULATION COMPLETE!")
    print("="*60)
    print("\nThe following data is now available:")
    print("  - Current metrics in Prometheus (CPU, memory, latency, errors, availability)")
    print("  - 120 days of historical baselines in SQLite")
    print("  - Traffic patterns by hour and day of week")
    print("  - Availability statistics (24h, 7d, 30d)")
    print("  - Application logs in Elasticsearch")
    print("\nTest queries to try:")
    print("  - 'What is the current CPU usage for all applications?'")
    print("  - 'Is the latency for payment-gateway abnormal compared to the 30-day baseline?'")
    print("  - 'What are the peak traffic times for user-service?'")
    print("  - 'What is the availability for notification-service over the past 7 days?'")
    print("  - 'Show me recent errors from payment-gateway'")
    print()


if __name__ == "__main__":
    main()
