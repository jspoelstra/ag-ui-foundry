---
title: AG-UI Foundry v2 Example
description: Example server integrating AG-UI with Azure AI Foundry v2 agents using Microsoft Agent Framework.
author: Microsoft
ms.date: 2026-02-17
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

## Prerequisites

* Python and pip
* An Azure AI Foundry project with a published agent
* Azure authentication via Azure CLI or environment-based credentials

## Setup

1. Install dependencies.

	```bash
	pip install -r requirements.txt
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
python server.py
```

The server runs on <http://localhost:8000>. The AG-UI endpoint is available at <http://localhost:8000/ag-ui>.

## Contributing

* Fork the repository and create a feature branch.
* Keep changes focused and add or update documentation as needed.
* Run the server locally to validate behavior.
* Open a pull request with a clear description of the change.
