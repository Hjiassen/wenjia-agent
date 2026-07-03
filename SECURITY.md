# Security Policy

## Supported Versions

Security fixes are accepted against the `main` branch and the latest tagged
release when releases are available.

## Reporting a Vulnerability

Please do not open a public issue with exploit details, API keys, private birth
data, session databases, or trace files.

Use GitHub private vulnerability reporting if it is available for this
repository:

https://github.com/Hjiassen/wenjia-agent/security/advisories/new

If private reporting is not available, open a minimal public issue asking for a
private contact path and omit sensitive details until a maintainer responds.

## Sensitive Data

`wenjia-agent` can store local session data, profile data, long-term memory, and
JSONL traces. Treat the following as sensitive:

- `.env` and any `OPENAI_API_KEY` value.
- `wenjia_agent_sessions.db` and related SQLite WAL/SHM files.
- `logs/`, especially trace files that include prompts, tool inputs, or model output.
- User-provided birth profile data and relationship context.

## Scope

Reports are most useful when they affect code or documentation in this
repository, including the FastAPI backend, React frontend, deployment scripts,
Docker configuration, local storage behavior, prompt/tool contracts, or data
handling defaults.

## Responsible Use

The project includes deterministic guardrails and high-risk-topic handling, but
it is still an application template and demo. Deployers are responsible for
their own authentication, rate limits, abuse monitoring, data retention policy,
and jurisdiction-specific compliance.
