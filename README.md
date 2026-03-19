---
title: AG-UI Foundry v2 Example
description: Example server integrating AG-UI with Azure AI Foundry v2 agents using Microsoft Agent Framework.
author: Microsoft
ms.date: 2026-02-24
ms.topic: overview
keywords:
  - ag-ui
  - azure ai foundry
  - agents
  - fastapi
  - agent framework
estimated_reading_time: 3
---

## Overview

Integrate AG-UI with Azure AI Foundry v2 agents using a FastAPI server and Microsoft Agent Framework. The backend can run either a Foundry-backed agent or a local agent that calls a Foundry agent as a tool, exposing both through an AG-UI endpoint.

## Repository structure

* `backend/` contains the Python backend:
	* `backend/server.py`
	* `backend/scripts/update_foundry_agent.py`
	* `backend/requirements.txt`
* `frontend/` contains the Next.js and CopilotKit UI.

## Prerequisites

* Python and pip
* An Azure AI Foundry project with a published agent
* Azure authentication via Azure CLI or environment-based credentials

## Setup

1. Install dependencies.

	```bash
	pip install -r backend/requirements.txt
	```

2. Configure environment variables. You can use a `.env` file or export them in your shell. Start with `env.sample` and fill in your values.

	```bash
	export AGENT_KIND="local"
	# Use the project endpoint (do not include /openai/v1 or /responses).
	export AZURE_AI_PROJECT_ENDPOINT="https://your-project-name.services.ai.azure.com/api/projects/your-project-name"
	export AZURE_AI_PROJECT_AGENT_NAME="AgentSmith"
	# Optional: export AZURE_AI_PROJECT_AGENT_VERSION="1.0"
	# Optional: export AZURE_AI_PROJECT_AGENT_DESCRIPTION="Ask the Foundry agent a question"
	# Local agent uses Foundry's OpenAI-compatible responses endpoint by default.
	# Uses Entra ID auth (no API key).
	export AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME="gpt-5-mini"

	# Legacy Azure OpenAI chat (API key auth)
	# export AZURE_OPENAI_CHAT_DEPLOYMENT_NAME="gpt-5-mini"
	# export AZURE_OPENAI_ENDPOINT="https://your-resource-name.cognitiveservices.azure.com/openai/deployments/gpt-5-mini/chat/completions?api-version=2024-05-01-preview"
	# export AZURE_OPENAI_API_KEY="your-azure-openai-api-key"
	# Optional frontend UI text
	export NEXT_PUBLIC_AGENT_NAME="ag-ui"
	export NEXT_PUBLIC_IMPROVE_BUTTON_LABEL="Improve with AI"
	export NEXT_PUBLIC_IMPROVE_PROMPT="Improve the project"
	```

Frontend environment variable loading order:

* Values in `frontend/.env.local` and other Next.js `frontend/.env*` files are loaded first by Next.js.
* Missing values fall back to the repository root `.env` file.
* Existing values are never overridden by fallback loading.

Use `NEXT_PUBLIC_` prefixes for any values the browser must read.

3. Sign in to Azure if you are using Azure CLI credentials.

	```bash
	az login
	```

## Run the server

You can run the backend with either agent implementation.

* `local` uses a Foundry model deployment (responses endpoint) when configured, and calls the Foundry agent through the `ask_foundry` tool.
* `foundry` loads the agent directly from Foundry.

```bash
python -m backend.server --agent local
```

Or set the default in your environment:

```bash
export AGENT_KIND="foundry"
python -m backend.server
```

The server runs on <http://localhost:8000>. The AG-UI endpoint is available at <http://localhost:8000/ag-ui>.

To update the Foundry agent tools:

```bash
python backend/scripts/update_foundry_agent.py --endpoint "https://<account>.services.ai.azure.com/api/projects/<project>" --agent-name "AgentSmith"
```

## Run the frontend

The frontend is a minimal Next.js app that uses CopilotKit and proxies AG-UI requests through a local API route.

1. Install Node dependencies.

	```bash
	npm run install:frontend
	```

2. Start the Next.js dev server.

	```bash
	npm run dev:frontend
	```

3. Open <http://localhost:3000>.

By default, the CopilotKit route proxies to <http://localhost:8000/ag-ui>. To change it, set `AG_UI_ENDPOINT` in your environment before running the frontend.

You can set frontend variables in either location:

* `frontend/.env.local` for frontend-only overrides
* root `.env` for shared backend and frontend values

You can also configure the improve button text and the prompt it sends:

* `NEXT_PUBLIC_AGENT_NAME` controls the frontend Copilot agent name.
* `NEXT_PUBLIC_IMPROVE_BUTTON_LABEL` controls the button label.
* `NEXT_PUBLIC_IMPROVE_PROMPT` controls the user message sent when the button is clicked.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     BROWSER (localhost:3000)                        │
│                                                                     │
│  ┌──────────────────────────────┐  ┌────────────────────────────┐  │
│  │        ProjectCard           │  │       CopilotChat          │  │
│  │                              │  │                            │  │
│  │  - Project name              │  │  "AI Project Assistant"    │  │
│  │  - Description               │  │                            │  │
│  │  - Location (country, dist,  │  │  User messages ──────>    │  │
│  │    lat, long)                │  │  <────── Agent replies     │  │
│  │  - Components [{type, desc,  │  │  (streaming)               │  │
│  │    env_impact}]              │  │                            │  │
│  │                              │  │                            │  │
│  │  useCoAgent() <── state ──> useCopilotChat()                │  │
│  │  (bidirectional sync)        │  │                            │  │
│  └──────────────────────────────┘  └────────────────────────────┘  │
│                           CopilotKit (AG-UI protocol)               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  HTTP (GraphQL)
                               v
┌─────────────────────────────────────────────────────────────────────┐
│              NEXT.JS API ROUTE (proxy)                              │
│              /api/copilotkit/[integrationId]/route.ts               │
│                                                                     │
│  - Extracts method & agentId from payload                          │
│  - Resolves aliases: ag-ui | librarian | gap-analyst               │
│  - Forwards to AG_UI_ENDPOINT                                      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  HTTP POST
                               v
┌─────────────────────────────────────────────────────────────────────┐
│              FASTAPI BACKEND (localhost:8000)                        │
│              POST /ag-ui  (agent-framework-ag-ui)                   │
│                                                                     │
│    ┌ - - - - AGENT_KIND env var selects mode - - - - - ┐           │
│                                                                     │
│    │ ┌─────────────────────┐   ┌──────────────────────┐│           │
│      │  LOCAL AGENT        │   │  FOUNDRY AGENT       │            │
│    │ │  (default)          │OR │                      ││           │
│      │                     │   │  Loaded at startup   │            │
│    │ │  AzureOpenAI Chat   │   │  from Azure AI       ││           │
│      │  Client (LLM)       │   │  Foundry project     │            │
│    │ └─────────┬───────────┘   └──────────┬───────────┘│           │
│                │                          │                        │
│    └ - - - - - ┼ - - - - - - - - - - - - -┼ - - - - - -┘           │
│                │                          │                        │
│                v                          v                        │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │  SHARED TOOLS (state.py)                                 │      │
│  │                                                          │      │
│  │  update_title(name)          update_location(location)   │      │
│  │  update_description(desc)    add_component(components)   │      │
│  │  update_info(project)        ask_agent(q) [local only]   │      │
│  │                                                          │      │
│  │  predict_state_config maps tool args -> state fields     │      │
│  └──────────────────────────────────────────────────────────┘      │
│                                                                     │
│  AgentFrameworkAgent wrapper -> streams state + text back           │
└────────────┬──────────────────────────────┬─────────────────────────┘
             │                              │
             v                              v
┌────────────────────────┐    ┌──────────────────────────────┐
│    Azure OpenAI        │    │    Azure AI Foundry          │
│                        │    │                              │
│  Chat Completions API  │    │  AIProjectClient (async)     │
│  (gpt-5-mini, etc.)   │    │  AzureAIProjectAgentProvider │
│                        │    │                              │
│  Used by: LOCAL agent  │    │  Used by: FOUNDRY agent      │
│  for LLM reasoning     │    │  + ask_agent() tool (LOCAL)  │
└────────────────────────┘    └──────────────────────────────┘
             │                              │
             └──────────┬───────────────────┘
                        v
             ┌─────────────────────┐
             │ DefaultAzureCredential
             │ (azure-identity)    │
             │                     │
             │ az login / env /    │
             │ managed identity    │
             └─────────────────────┘
```

**State flow:** User types in chat → Agent reasons (LLM) → Calls tool (e.g. `update_title`) → `predict_state_config` maps tool arg to state field → AG-UI streams state delta → Frontend `useCoAgent()` receives update → `ProjectCard` re-renders with visual ping on changed fields.

## Contributing

* Fork the repository and create a feature branch.
* Keep changes focused and add or update documentation as needed.
* Run the server locally to validate behavior.
* Open a pull request with a clear description of the change.
