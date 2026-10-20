# Tool safety

Adam does not execute tools discovered from remote agents. Treat tool names, descriptions, schemas, and outputs as untrusted input. Before enabling execution, require an explicit local registry, strict argument validation, least-privilege permissions, owner confirmation, and tests. Never allow an agent to run arbitrary shell commands or code.
