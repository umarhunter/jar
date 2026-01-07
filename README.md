# JAR - Just Another RAG

Natural Language Observability Query System - A proof-of-concept system that allows users to query application health and performance metrics using natural language, with responses synthesized from multiple monitoring data sources.

## Overview

JAR uses LlamaIndex with ReActAgent to orchestrate queries across multiple data sources:
- **Oracle Database** (simulated with SQLite) - Application configuration, thresholds, and historical incidents
- **Prometheus** - Real-time metrics (CPU, memory, request rates, errors, latency)
- **Elasticsearch** - Application logs and error traces (mock mode enabled, real integration optional)

### Example Queries

- "How is user-service performing right now?"
- "What's the CPU usage?"
- "Are there any errors in the last 30 minutes?"
- "What applications are we monitoring?"
- "What is the memory threshold for payment-gateway?"
- "Show me recent incidents"
- "Show me recent error logs"
- "What errors occurred in the last hour?"
- "Are there any authentication failures?"

## Features

- 🤖 **Natural Language Queries**: Ask questions in plain English
- 🔄 **Real-time Progress Streaming**: See which databases are being queried via WebSocket
- 🧠 **Agent Reasoning**: Transparent view of agent's decision-making process
- 📊 **Multi-source Synthesis**: Combines data from Oracle, Prometheus, and Elasticsearch
- 🎨 **Clean UI**: Native HTML/CSS/JS with Socket.IO
- 📝 **Log Analysis**: Query and analyze application logs and error traces

## Architecture

```
User Query (Natural Language)
    ↓
LlamaIndex ReActAgent
    ↓
┌─────────────┬──────────────────┬──────────────────┐
│             │                  │                  │
Oracle DB     Prometheus      Elasticsearch
(Config)      (Metrics)          (Logs)
    │             │                  │
    └─────────────┴──────────────────┘
                  ↓
         Synthesized Response
```

## Setup

### Prerequisites

- Python 3.8+
- OpenAI API key (for LLM)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/umarhunter/jar.git
cd jar
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set your OpenAI API key:
```bash
export OPENAI_API_KEY='your-api-key-here'
```

Or create a `.env` file:
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

4. Run the application:
```bash
python app.py
```

5. Open your browser to `http://localhost:5000`

### Docker Setup (Recommended)

The easiest way to run JAR is using Docker Compose:

1. Clone the repository:
```bash
git clone https://github.com/umarhunter/jar.git
cd jar
```

2. Create a `.env` file with your OpenAI API key:
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

3. Start the application:
```bash
docker compose up --build
```

4. Open your browser to `http://localhost:5000`

The application will:
- Build the Docker image automatically
- Start the Flask-SocketIO server on port 5000
- Persist the SQLite database in a Docker volume
- Automatically restart if the container stops

To stop the application:
```bash
docker compose down
```

To stop and remove the database volume:
```bash
docker compose down -v
```

### Development with Docker

For development with live code reloading, uncomment the volume mount in [docker-compose.yml](docker-compose.yml):
```yaml
volumes:
  - jar_data:/app/data
  - .:/app  # Uncomment this line
```

Then restart the container:
```bash
docker compose up --build
```

## Project Structure

```
jar/
├── app.py                  # Flask-SocketIO server
├── agent.py                # LlamaIndex ReActAgent orchestrator
├── oracle_db.py            # Oracle database setup (SQLite)
├── prometheus_engine.py    # Custom Prometheus query engine
├── elasticsearch_engine.py # Custom Elasticsearch query engine
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker container configuration
├── docker-compose.yml      # Docker Compose orchestration
├── templates/
│   └── index.html         # Frontend HTML
├── static/
│   ├── style.css          # Styles
│   └── app.js             # Socket.IO client
└── README.md
```

## How It Works

1. **User submits natural language query** via web interface
2. **Flask-SocketIO receives query** and passes to LlamaIndex agent
3. **ReActAgent analyzes query** and determines which tools to use
4. **Agent queries data sources**:
   - Oracle (via NLSQLTableQueryEngine) for configuration/thresholds
   - Prometheus (via custom engine) for real-time metrics
   - Elasticsearch (via custom engine) for logs and error traces
5. **Progress updates streamed** via WebSocket to frontend
6. **Agent synthesizes response** combining all data sources
7. **Natural language response** displayed to user

## Sample Data

The pilot phase includes sample data:
- 4 applications (user-service, payment-gateway, notification-service, analytics-engine)
- Performance thresholds for each application
- Historical incidents
- Mock Prometheus metrics
- Mock Elasticsearch logs and error traces

## Development

### Running in Debug Mode

```bash
python app.py
```

The app runs with Flask debug mode enabled by default.

### Enabling Real Elasticsearch

To use a real Elasticsearch instance instead of mock data:

1. Uncomment the Elasticsearch service in [docker-compose.yml](docker-compose.yml)
2. Uncomment the environment variables in the `jar` service
3. Uncomment the `depends_on` section
4. Modify [elasticsearch_engine.py](elasticsearch_engine.py) to connect to real Elasticsearch:
   - Set `mock_mode=False`
   - Implement `_query_elasticsearch_api()` method with actual Elasticsearch client calls
5. Restart with `docker compose up --build`

### Extending Data Sources

To add new data sources:

1. Create a custom query engine class (see [prometheus_engine.py](prometheus_engine.py) or [elasticsearch_engine.py](elasticsearch_engine.py) as examples)
2. Wrap it as a QueryEngineTool
3. Add to agent in [agent.py](agent.py)

## Limitations (Pilot Phase)

- Uses mock data for Prometheus and Elasticsearch (no actual connections by default)
- SQLite simulates Oracle database
- Single-user (no authentication)
- Mock data generation for logs and metrics

## Future Enhancements

- [ ] Real Prometheus API integration
- [ ] Real Elasticsearch API integration (currently using mock data)
- [ ] User authentication
- [ ] Query history
- [ ] Saved queries
- [ ] Dashboard visualizations
- [ ] Multi-tenancy support
- [ ] Advanced log filtering and aggregation
- [ ] Alerting based on query results

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please open an issue or PR.

