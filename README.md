---
title: AG-UI Foundry v2 Example
description: Example server integrating AG-UI with Azure AI Foundry v2 agents using Microsoft Agent Framework.
author: Microsoft
ms.date: 2026-02-20
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

Integrate AG-UI with Azure AI Foundry v2 agents using a FastAPI server and Microsoft Agent Framework. The server loads an existing agent from your Foundry project and exposes it at an AG-UI endpoint.

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

2. Configure environment variables. You can use a `.env` file or export them in your shell.

	```bash
	export AZURE_AI_PROJECT_ENDPOINT="https://your-project-name.services.ai.azure.com/api/projects/your-project-name"
	export AZURE_AI_PROJECT_AGENT_NAME="AgentSmith"
	# Optional: export AZURE_AI_PROJECT_AGENT_VERSION="1.0"
	```

3. Sign in to Azure if you are using Azure CLI credentials.

	```bash
	az login
	```

## Run the server

```bash
python backend/server.py
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

## Contributing

* Fork the repository and create a feature branch.
* Keep changes focused and add or update documentation as needed.
* Run the server locally to validate behavior.
* Open a pull request with a clear description of the change.
