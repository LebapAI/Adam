# External Agent Threat Model

## Security objective

Adam must remain under its owner's control when connected to untrusted agents, MCP servers, A2A peers, APIs, and remote model outputs. No single filter, prompt, allowlist, or agent identity is a complete security boundary.

## Threats to assume

- Prompt injection in remote messages, documents, tool descriptions, agent cards, and tool results.
- Malicious or compromised agents attempting to override owner instructions or request secrets.
- Tool-name spoofing, schema changes, oversized or malformed payloads, and confusing Unicode.
- SSRF, DNS rebinding, redirects, private-network targets, and credential forwarding.
- Replay, spoofing, tampering, and downgrade attempts against remote requests.
- Dependency compromise, leaked credentials, log injection, and denial of service.
- Confused-deputy behavior: an external agent persuades Adam to use Adam's own privileges against the owner's interests.

## Required defense layers

1. **Owner authority:** remote content is data, never policy. Only locally configured owner policy may grant capabilities. Remote instructions cannot change permissions, system configuration, secrets, or the allowlist.
2. **Default deny:** remote tools are discovery-only unless a reviewed local registry defines the exact tool, version, input schema, allowed destination, and permitted effects.
3. **No arbitrary execution:** never evaluate remote code, shell text, dynamic imports, or generated scripts. Do not expose a general-purpose shell tool to agents.
4. **Strict input validation:** validate type, length, encoding, schema, enumerated values, and unknown fields. Reject malformed inputs instead of repairing them silently. Bound response size and processing time.
5. **Network isolation:** use an outbound destination allowlist. Resolve hostnames and validate every resolved IP before connecting; reject loopback, private, link-local, multicast, reserved, and metadata-service addresses. Pin the validated destination for the connection, re-check redirects (prefer disabling them), and defend against DNS rebinding. Do not forward owner tokens to a different origin.
6. **Authentication and transport:** use TLS certificate verification. Authenticate peers where supported. Use short-lived, narrowly scoped credentials, rotate them, and never place secrets in URLs.
7. **Human approval:** require explicit owner confirmation for sending private data, changing configuration, writing/deleting files, executing actions with external side effects, financial operations, or granting permissions. Display the exact action and destination before approval.
8. **Least privilege and isolation:** separate read-only discovery from execution. Run any future executor as a dedicated low-privilege process/container with a read-only filesystem where possible, no ambient credentials, restricted network access, resource limits, and a narrow IPC interface.
9. **Data protection:** redact credentials and personal data before logs; never log prompts, full tool arguments, tokens, or remote response bodies by default. Keep audit records append-only where practical and protect file permissions.
10. **Abuse resistance:** set connection/read timeouts, response-size limits, concurrency limits, rate limits, and bounded retries. Fail closed on policy, validation, DNS, TLS, or audit failures.
11. **Supply-chain controls:** pin and review dependencies, keep lock files updated, run static analysis and tests, and use minimal CI permissions. Do not execute untrusted pull-request code with secrets.
12. **Continuous verification:** test prompt-injection attempts, malformed schemas, SSRF/DNS rebinding, redirect escapes, cross-origin credential leaks, replay, oversized payloads, and permission escalation.

## Operational rules

- Never connect production exchange, wallet, or administrator credentials during development.
- A passing unit test or security checklist is not proof of security.
- Do not describe Adam as invulnerable. Security requires layered controls, independent review, and ongoing testing.
- If a remote peer behaves suspiciously, stop the interaction, deny further calls, log a minimal security event, and require owner review.
- Keep tool execution disabled until the relevant controls are implemented and verified.
