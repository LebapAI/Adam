# Adam AI

Adam is a personal AI agent integration project designed to coordinate with external AI services and compatible agents through APIs, MCP, and A2A.

## Goals
- Connect to configured AI APIs.
- Discover and use trusted MCP tools.
- Exchange tasks with compatible A2A agents.
- Keep credentials outside source control.
- Treat remote agent output as untrusted data.
- Require human approval before consequential actions.

## Project status
This repository is an early starter scaffold. External integrations may require provider-specific configuration and protocol-version adjustments. It is not production-hardened and should be tested with non-sensitive data first.

## Quick start
1. Install Python 3.11 or newer.
2. Create a virtual environment.
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env`, set a unique `ADAM_OWNER_PASSWORD` of at least 16 characters, and configure only the API settings you plan to use.
5. Run: `python main.py`

## Commands
- `status` — show configured integrations.
- `ask: your question` — send a question to the configured LLM API.
- `mcp-tools` — list tools from the configured local MCP server.
- `a2a: your task` — attempt to send a task to a configured A2A agent.
- `exit` — quit.

## Development and tests
Install development dependencies and run the checks:

```bash
pip install -r requirements-dev.txt
python -m compileall -q .
python -m pytest -q
ruff check .
```

GitHub Actions runs these checks on pushes and pull requests to `main` or `master`.

## Security
- Never commit `.env`, API keys, passwords, or private keys.
- Adam requires the configured owner password (minimum 16 characters) before accepting CLI commands. Choose a new, unique password and do not reuse a password shared in a chat.
- Keep `.env` local and restrict its file permissions. Environment variables can be exposed by the host or process; for production, prefer a dedicated secrets manager where available.
- CLI errors intentionally avoid printing raw provider exception details, which may contain sensitive request or response data.
- Model and A2A responses pass through best-effort secret-pattern filtering before display. This is not a guarantee and does not make it safe to submit secrets to external services.
- Connect only to agents and MCP servers you trust and are authorized to use.
- Do not execute code or commands returned by remote agents automatically.
- Use least-privilege credentials and approval gates for consequential operations.
- A successful network connection does not prove a remote agent is trustworthy.
- Secret filtering is best-effort only; never send secrets to remote agents or rely on redaction as a security boundary.

## Integrations
- **API:** OpenAI-compatible chat completions endpoint.
- **MCP:** local stdio MCP server using the official Python SDK.
- **A2A:** a basic adapter for an agent that publishes a compatible Agent Card and task endpoint. The current adapter requires HTTPS and the task endpoint to share the Agent Card's origin to reduce credential leakage risk. A2A implementations vary; check the remote agent's documentation.

## License
No license has been selected yet. Until a license is added, do not assume others have permission to reuse this code.
