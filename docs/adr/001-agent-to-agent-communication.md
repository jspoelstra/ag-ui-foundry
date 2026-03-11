# ADR-001: Agent-to-Agent Communication Pattern

**Status:** Accepted  
**Date:** 2026-03-09  
**Deciders:** Jacob Spoelstra  

## Context

The ag-ui-foundry project has two agents:

- **Local agent** — runs in the AG-UI FastAPI server, backed by Azure OpenAI. Owns
  the project state and has tools to update it (`update_title`, `update_description`,
  `update_location`, `add_component`, `update_info`). Integrates with the frontend
  via AG-UI's `predict_state_config` for real-time state streaming.

- **Foundry agent** — hosted in Azure AI Foundry Agent Service. A research/knowledge
  agent that can answer domain questions (e.g., about renewable energy projects).

The local agent needs to delegate research questions to the Foundry agent and
incorporate the answers into project state updates. We evaluated three approaches for
this agent-to-agent communication.

## Decision Drivers

- Preserve dynamic routing: the local agent's LLM should decide *when* to delegate
- Maintain AG-UI state integration (`predict_state_config` and state streaming)
- Minimize architectural disruption
- Support a path toward richer multi-agent patterns in the future

## Options Considered

### Option 1: ConnectedAgentTool (Azure AI Foundry native)

`azure.ai.agents.models.ConnectedAgentTool` is the official Foundry mechanism for
agent-to-agent delegation. An orchestrator agent registers a sub-agent as a connected
tool; routing, context passing, and response handling happen server-side in the
Foundry Agent Service.

```python
from azure.ai.agents.models import ConnectedAgentTool

connected = ConnectedAgentTool(
    id=foundry_agent.id,
    name="research-agent",
    description="Researches questions about renewable energy projects",
)

orchestrator = project_client.agents.create_agent(
    model="gpt-4o",
    name="orchestrator",
    instructions="Delegate research to the research agent.",
    tools=connected.definitions + state_tools,
)
```

**Pros:**
- Native Foundry feature, server-side execution
- Automatic context management between agents
- The direction Azure AI Foundry is investing in

**Cons:**
- Both agents must be Foundry-hosted — the local agent would need to move from
  `Agent()` + `AzureOpenAIChatClient` to a Foundry-hosted agent
- Significant architecture change required
- Less control over the communication (opaque server-side handoff)
- Unclear how `predict_state_config` would work with a Foundry-hosted orchestrator

> **Update (2026-03-11) — Foundry-hosted agent with client-side tools: findings**
>
> We built and tested a hybrid variant of Option 1 in `foundry_agent.py`: a
> Foundry-hosted agent loaded via `AzureAIProjectAgentProvider.get_agent()` with
> the state-management tools (`update_title`, `update_description`, etc.) passed
> as client-side function tools. This proved that **client-side function tools on
> Foundry agents do work** — the Agent Framework registers tool definitions with
> the Foundry agent, intercepts tool calls locally, executes the functions, and
> submits results back via `submit_tool_outputs`. AG-UI's `predict_state_config`
> can intercept the tool call arguments and stream state updates to the frontend,
> exactly as it does for the local agent.
>
> However, we hit an **unsolved blocker**: when the Foundry agent also has
> server-side tool connections (in our case, MCP tools including a Foundry IQ
> knowledge base), the intermediate tool-call and tool-end events from those
> server-side tools leak through the AG-UI event stream. The client-side
> `AgentFrameworkAgent` receives `tool_call_end` events for tool calls it never
> initiated, causing AG-UI protocol errors ("tool-end message with no active tool
> call"). Extensive workaround attempts (filtering, event suppression) did not
> resolve the issue.
>
> This is the primary reason the project uses the "Foundry agent as tool"
> pattern (Option 3) rather than a Foundry-hosted orchestrator.
>
> **What would unblock this path:**
> - The Agent Framework or AG-UI adapter filtering out events for server-side-only
>   tool calls before they reach the AG-UI stream
> - The Foundry Agent Service providing a mode that suppresses tool events for
>   server-side tools when the caller is a client-side orchestrator
> - A clear separation in the event stream between client-side tool calls
>   (requiring `submit_tool_outputs`) and server-side tool calls (fully resolved
>   within the Foundry service)

### Option 2: WorkflowBuilder (Agent Framework SDK)

The `agent-framework` SDK's `WorkflowBuilder` composes agents as nodes in a directed
graph with typed edges and streaming support.

```python
from agent_framework import Executor, WorkflowBuilder, WorkflowContext, handler

class ResearchExecutor(Executor):
    @handler
    async def handle(self, question: str, ctx: WorkflowContext[dict]) -> None:
        response = await self.foundry_agent.run(...)
        await ctx.send_message({"research": response.text})

class StateUpdater(Executor):
    @handler
    async def handle(self, data: dict, ctx: WorkflowContext[Never, str]) -> None:
        response = await self.local_agent.run(...)
        await ctx.yield_output(response.text)

workflow = (
    WorkflowBuilder()
    .set_start_executor(research)
    .add_edge(research, updater)
    .build()
)
```

**Pros:**
- Streaming support via `run_stream`
- Typed edges enforce data contracts between agents
- Supports bidirectional loops and fan-out/fan-in
- Can mix local and Foundry agents

**Cons:**
- Fixed graph — the LLM doesn't dynamically choose which agent to call
- Requires restructuring the AG-UI integration (`AgentFrameworkAgent` wraps a single
  `Agent`, not a `Workflow`)
- More complex setup for what is currently a simple delegation pattern

### Option 3: Improved Function Tool (pragmatic enhancement)

Keep the current pattern — the Foundry agent wrapped as a `@tool`-decorated function
— but fix its limitations: add a context parameter, improve error handling, and
potentially support streaming.

```python
async def ask_agent(question: str, context: str = "") -> str:
    """Ask the Foundry agent a question.

    Args:
        question: The question to research
        context: Optional current project state for additional context
    """
    prompt = question
    if context:
        prompt = f"Context: {context}\n\nQuestion: {question}"

    response = await agent.run(messages=prompt, stream=False)
    if response.text is None:
        return "Error: The research agent did not return a response."
    return response.text
```

**Pros:**
- Minimal change to current architecture
- Local agent still dynamically decides when to delegate
- Preserves AG-UI integration and `predict_state_config`
- Easy to understand and debug

**Cons:**
- Still one-way communication
- Still text-based (no structured response)
- No shared conversation thread

## Decision

**Adopt a phased approach:**

1. **Now — Option 3 (Improved Function Tool).** Enhance the current `ask_agent` tool
   with context passing and better error handling. This preserves the architecture
   and AG-UI state integration while addressing the most pressing limitations.

2. **Future — Option 1 (ConnectedAgentTool).** When/if the local agent moves to
   being Foundry-hosted, migrate to `ConnectedAgentTool` for native server-side
   agent-to-agent delegation.

3. **If needed — Option 2 (WorkflowBuilder).** For complex multi-agent scenarios
   (e.g., research → validate → update → notify), adopt the WorkflowBuilder for
   expressive orchestration. This would require solving the AG-UI integration gap.

## Consequences

- The function-tool pattern remains the primary communication mechanism in the
  short term, keeping the codebase simple.
- Adding the `context` parameter enables the Foundry agent to give more relevant
  answers by seeing current project state.
- Better error handling prevents silent failures when the Foundry agent is
  unavailable.
- The ADR documents a clear upgrade path so we don't re-evaluate from scratch
  when the time comes.

## Comparison Matrix

| Criteria                      | ConnectedAgentTool | WorkflowBuilder | Improved Tool |
|-------------------------------|--------------------|-----------------| --------------|
| Effort to implement           | High               | Medium          | Low           |
| Dynamic routing (LLM decides) | Yes                | No (fixed graph)| Yes           |
| Streaming support             | Depends on Foundry | Yes             | Possible      |
| AG-UI state integration       | Needs rework       | Needs rework    | Works today   |
| Client-side function tools    | Work (tested) ¹    | Yes             | Yes           |
| Server-side MCP tool compat.  | **Broken** ¹       | N/A             | N/A           |
| Structured data passing       | Server-side        | Yes (typed)     | Partial       |
| Bidirectional communication   | Server-side        | Yes             | No            |
| Requires architecture change  | Yes (both hosted)  | Yes (workflow)  | No            |

¹ See "Update (2026-03-11)" in Option 1 above.
