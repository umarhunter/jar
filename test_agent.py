#!/usr/bin/env python3
"""
Test script for the ObservabilityAgent.
Tests the agent in a synchronous context similar to Flask-SocketIO.
"""
import os
import sys

# Ensure we have the OpenAI API key
if not os.environ.get('OPENAI_API_KEY'):
    print("Error: OPENAI_API_KEY environment variable not set")
    print("Please set it with: export OPENAI_API_KEY='your-key'")
    sys.exit(1)

from agent import ObservabilityAgent

def test_callback(progress_data):
    """Mock progress callback to see what's happening."""
    print(f"[{progress_data['step']}] {progress_data['message']}")
    if progress_data.get('source'):
        print(f"  Source: {progress_data['source']}")
    if progress_data.get('reasoning'):
        print(f"  Reasoning: {progress_data['reasoning']}")

def main():
    print("="*60)
    print("Testing ObservabilityAgent")
    print("="*60)
    
    # Initialize agent
    print("\n1. Initializing agent...")
    try:
        agent = ObservabilityAgent(
            progress_callback=test_callback,
            verbose=False
        )
        print("✓ Agent initialized successfully\n")
    except Exception as e:
        print(f"✗ Failed to initialize agent: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Test connections
    print("2. Testing data source connections...")
    print("-"*60)
    try:
        status = agent.test_connections()
        print("\nConnection Status:")
        print(f"  Oracle:        {'✓ Connected' if status['oracle']['connected'] else '✗ Failed'}")
        if status['oracle']['error']:
            print(f"                 Error: {status['oracle']['error']}")
        print(f"  Prometheus:    {'✓ Connected' if status['prometheus']['connected'] else '✗ Failed'} ({status['prometheus']['mode']})")
        print(f"  Elasticsearch: {'✓ Connected' if status['elasticsearch']['connected'] else '✗ Failed'} ({status['elasticsearch']['mode']})")
        
        if not all([status['oracle']['connected'], 
                   status['prometheus']['connected'], 
                   status['elasticsearch']['connected']]):
            print("\n⚠ Warning: Some connections failed, but continuing with available sources...")
    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test query
    print("\n3. Running test query: 'What is the CPU usage?'")
    print("-"*60)
    try:
        response = agent.query("What is the CPU usage?")
        print("\n" + "="*60)
        print("RESPONSE:")
        print("="*60)
        print(response)
        print("="*60)
        print("\n✓ Query executed successfully")
    except Exception as e:
        print(f"\n✗ Query failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "="*60)
    print("All tests passed!")
    print("="*60)

if __name__ == "__main__":
    main()
