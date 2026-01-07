# JAR - Just Another RAG

Natural language query system for application observability. Ask questions about system health and performance metrics in plain English.

## Quick Start

```bash
# Clone and setup
git clone https://github.com/umarhunter/jar.git
cd jar
cp .env.example .env  # Add your OPENAI_API_KEY

# Run with Docker (recommended)
docker compose up --build

# Or run locally
pip install -r requirements.txt
export PYTHONPATH=$PWD/src
python src/jar/app.py
```

Access at `http://localhost:5001`

## Example Queries

- "How is user-service performing right now?"
- "What's the CPU usage?"
- "Are there any errors in the last 30 minutes?"
- "Show me recent error logs"

## Architecture

JAR uses LlamaIndex with FunctionAgent to query multiple data sources:
- **Oracle DB** (SQLite) - Configuration, thresholds, incidents
- **Prometheus** - Real-time metrics (CPU, memory, network)
- **Elasticsearch** - Application logs and error traces

```
User Query → LlamaIndex Agent → [Oracle | Prometheus | Elasticsearch] → Response
```

## Features

- Natural language queries via web interface
- Real-time progress streaming (WebSocket)
- Multi-source data synthesis
- Agent reasoning visibility
- Log analysis and error tracking

## Configuration

All services configured in `docker-compose.yml`:
- JAR app: port 5001
- Prometheus: port 9090
- Elasticsearch: port 9200
- Node Exporter: port 9100

## Project Structure

```
jar/
├── src/jar/                 # Main application package
│   ├── app.py              # Flask-SocketIO server
│   ├── agent.py            # LlamaIndex agent orchestrator
│   ├── engines/            # Query engines
│   │   ├── prometheus.py   # Prometheus query engine
│   │   ├── elasticsearch.py # Elasticsearch query engine
│   │   └── utils.py        # Shared utilities
│   └── database/           # Database layer
│       └── models.py       # Oracle DB models & setup
## Development

```bash
# Local development
export OPENAI_API_KEY='your-key'
export PYTHONPATH=$PWD/src
python src/jar/app.py

# Run tests
export PYTHONPATH=$PWD/src
python tests/test_agent.py

# Populate dummy data
export PYTHONPATH=$PWD/src
python scripts/populate_dummy_data.py

# Docker development (with live reload)
# Uncomment volume mount in docker-compose.yml
docker compose up --build
``` └── prometheus.yml
├── data/                    # Runtime data (gitignored)
├── docs/                    # Documentation
└── docker-compose.yml       # Service orchestration
```

## Development

```bash
# Local development
export OPENAI_API_KEY='your-key'
python app.py

# Docker development (with live reload)
# Uncomment volume mount in docker-compose.yml
docker compose up --build
```

Access monitoring tools:
- Oracle DB: `sqlite3 oracle.db` (SQLite simulating Oracle)
- Prometheus UI: http://localhost:9090
- Elasticsearch: http://localhost:9200

## License

MIT

