# Security Policy

AICP is a **security-critical control plane** for organizational automation. It governs agent execution, enforces policy, manages approvals, and maintains audit trails.

Because AICP controls what actions can execute and when humans must approve them, security issues here affect:
- Policy enforcement
- Workflow safety
- Approval correctness
- Session integrity
- Auditability
- Org-boundary guarantees

---

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.9.x | ✅ Latest |
| < 0.9 | ❌ End-of-life |

Only the latest minor version receives security updates.

---

## Reporting a Vulnerability

**Do NOT open a public issue for security vulnerabilities.**

Email: [security@aicp.ai](mailto:security@aicp.ai)

Or use GitHub's [private vulnerability reporting](https://github.com/Theory903/AICP/security/advisories/new)

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any known fixes

---

## Security Features

AICP provides these security mechanisms:

| Feature | Purpose |
|---------|---------|
| **SSRF Protection** | Block private IPs, DNS rebinding |
| **DEK Encryption** | Per-credential AES-256-GCM encryption |
| **Policy Engine** | Allow/deny/ask/limit before execution |
| **Approval Lifecycle** | Human-in-the-loop for risky actions |
| **Trust Tiers** | 0 (anonymous) to 4 (fully autonomous) |
| **Audit Trail** | Append-only, replayable, correlation IDs |
| **Plugin Sandbox** | Isolated execution for third-party plugins |
| **Session Isolation** | Resumable, multi-tenant sessions |

---

## Security Guidelines

When developing with AICP:

1. **Never bypass policy evaluation** for side-effecting capabilities
2. **Always log audit entries** for every execution
3. **Use DEK encryption** for any stored credentials
4. **Enable SSRF protection** for HTTP capabilities
5. **Require approvals** for high-risk capabilities
6. **Never suppress type errors** (`as any`, `@ts-ignore`)
7. **Never swallow exceptions** silently

---

## Scope

This policy covers:
- AICP Python packages (`packages/core`, `packages/runtime`)
- Mammoth Rust crates (`apps/mammoth`)
- Adapters (`adapters/*`)
- SDKs (`sdks/*`)

This does NOT cover:
- Third-party integrations (report to those projects)
- Downstream applications using AICP

---

*Last updated: 2026-04-06*
