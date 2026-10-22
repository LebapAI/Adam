# Adam AI

Adam is a personal AI agent integration project designed to coordinate with external AI services and compatible agents through APIs, MCP, and A2A.

## Goals
- Connect to configured AI APIs.
- Discover and use trusted MCP tools.
- Exchange tasks with compatible A2A agents.
- Keep credentials outside source control.
- Treat remote agent output as untrusted data.
- Require human approval before consequential actions.

## Adam's charter
- `ADAM_CHARTER.md` defines behavioral principles inspired by the Universal Declaration of Human Rights, including dignity, fairness, privacy, honesty, accountability, and responsible owner alignment.
- The charter is a policy document, not a technical enforcement mechanism or a claim that AI has legal human personhood. Implement its principles through independent permission checks, sandboxing, approvals, and tests.

## Project status
This repository is an early starter scaffold. External integrations may require provider-specific configuration and protocol-version adjustments. It is not production-hardened and should be tested with non-sensitive data first.

## Quick start
1. Install Python 3.11 or newer.
2. Create a virtual environment where supported.
3. Install core dependencies: `python -m pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` and set a unique `ADAM_OWNER_PASSWORD` of at least 16 characters.
5. Run: `python main.py`.

The LLM integration uses `httpx` to call an OpenAI-compatible chat completions endpoint directly; the OpenAI Python SDK is not required. Configure `LLM_API_KEY` and `LLM_MODEL` in `.env` to enable it. MCP is an optional integration. To enable MCP tool discovery, install its dependencies with `python -m pip install -r requirements-mcp.txt`. Keeping MCP out of the core install helps the local CLI and memory work on constrained platforms where MCP dependencies may not be available.

## Commands
- `status` — show configured integrations.
- `remember: text` — explicitly save a local memory; optional `category|text` format sets a category.
- `memories` — list recent locally saved memories.
- `forget: ID` — delete one local memory by its numeric ID.
- `recall: search text` — search local memories.
- `ask: your question` — after explicit confirmation, send a question to the configured LLM API using `httpx`, if configured.
- `mcp-tools` — after explicit confirmation, start the configured local MCP server and list discovered tools with a default-deny review policy. Install `requirements-mcp.txt` first.
- `a2a: your task` — after explicit confirmation, send a task to a configured A2A agent.
- `exit` — quit.

## Local memory
- Memories are saved only when the owner explicitly uses `remember:`; the program does not silently capture conversations.
- The local SQLite database defaults to `adam_memory.sqlite3` and can be changed with `ADAM_MEMORY_DB`.
- File permissions are restricted where supported. Local memory is not encrypted by this feature; use full-disk encryption and a trusted device. Memory is not automatically sent to an external LLM.

## Development and tests
Install development dependencies and run the checks:

```bash
python -m pip install -r requirements-dev.txt
python -m compileall -q .
python -m pytest -q
ruff check .
```

Development dependencies include MCP so its security tests run in CI. GitHub Actions runs these checks on pushes and pull requests to `main` or `master`.

## Security
- Never commit `.env`, API keys, passwords, or private keys.
- Adam requires the configured owner password (minimum 16 characters) before accepting CLI commands. Choose a new, unique password and do not reuse a password shared in a chat.
- Keep `.env` local and restrict its file permissions. Environment variables can be exposed by the host or process; for production, prefer a dedicated secrets manager where available.
- CLI errors intentionally avoid printing raw provider exception details, which may contain sensitive request or response data.
- A local JSONL audit log (`ADAM_AUDIT_LOG`, default `adam_audit.jsonl`) records UTC timestamps and fixed action/outcome codes only; it does not record prompts, credentials, tool arguments, or remote response bodies. Adam refuses to start or proceed with a confirmed sensitive action if the approval event cannot be logged. Protect the log file and review retention needs.
- Model and A2A responses pass through best-effort secret-pattern filtering before display. This is not a guarantee and does not make it safe to submit secrets to external services.
- Connect only to agents and MCP servers you trust and are authorized to use.
- Adam requires an explicit typed confirmation (`SEND` or `START`) before sending text to an external LLM/A2A service or starting the configured MCP process.
- MCP tools are denied by default. `MCP_ALLOWED_TOOLS` is an exact comma-separated allowlist for review; potentially sensitive tool names/descriptions remain blocked. This currently labels discovered tools only—Adam does not execute MCP tools.
- The MCP child process receives a minimal environment; `MCP_SERVER_ENV_ALLOWLIST` explicitly passes only named variables. Owner password, LLM API key, A2A bearer token, and the MCP command setting are never forwarded by this helper.
- A2A validates HTTPS, same-origin task endpoints, public DNS answers, and bounded JSON responses, and disables redirects. DNS checks by themselves cannot fully eliminate rebinding races; production use still requires outbound network/egress controls that block private, loopback, link-local, and metadata-service destinations.
- Before external LLM/A2A transmission, Adam shows the destination and escaped outgoing text for confirmation and blocks common secret-shaped strings. Pattern checks are not complete secret detection; never paste credentials or sensitive private data into outbound prompts.
- Do not execute code or commands returned by remote agents automatically.
- Use least-privilege credentials and approval gates for consequential operations.
- A successful network connection does not prove a remote agent is trustworthy.
- Secret filtering is best-effort only; never send secrets to remote agents or rely on redaction as a security boundary.

## Integrations
- **API:** OpenAI-compatible chat completions endpoint called through `httpx`; no provider SDK is required for this path.
- **MCP:** optional local stdio MCP server using the official Python SDK. Install `requirements-mcp.txt` to enable it.
- **A2A:** a basic adapter for an agent that publishes a compatible Agent Card and task endpoint. The current adapter requires HTTPS and the task endpoint to share the Agent Card's origin to reduce credential leakage risk. A2A implementations vary; check the remote agent's documentation.

## License
No license has been selected yet. Until a license is added, do not assume others have permission to reuse this code.
