"""
Test queries against the ObservabilityAgent with populated dummy data.

Usage:
  python test_queries.py              # Run all test queries
  python test_queries.py "your query" # Test a single query
"""
from jar.agent import ObservabilityAgent
import sys

def test_query(agent, query, show_header=True):
    """Test a single query and display the result."""
    if show_header:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)

    try:
        response = agent.query(query)
        print(f"\n{response}\n")
        return True
    except Exception as e:
        print(f"\n✗ Error: {e}\n")
        return False

def main():
    if len(sys.argv) > 1:
        # Single query mode
        query = " ".join(sys.argv[1:])
        print("Initializing agent...")
        agent = ObservabilityAgent(verbose=False)
        print(f"\nQuery: {query}")
        print("="*60)
        test_query(agent, query, show_header=False)
        return

    # Multi-query test mode
    print("="*60)
    print("ObservabilityAgent Query Tests")
    print("="*60)

    print("\nInitializing agent...")
    agent = ObservabilityAgent(verbose=False)
    print("✓ Agent initialized\n")

    # Quick tests for populated data
    test_queries = [
        "Show me recent errors",
        "What applications are being monitored?",
        "What are the performance thresholds for user-service?",
    ]

    results = []
    for query in test_queries:
        success = test_query(agent, query)
        results.append((query, success))

    # Summary
    print("="*60)
    successful = sum(1 for _, success in results if success)
    print(f"✓ {successful}/{len(results)} queries successful")
    print("="*60)

if __name__ == "__main__":
    main()
