"""
Flask-SocketIO application for natural language observability queries.
Integrates LlamaIndex agent with WebSocket progress streaming.
"""
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import eventlet
import os
from agent import ObservabilityAgent

# Monkey patch for eventlet
eventlet.monkey_patch()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Global agent instance
agent = None


def progress_callback(progress_data):
    """Callback function to emit progress updates via WebSocket."""
    socketio.emit('progress', progress_data)
    eventlet.sleep(0)  # Allow other greenlets to run


@app.route('/')
def index():
    """Render the main chat interface."""
    return render_template('index.html')


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    global agent
    print('Client connected')
    
    try:
        # Initialize agent on first connection if not already initialized
        if agent is None:
            emit('status', {'message': 'Initializing agent...', 'type': 'info'})
            
            # Check for OpenAI API key
            api_key = os.environ.get('OPENAI_API_KEY')
            if not api_key:
                emit('status', {
                    'message': 'Warning: OPENAI_API_KEY not set. Please set it to use the agent.',
                    'type': 'warning'
                })
                return
            
            agent = ObservabilityAgent(
                openai_api_key=api_key,
                progress_callback=progress_callback,
                verbose=True
            )
        
        emit('status', {'message': 'Connected to server. Agent ready.', 'type': 'success'})
        
    except Exception as e:
        emit('status', {
            'message': f'Error initializing agent: {str(e)}',
            'type': 'error'
        })


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    print('Client disconnected')


@socketio.on('query')
def handle_query(data):
    """
    Handle natural language query requests from the client.
    Uses LlamaIndex agent to orchestrate queries across data sources.
    Emits progress updates for each step.
    """
    global agent
    
    query = data.get('query', '')
    
    if not query:
        emit('error', {
            'message': 'Empty query received',
            'type': 'error',
            'reasoning': 'Please provide a valid query'
        })
        return
    
    try:
        # Check if agent is initialized
        if agent is None:
            emit('error', {
                'message': 'Agent not initialized. Please check OPENAI_API_KEY.',
                'type': 'error',
                'reasoning': 'Cannot process query without initialized agent'
            })
            return
        
        # Process query through agent
        # Agent will emit progress updates via the callback
        response = agent.query(query)
        
        # Emit final result
        emit('result', {
            'message': 'Query processing complete',
            'response': response,
            'query': query,
            'reasoning': 'Successfully synthesized response from all relevant data sources'
        })
        
    except Exception as e:
        # Handle errors via WebSocket events
        import traceback
        error_details = traceback.format_exc()
        print(f"Error processing query: {error_details}")
        
        emit('error', {
            'message': f'Error processing query: {str(e)}',
            'type': 'error',
            'reasoning': 'An unexpected error occurred during query processing',
            'details': error_details if app.debug else None
        })


@socketio.on('reset')
def handle_reset():
    """Reset agent conversation history."""
    global agent
    
    try:
        if agent:
            agent.reset()
            emit('status', {
                'message': 'Agent conversation reset',
                'type': 'success'
            })
    except Exception as e:
        emit('error', {
            'message': f'Error resetting agent: {str(e)}',
            'type': 'error'
        })


if __name__ == '__main__':
    # Initialize database on startup
    from oracle_db import create_sample_database
    print("Initializing sample database...")
    create_sample_database()
    print("Database ready!")
    
    print("\n" + "="*60)
    print("JAR - Just Another RAG - Natural Language Observability")
    print("="*60)
    print("Starting Flask-SocketIO server...")
    print("Set OPENAI_API_KEY environment variable to use the agent")
    print("="*60 + "\n")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
