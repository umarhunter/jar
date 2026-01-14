#!/usr/bin/env python3
"""
Script to wipe all databases (SQLite, Elasticsearch, Prometheus Pushgateway)
without repopulating them.

Use this before running populate_dummy_data.py manually.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests


def wipe_databases():
    """Wipe all existing databases to start fresh."""
    print("\n" + "="*60)
    print("WIPING ALL DATABASES")
    print("="*60)

    # 1. Wipe SQLite database
    db_path = os.getenv('DATABASE_PATH', 'oracle_pilot.db')
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"  ✓ Deleted SQLite database: {db_path}")
    else:
        print(f"  ○ SQLite database not found: {db_path}")

    # 2. Wipe Elasticsearch index
    es_host = os.getenv('ELASTICSEARCH_HOST', 'http://localhost:9200')
    try:
        response = requests.delete(f"{es_host}/application_logs", timeout=5)
        if response.status_code in [200, 404]:
            print(f"  ✓ Deleted Elasticsearch index: application_logs")
        else:
            print(f"  ✗ Warning: Could not delete ES index: {response.status_code}")
    except requests.RequestException as e:
        print(f"  ✗ Warning: Could not connect to Elasticsearch: {e}")
        print(f"    Make sure Elasticsearch is running: docker-compose up -d elasticsearch")

    # 3. Clear Prometheus Pushgateway metrics
    pg_host = os.getenv('PUSHGATEWAY_URL', 'http://localhost:9091')
    try:
        # Delete all metrics from both jobs
        response1 = requests.delete(f"{pg_host}/metrics/job/observability_metrics", timeout=5)
        response2 = requests.delete(f"{pg_host}/metrics/job/test_metrics", timeout=5)
        print(f"  ✓ Cleared Prometheus Pushgateway metrics")
    except requests.RequestException as e:
        print(f"  ✗ Warning: Could not connect to Pushgateway: {e}")
        print(f"    Make sure Pushgateway is running: docker-compose up -d pushgateway")

    print("\n" + "="*60)
    print("DATABASE WIPE COMPLETE")
    print("="*60)
    print("\nNext steps:")
    print("  1. Run populate_dummy_data.py to generate fresh data:")
    print("     python scripts/populate_dummy_data.py")
    print()


if __name__ == "__main__":
    wipe_databases()
