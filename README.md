# Orchestrator

The Orchestrator coordinates four specialized CustomGPT agents to deliver a cohesive response to user prompts. It receives incoming chat messages, fans them out to the registered agents, stitches together their replies, and streams the aggregated answer back to the caller. This document captures everything you need to set up the project locally and understand the typical runtime flow.

## Prerequisites

Before cloning the repository, ensure you have the following tooling installed:

- **Python 3.11 or later** – the web service and orchestration logic are implemented in Python.
- **Poetry 1.6+** – used for dependency management and virtual environment isolation.
- **Node.js 18+ (optional)** – required only when you want to run the companion web UI for manual testing.
- **Make (optional)** – convenience wrapper for common developer commands.
- **CustomGPT account** – you will need an API key and four agent project IDs to let the orchestrator talk to your deployed agents.

## Project structure

A typical checkout looks like the tree below. Source files live under `src/orchestrator`, while integration and unit tests sit in `tests/`.

```
.
├── README.md
├── pyproject.toml
├── poetry.lock
├── src/
│   └── orchestrator/
│       ├── __init__.py
│       ├── config.py
│       ├── main.py
│       ├── router.py
│       ├── clients/
│       │   └── customgpt.py
│       └── agents/
│           ├── researcher.py
│           ├── planner.py
│           ├── builder.py
│           └── reviewer.py
└── tests/
    ├── __init__.py
    ├── test_routes.py
    └── test_agents.py
```

> **Note:** File names can evolve as the service grows, but the layout above highlights the major concepts—configuration, HTTP entrypoints, CustomGPT adapters, and the four agent specializations.

## Installation

Clone the repository and install dependencies with Poetry:

```bash
git clone https://github.com/your-org/orchestrator.git
cd orchestrator
poetry install
```

If you prefer to work inside a dedicated shell, spawn it with:

```bash
poetry shell
```

Developers who do not want to use Poetry can fall back to `pip` by exporting the lock file:

```bash
poetry export -f requirements.txt --output requirements.txt
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment configuration

All runtime credentials live in environment variables so that secrets never end up in source control. Create a `.env` file in the project root (the same directory as `pyproject.toml`) with the variables below:

```dotenv
CUSTOMGPT_API_KEY=sk-your-api-key
RESEARCH_AGENT_PROJECT_ID=proj-xxxxxxxx-researcher
PLANNING_AGENT_PROJECT_ID=proj-xxxxxxxx-planner
BUILDER_AGENT_PROJECT_ID=proj-xxxxxxxx-builder
REVIEW_AGENT_PROJECT_ID=proj-xxxxxxxx-reviewer
ORCHESTRATOR_BASE_URL=http://localhost:8000
ORCHESTRATOR_LOG_LEVEL=info
```

Finally, load those settings before starting the application:

```bash
cp .env.example .env  # if the template exists
poetry run python -m orchestrator.config --check
```

The `--check` command validates that your API key and agent IDs are present and well formed.

## Running the development server

Launch the FastAPI application with Uvicorn:

```bash
poetry run uvicorn orchestrator.main:app --reload --port 8000
```

The server exposes both a REST endpoint at `POST /v1/chat` and a WebSocket stream at `ws://localhost:8000/v1/chat/stream`. If you are using the optional web UI, run its development server in a second terminal:

```bash
npm install
npm run dev
```

## Running tests

Execute the automated test suite with:

```bash
poetry run pytest
```

To include type checks and style linters, run the aggregated quality gate:

```bash
poetry run task lint
poetry run task typecheck
```

## Usage

The orchestrator expects each incoming chat turn to contain a `conversation_id`, `messages`, and optional `context` payload. Below is a sample cURL invocation showing a multi-step conversation:

```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CUSTOMGPT_API_KEY" \
  -d '{
        "conversation_id": "demo-123",
        "messages": [
          {"role": "user", "content": "Draft a blog post about sustainable architecture trends."}
        ],
        "context": {
          "tone": "informative",
          "length": "800 words"
        }
      }'
```

Behind the scenes, the orchestrator executes the following workflow for every user prompt:

1. **Research Agent** receives the raw prompt and optional context, performs knowledge retrieval, and posts a structured summary with citations.
2. **Planning Agent** consumes the research summary, designs an outline, and defines the tasks required to fulfill the request.
3. **Builder Agent** converts the plan into a full draft, obeying the tone, length, and formatting instructions included in the conversation context.
4. **Reviewer Agent** scores the builder output, flags inconsistencies or policy violations, and proposes inline edits.
5. The orchestrator merges the reviewer feedback back into the builder draft, assembles metadata (sources, review comments, token usage), and returns a unified response payload to the caller.

For conversational sessions, subsequent turns include the orchestrator's previous reply in the `messages` array. The service automatically replays the last exchange to each agent so that they operate with the same context. When streaming via WebSockets, you will observe incremental updates from each agent as they complete their respective subtask, followed by the orchestrator's final `complete` event.

With the prerequisites, configuration, and commands above, you can start the development server, iterate on the orchestration logic, and run the automated checks with confidence.
