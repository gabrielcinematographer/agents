# Connect the cloud teams

The shared desk has two interfaces: GitHub files and small MCP read/write tools. They use Git, not model inference. This does not make consumer chat accounts share their histories automatically.

## Cloud worker setup

Clone this repository in the worker's cloud workspace. It needs Python 3.12+, Git and read/write access to this repository. Use the worker's existing GitHub connection. Do not copy Codex proxy credentials to another service.

For MCP-capable clients, install the pinned server dependency in an isolated environment:

```
python -m venv .venv-team
.venv-team/bin/pip install -r requirements-team.lock
```

Start `.venv-team/bin/python -m team_sync.server` with this repository as the working directory. A client configuration template is in `config/team-mcp.json`; replace its example paths with the worker's actual cloud paths. The server uses stdio; it is not a publicly hosted URL. Do not add it as a remote web connector.

## Claude

Claude Code can register a stdio MCP server. Run this in its cloud worker, with paths adjusted:

```
claude mcp add --transport stdio team-desk -- /workspace/agents/.venv-team/bin/python -m team_sync.server
```

Launch Claude Code from the agents checkout so Python finds the package, or set PYTHONPATH to that checkout. Then ask the worker to call `team_projects` and `team_read`, publish a confirmed handoff, and check that another worker sees it. A Claude web GitHub connector alone should not be assumed to support publishing.

## Grok and Jev

Their consumer websites have not been shown to accept this stdio MCP server. Do not invent a connector. Their cloud workers can use the plain Python interface instead:

```
python -m team_sync read trading
python -m team_sync post trading --provider grok --completed "Reviewed a change" --evidence "commit or output link" --next-step "Next task"
```

Use `--provider jev` for the Jev worker. The existing Jev model API is separate: API inference alone does not provide GitHub tools, shared memory or a running worker. No paid API call is needed to sync an already produced result.

## When to share

Read before starting work. Publish after new confirmed results, decisions or blockers. Each provider's worker must call the tool or command at those points. Provider labels are author-supplied; GitHub credentials enforce access. Only connect trusted workers: this server can write to the shared repository.

## Connection status

- Codex cloud: existing Git access works; shared tools tested here.
- Claude Code: template prepared; client registration and its GitHub access remain unverified.
- Grok: command interface prepared; cloud worker/access remain unverified.
- Jev: command interface prepared; cloud worker/access remain unverified.
- Continuous event delivery: no always-on deployment or incoming webhook configured.

Never store credentials, personal application documents or private chat histories in the public shared desk. Account owners must authorize their service's GitHub access in that service's own settings. A subscription does not grant API access, and API keys are not needed just to read/write shared Git updates.
