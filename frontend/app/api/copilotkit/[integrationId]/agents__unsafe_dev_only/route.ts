const agentName = process.env.AZURE_AI_PROJECT_AGENT_NAME ?? "ag-ui";
const agentAliases = ["ag-ui", "librarian", "gap-analyst"];
const agents = Array.from(new Set([agentName, ...agentAliases])).map((name) => ({
  id: name,
  name,
  description: "Project agent",
}));

export async function GET(): Promise<Response> {
  return Response.json({ agents });
}

export async function POST(): Promise<Response> {
  return Response.json({ agents });
}
