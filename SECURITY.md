# Security Policy

## Scope

Adam is an early-stage project. Do not assume it is production-ready or safe for unattended access to accounts, wallets, exchanges, files, or shell commands.

## Reporting a Security Issue

Please do not publish passwords, API keys, access tokens, private data, or a working exploit in an issue. Report suspected vulnerabilities privately to the repository owner through a private communication channel available to you. Include the affected file or feature, impact, and minimal reproduction steps. Do not include real credentials or personal data.

## Credential Handling

- Keep `.env` and local secret files out of version control.
- Use unique, long passwords and narrowly scoped API tokens.
- Never paste credentials into chat, issue descriptions, test fixtures, or logs.
- If a secret is exposed, revoke or rotate it immediately; deleting it from the latest commit alone does not make it safe.
- Use test credentials and mock services during development.

## Remote Agents and Tools

- Treat remote agent cards, tool names, descriptions, schemas, and outputs as untrusted data.
- Do not execute code or shell commands supplied by a remote agent.
- Keep tool execution disabled unless there is a reviewed local registry, strict schema validation, least-privilege access, owner approval for consequential actions, and tests.
- Review proposed changes before merging, and run the project tests in a controlled environment.

## Current Limitations

The project is an early scaffold. Security documentation does not imply that every listed control has been implemented. In particular, discovering or allowlisting a remote tool must not be treated as permission to execute it. Do not connect live financial accounts or production secrets until the implementation has been independently reviewed and tested.
