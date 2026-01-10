"""
Flask-SocketIO application for natural language observability queries.
Integrates LlamaIndex agent with WebSocket progress streaming.
"""
import asyncio
import os

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from prometheus_client import make_wsgi_app
from dotenv import load_dotenv
from jar.agent import ObservabilityAgent
from jar.database.models import create_sample_database

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__,
            static_folder='web/static',
            template_folder='web/templates')
# Use environment variable for secret key, with secure random fallback for development
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Add Prometheus metrics endpoint
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})

# Global agent instance
agent = None


def progress_callback(progress_data):
    """Callback function to emit progress updates via WebSocket."""
    socketio.emit('progress', progress_data)
    # Force immediate flush in threading mode
    socketio.sleep(0)


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

            # Determine LLM provider
            llm_provider = os.environ.get('LLM_PROVIDER', 'openai').lower()

            if llm_provider == 'ollama':
                # Ollama mode - no API key needed
                ollama_model = os.environ.get('OLLAMA_MODEL', 'qwen2.5:14b')
                ollama_base_url = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')

                emit('status', {
                    'message': f'Using Ollama (offline mode) with model {ollama_model}',
                    'type': 'info'
                })

                agent = ObservabilityAgent(
                    llm_provider='ollama',
                    ollama_model=ollama_model,
                    ollama_base_url=ollama_base_url,
                    progress_callback=progress_callback,
                    verbose=True
                )
            else:
                # OpenAI mode - API key required
                api_key = os.environ.get('OPENAI_API_KEY')
                if not api_key:
                    emit('status', {
                        'message': 'Warning: OPENAI_API_KEY not set. Please set it or switch to Ollama (LLM_PROVIDER=ollama).',
                        'type': 'warning'
                    })
                    return

                emit('status', {
                    'message': 'Using OpenAI GPT-4o',
                    'type': 'info'
                })

                agent = ObservabilityAgent(
                    openai_api_key=api_key,
                    llm_provider='openai',
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
            llm_provider = os.environ.get('LLM_PROVIDER', 'openai').lower()
            error_msg = 'Agent not initialized. '
            if llm_provider == 'ollama':
                error_msg += 'Please check Ollama connection (OLLAMA_BASE_URL).'
            else:
                error_msg += 'Please check OPENAI_API_KEY.'

            emit('error', {
                'message': error_msg,
                'type': 'error',
                'reasoning': 'Cannot process query without initialized agent'
            })
            return
        
        # Process query through agent (streaming is always enabled)
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
    
    print("Initializing sample database...")
    create_sample_database()
    print("Database ready!")
    
    llm_provider = os.environ.get('LLM_PROVIDER', 'openai').lower()
    if llm_provider == 'ollama':
        print("LLM Provider: Ollama (offline mode)")
        print(f"Model: {os.environ.get('OLLAMA_MODEL', 'qwen2.5:14b')}")
        print(f"Base URL: {os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')}")
    else:
        print("LLM Provider: OpenAI")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
