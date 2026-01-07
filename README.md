# JAR - Just Another RAG

Natural Language Observability Query System - A proof-of-concept system that allows users to query application health and performance metrics using natural language, with responses synthesized from multiple monitoring data sources.

## Overview

JAR uses LlamaIndex with ReActAgent to orchestrate queries across multiple data sources:
- **Oracle Database** (simulated with SQLite) - Application configuration, thresholds, and historical incidents
- **Prometheus** - Real-time metrics (CPU, memory, request rates, errors, latency)
- **Elasticsearch** - Application logs and error traces (planned for phase 2)

### Example Queries

- "How is user-service performing right now?"
- "What's the CPU usage?"
- "Are there any errors in the last 30 minutes?"
- "What applications are we monitoring?"
- "What is the memory threshold for payment-gateway?"
- "Show me recent incidents"

## Features

- 🤖 **Natural Language Queries**: Ask questions in plain English
- 🔄 **Real-time Progress Streaming**: See which databases are being queried via WebSocket
- 🧠 **Agent Reasoning**: Transparent view of agent's decision-making process
- 📊 **Multi-source Synthesis**: Combines data from Oracle and Prometheus
- 🎨 **Clean UI**: Native HTML/CSS/JS with Socket.IO

## Architecture

```
User Query (Natural Language)
    ↓
LlamaIndex ReActAgent
    ↓
┌─────────────┬──────────────────┐
│             │                  │
Oracle DB     Prometheus      Elasticsearch
(Config)      (Metrics)       (Logs - Phase 2)
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
├── requirements.txt        # Python dependencies
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
5. **Progress updates streamed** via WebSocket to frontend
6. **Agent synthesizes response** combining all data sources
7. **Natural language response** displayed to user

## Sample Data

The pilot phase includes sample data:
- 4 applications (user-service, payment-gateway, notification-service, analytics-engine)
- Performance thresholds for each application
- Historical incidents
- Mock Prometheus metrics

## Development

### Running in Debug Mode

```bash
python app.py
```

The app runs with Flask debug mode enabled by default.

### Extending Data Sources

To add new data sources (e.g., Elasticsearch):

1. Create a custom query engine class (see `prometheus_engine.py` as example)
2. Wrap it as a QueryEngineTool
3. Add to agent in `agent.py`

## Limitations (Pilot Phase)

- Uses mock data for Prometheus (no actual Prometheus connection)
- SQLite simulates Oracle database
- Elasticsearch not yet implemented
- Single-user (no authentication)

## Future Enhancements

- [ ] Real Prometheus API integration
- [ ] Elasticsearch query engine
- [ ] User authentication
- [ ] Query history
- [ ] Saved queries
- [ ] Dashboard visualizations
- [ ] Multi-tenancy support

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please open an issue or PR.

