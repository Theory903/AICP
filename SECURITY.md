# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.3.x   | :white_check_mark: |
| < 0.3   | :x:                |

AICP is pre-1.0 software. Only the latest minor version receives security updates.

## Reporting a Vulnerability

**Do not open a public issue** for security vulnerabilities.

Email: **[security@aicp.ai](mailto:security@aicp.ai)** (or use GitHub's [private vulnerability reporting](https://github.com/Theory903/AICP/security/advisories/new))

Include:
- A description of the vulnerability
- Steps to reproduce (or a minimal proof-of-concept)
- The affected component (runtime, CLI, adapter, spec)
- Your assessment of severity (low/medium/high/critical)

You will receive an acknowledgment within **48 hours**. We aim to triage and respond with a remediation plan within **7 days**.

## Scope

### In Scope
- Policy bypass (capability executed without policy evaluation)
- Approval bypass (approval-gated action executed without human approval)
- Session hijacking or token forgery
- Injection vulnerabilities in the runtime or CLI
- Path traversal in file-based persistence
- SQL injection in SQLite persistence backend
- Denial of service via malformed input

### Out of Scope
- Vulnerabilities in example applications
- Issues in empty adapter directories (no code to exploit)
- Pre-existing LSP/Pydantic type errors (benign false positives)

## Security Architecture

AICP is designed with security as a first-class concern:
- **Policy-gated execution**: Every capability is policy-evaluated before side effects
- **Approval lifecycle**: Approval-gated actions block until human resolution
- **Audit trail**: Every action produces an append-only audit entry
- **Replayability**: Every action is replayable for forensic analysis
- **Trust tiers**: Capability access is determined by trust level (0-4)
- **Fail-closed defaults**: If policy evaluation fails, deny

## Known Limitations (v0.3.0)
- Session storage is plaintext (encryption planned for v0.9.0)
- No rate limiting at the API boundary
- No multi-tenant isolation enforcement
- Semantic retrieval uses keyword co-occidence only (no embeddings)
