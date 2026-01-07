"""
Test real-time streaming of progress updates.
"""
from jar.agent import ObservabilityAgent
import time

def progress_handler(data):
    """Print progress updates as they arrive."""
    timestamp = time.strftime("%H:%M:%S")
    source = data.get('source') or 'system'
    print(f"[{timestamp}] {source:15s} | {data['step']:20s} | {data['message']}")

def main():
    print("="*80)
    print("Testing Real-Time Progress Streaming")
    print("="*80)

    print("\nInitializing agent with progress callback...")
    agent = ObservabilityAgent(progress_callback=progress_handler, verbose=False)

    print("\n" + "="*80)
    print("Sending Query: 'Show me recent errors'")
    print("="*80 + "\n")

    response = agent.query("Show me recent errors")

    print("\n" + "="*80)
    print("FINAL RESPONSE:")
    print("="*80)
    print(response)

if __name__ == "__main__":
    main()
