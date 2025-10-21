# Orchestrator

This repository contains a sample multi-agent chat orchestrator that demonstrates how to route user prompts to multiple CustomGPT agents and present the combined responses in a single conversation UI.

## Frontend application

The React-based frontend lives in [`frontend/`](frontend/). It is built with Vite and TypeScript and provides a chat interface that can display responses from multiple agents simultaneously.

### Getting started

```bash
cd frontend
npm install
```

Create a `.env.local` file in the `frontend/` directory based on the provided example:

```bash
cp .env.example .env.local
```

Edit `.env.local` and set the `VITE_CUSTOMGPT_API_KEY` value. The key is injected at build time and never committed to the repository.

```ini
VITE_CUSTOMGPT_API_KEY=8605|e7w7KAmNu7U1hWewHyBDWgLqOeQAgzVOfcAfhBo16d20ba9b
```

### Available scripts

| Command | Description |
| --- | --- |
| `npm run dev` | Starts the Vite development server. |
| `npm run build` | Type-checks the project and bundles the production build. |
| `npm run preview` | Serves the built assets locally. |
| `npm run lint` | Runs ESLint against the source files. |

## Architecture overview

- **Services** – [`src/services/customgpt.ts`](frontend/src/services/customgpt.ts) wraps the CustomGPT API and ensures all requests include the project identifier and API key.
- **Orchestrator** – [`src/orchestrator/AgentRouter.ts`](frontend/src/orchestrator/AgentRouter.ts) routes incoming prompts to the appropriate CustomGPT agents (project IDs `83668`, `49501`, `37400`, and `9262`), aggregates their responses, and returns them to the UI.
- **UI** – [`src/components/ChatWindow.tsx`](frontend/src/components/ChatWindow.tsx) renders the conversation and handles user input while [`src/App.tsx`](frontend/src/App.tsx) coordinates the data flow.

## Environment variables

| Name | Description |
| --- | --- |
| `VITE_CUSTOMGPT_API_KEY` | API key used to authenticate requests to CustomGPT. Required for all chat interactions. |

Ensure the `.env.local` file is excluded from version control (Vite ignores local env files by default). The example file documents the required entries without leaking secrets.
