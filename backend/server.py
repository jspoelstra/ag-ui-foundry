# Copyright (c) Microsoft. All rights reserved.

"""Example FastAPI server with AG-UI endpoints."""

from __future__ import annotations

import argparse
import logging
import os
from typing import cast

from dotenv import load_dotenv

import uvicorn
from agent_framework.ag_ui import add_agent_framework_fastapi_endpoint
from agent_framework.azure import AzureOpenAIChatClient, AzureOpenAIResponsesClient
from azure.identity import DefaultAzureCredential
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.foundry_agent import foundry_agent
from backend.local_agent import local_agent


load_dotenv()  # Load environment variables from .env file if present

# Configure logging to file and console (disabled by default - set ENABLE_DEBUG_LOGGING=1 to enable)
if os.getenv("ENABLE_DEBUG_LOGGING"):
    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log", "server.log")

    # Remove any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Configure new handlers
    file_handler = logging.FileHandler(log_file, mode="w")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.INFO)

    # Explicitly set log levels for our modules
    logging.getLogger("agent_framework_ag_ui").setLevel(logging.INFO)
    logging.getLogger("agent_framework").setLevel(logging.INFO)

    logger = logging.getLogger(__name__)
    logger.info(f"AG-UI Examples Server starting... Logs writing to: {log_file}")


def create_app(agent_kind: str | None = None) -> FastAPI:
    app = FastAPI(title="Agent Framework AG-UI Server")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    selected_agent = (agent_kind or os.getenv("AGENT_KIND", "local")).strip().lower()
    if selected_agent == "foundry":
        agent = foundry_agent()
    else:
        agent = local_agent(_create_local_client())

    add_agent_framework_fastapi_endpoint(
        app=app,
        agent=agent,
        path="/ag-ui",
    )

    # Optional root endpoint for health check
    @app.get("/")
    async def root():
        return {
            "status": "running",
            "message": "AG-UI endpoint available at /ag-ui",
            "agent": selected_agent,
        }

    return app


def _create_local_client():
    responses_deployment = os.getenv("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME", "").strip()
    project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "").strip()

    if responses_deployment and project_endpoint:
        credential = DefaultAzureCredential()
        return AzureOpenAIResponsesClient(
            project_endpoint=project_endpoint,
            deployment_name=responses_deployment,
            credential=credential,
        )

    return AzureOpenAIChatClient()


app = create_app()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the AG-UI server.")
    parser.add_argument(
        "--agent",
        choices=("local", "foundry"),
        help="Select which agent backend to use.",
    )
    return parser.parse_args()


def main():
    """Run the server."""
    args = _parse_args()
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"\nAG-UI Server starting on http://{host}:{port}")
    print("Set ENABLE_DEBUG_LOGGING=1 for detailed request logging\n")

    # Use log_config=None to prevent uvicorn from reconfiguring logging
    # This preserves our file + console logging setup
    uvicorn.run(
        create_app(args.agent),
        host=host,
        port=port,
        log_config=None,
    )


if __name__ == "__main__":
    main()