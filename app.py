"""
Flask-SocketIO application for streaming agent progress updates.
"""
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import eventlet
import time
import random

# Monkey patch for eventlet
eventlet.monkey_patch()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')


@app.route('/')
def index():
    """Render the main chat interface."""
    return render_template('index.html')


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print('Client connected')
    emit('status', {'message': 'Connected to server', 'type': 'success'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    print('Client disconnected')


@socketio.on('query')
def handle_query(data):
    """
    Handle query requests from the client.
    Simulates querying Oracle, Prometheus, and Elasticsearch.
    Emits progress updates for each step.
    """
    query = data.get('query', '')
    
    try:
        # Emit initial acknowledgment
        emit('progress', {
            'step': 'started',
            'message': f'Processing query: "{query}"',
            'source': None,
            'reasoning': 'Initializing query processing and planning data retrieval strategy'
        })
        eventlet.sleep(0.5)
        
        # Step 1: Query Oracle for configuration
        emit('progress', {
            'step': 'oracle_start',
            'message': 'Querying Oracle database for application configuration and thresholds...',
            'source': 'oracle',
            'reasoning': 'Retrieving baseline configuration to determine acceptable performance thresholds'
        })
        eventlet.sleep(1)
        
        # Simulate Oracle query results
        oracle_results = {
            'cpu_threshold': '80%',
            'memory_threshold': '85%',
            'response_time_threshold': '500ms'
        }
        emit('progress', {
            'step': 'oracle_complete',
            'message': f'Oracle query complete. Retrieved thresholds: {oracle_results}',
            'source': 'oracle',
            'reasoning': 'Successfully obtained threshold configuration for performance evaluation',
            'data': oracle_results
        })
        eventlet.sleep(0.5)
        
        # Step 2: Query Prometheus for metrics
        emit('progress', {
            'step': 'prometheus_start',
            'message': 'Querying Prometheus for CPU metrics and performance data...',
            'source': 'prometheus',
            'reasoning': 'Gathering real-time metrics to compare against configured thresholds'
        })
        eventlet.sleep(1.5)
        
        # Simulate Prometheus query results
        prometheus_results = {
            'cpu_usage': f'{random.randint(60, 95)}%',
            'memory_usage': f'{random.randint(70, 90)}%',
            'request_count': random.randint(1000, 5000),
            'avg_response_time': f'{random.randint(200, 600)}ms'
        }
        emit('progress', {
            'step': 'prometheus_complete',
            'message': f'Prometheus query complete. Current metrics: {prometheus_results}',
            'source': 'prometheus',
            'reasoning': 'Metrics retrieved successfully. Analyzing performance against thresholds',
            'data': prometheus_results
        })
        eventlet.sleep(0.5)
        
        # Step 3: Query Elasticsearch for logs
        emit('progress', {
            'step': 'elasticsearch_start',
            'message': 'Checking error logs in Elasticsearch...',
            'source': 'elasticsearch',
            'reasoning': 'Searching for error patterns and anomalies in application logs'
        })
        eventlet.sleep(1.2)
        
        # Simulate Elasticsearch query results
        error_count = random.randint(0, 50)
        elasticsearch_results = {
            'error_count': error_count,
            'warning_count': random.randint(10, 100),
            'recent_errors': [
                'Connection timeout in service A',
                'Database query exceeded threshold',
                'Memory allocation warning'
            ] if error_count > 20 else []
        }
        emit('progress', {
            'step': 'elasticsearch_complete',
            'message': f'Elasticsearch query complete. Found {error_count} errors.',
            'source': 'elasticsearch',
            'reasoning': 'Log analysis complete. Identifying critical issues and patterns',
            'data': elasticsearch_results
        })
        eventlet.sleep(0.5)
        
        # Final analysis
        emit('progress', {
            'step': 'analysis',
            'message': 'Analyzing collected data and generating insights...',
            'source': None,
            'reasoning': 'Correlating metrics, thresholds, and logs to provide actionable recommendations'
        })
        eventlet.sleep(1)
        
        # Generate summary
        cpu_over_threshold = int(prometheus_results['cpu_usage'].rstrip('%')) > int(oracle_results['cpu_threshold'].rstrip('%'))
        memory_over_threshold = int(prometheus_results['memory_usage'].rstrip('%')) > int(oracle_results['memory_threshold'].rstrip('%'))
        
        summary = {
            'query': query,
            'status': 'warning' if (cpu_over_threshold or memory_over_threshold or error_count > 20) else 'healthy',
            'findings': []
        }
        
        if cpu_over_threshold:
            summary['findings'].append(f"⚠️ CPU usage ({prometheus_results['cpu_usage']}) exceeds threshold ({oracle_results['cpu_threshold']})")
        if memory_over_threshold:
            summary['findings'].append(f"⚠️ Memory usage ({prometheus_results['memory_usage']}) exceeds threshold ({oracle_results['memory_threshold']})")
        if error_count > 20:
            summary['findings'].append(f"⚠️ High error count detected: {error_count} errors")
        
        if not summary['findings']:
            summary['findings'].append('✅ All systems operating within normal parameters')
        
        emit('result', {
            'message': 'Query processing complete',
            'summary': summary,
            'reasoning': 'Analysis complete. All data sources have been queried and evaluated'
        })
        
    except Exception as e:
        # Handle errors via WebSocket events
        emit('error', {
            'message': f'Error processing query: {str(e)}',
            'type': 'error',
            'reasoning': 'An unexpected error occurred during query processing'
        })


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
