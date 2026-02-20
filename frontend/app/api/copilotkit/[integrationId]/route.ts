export const runtime = "nodejs";

const AG_UI_ENDPOINT = process.env.AG_UI_ENDPOINT ?? "http://localhost:8000/ag-ui";
const AGENT_NAME = process.env.AZURE_AI_PROJECT_AGENT_NAME ?? "ag-ui";
const SUPPORTED_AGENT_ALIASES = ["ag-ui", "librarian", "gap-analyst"] as const;

function normalizeAgentId(agentId: string | undefined): string {
  if (!agentId) {
    return AGENT_NAME;
  }

  const trimmed = agentId.trim();

  if (!trimmed) {
    return AGENT_NAME;
  }

  if (SUPPORTED_AGENT_ALIASES.includes(trimmed as (typeof SUPPORTED_AGENT_ALIASES)[number])) {
    return AGENT_NAME;
  }

  return trimmed;
}

const runtimeAgents = Array.from(new Set([AGENT_NAME, ...SUPPORTED_AGENT_ALIASES]));
const RUNTIME_INFO = {
  version: "0.0.0",
  audioFileTranscriptionEnabled: false,
  agents: Object.fromEntries(
    runtimeAgents.map((agentName) => [
      agentName,
      {
        name: agentName,
        className: "AgentFrameworkAgent",
        description: "Project agent",
      },
    ])
  ),
};

async function proxyRequest(request: Request): Promise<Response> {
  const requestUrl = new URL(request.url);
  const targetUrl = new URL(AG_UI_ENDPOINT);
  targetUrl.search = requestUrl.search;

  const headers = new Headers(request.headers);
  headers.delete("host");

  let body: BodyInit | undefined;

  if (request.method !== "GET" && request.method !== "HEAD") {
    const contentType = request.headers.get("content-type") ?? "";

    if (contentType.includes("application/json")) {
      const json = await request.json();
      const method =
        json && typeof json === "object" && "method" in json
          ? (json as { method?: string }).method
          : undefined;

      if (method === "info") {
        return Response.json(RUNTIME_INFO);
      }

      const payload =
        json && typeof json === "object" && "body" in json && "method" in json
          ? (json as { body: unknown; params?: { agentId?: string } }).body
          : json;

      const agentId =
        json && typeof json === "object" && "params" in json
          ? (json as { params?: { agentId?: string } }).params?.agentId
          : undefined;

      const normalizedAgentId = normalizeAgentId(agentId);

      if (!targetUrl.searchParams.has("agentId")) {
        targetUrl.searchParams.set("agentId", normalizedAgentId);
      }

      if (json && typeof json === "object" && "params" in json) {
        const payloadWithAgent = json as { params?: { agentId?: string } };
        payloadWithAgent.params = {
          ...(payloadWithAgent.params ?? {}),
          agentId: normalizedAgentId,
        };
      }

      body = JSON.stringify(payload ?? {});
      headers.set("content-type", "application/json");
      headers.delete("content-length");
    } else {
      body = await request.arrayBuffer();
    }
  }

  const response = await fetch(targetUrl, {
    method: request.method,
    headers,
    body,
  });

  return new Response(response.body, {
    status: response.status,
    headers: response.headers,
  });
}

export async function GET(request: Request): Promise<Response> {
  return proxyRequest(request);
}

export async function POST(request: Request): Promise<Response> {
  return proxyRequest(request);
}
