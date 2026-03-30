<!--
  Contributing Guide - Professional Style
-->

<div align="center">

# Contributing to AICP

Thank you for your interest in contributing to **AICP**!

</div>

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Making Contributions](#making-contributions)
5. [Pull Request Process](#pull-request-process)
6. [Coding Standards](#coding-standards)
7. [Protocol Changes (RFCs)](#protocol-changes-rfcs)

---

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md) to keep our community approachable and respectable.

---

## Getting Started

### Fork the Repository

```bash
# Fork via GitHub UI, then clone your fork
git clone https://github.com/YOUR_USERNAME/aicp.git
cd aicp
```

### Install Dependencies

```bash
# Install all dependencies
pnpm install

# Or language-specific
pip install -e "packages/core[dev]"
pip install -e "packages/runtime[dev]"
```

---

## Development Setup

### Python

```bash
# Install in development mode
pip install -e "packages/core[dev]"
pip install -e "packages/runtime[dev]"

# Run tests
pytest

# Lint and format
ruff check .
ruff format .

# Type checking
ruff check --select=typecheck .
```

### TypeScript

```bash
# Install dependencies
cd sdks/typescript
npm install

# Build all packages
npm run build

# Lint and typecheck
npm run lint
npm run typecheck

# Run tests
npm test
```

---

## Making Contributions

### Bug Reports

When reporting a bug, please include:

- **Clear title** describing the issue
- **Steps to reproduce** the bug
- **Expected vs actual behavior**
- **Environment details** (OS, Python version, etc.)
- **Minimal reproduction** if possible

### Feature Requests

For new features:

1. Open an issue with the `feature` label
2. Describe the **use case** — why do you need this?
3. Explain how it **fits AICP's design**
4. Provide **example code** if possible

### Documentation Improvements

- Fix typos, clarify explanations
- Add missing code examples
- Translate or localize content
- Improve diagrams

---

## Pull Request Process

### Before You Start

1. **Check existing issues** — Is this already being worked on?
2. **Open a discussion** — For significant changes
3. **Create an RFC** — For protocol changes (see below)

### Creating a PR

```bash
# Create a feature branch
git checkout -b feat/your-feature

# Or bugfix
git checkout -b fix/bug-description

# Make changes and commit
# Use conventional commits
git commit -m "feat: add capability search by tags"

# Push and create PR
git push -u origin feat/your-feature
```

### PR Requirements

- ✅ **Tests pass** — Add tests for new features
- ✅ **Lint clean** — No ruff/typescript errors
- ✅ **Type hints** — Full type coverage
- ✅ **Documentation** — Update docs if needed
- ✅ **Description** — Clear summary of changes

### Commit Messages

We use [Conventional Commits](https://conventionalcommits.org):

```
feat: add capability search by tags
fix: resolve policy evaluation edge case
docs: update quick start guide
refactor: simplify executor error handling
test: add test for OAuth2 auth flow
chore: update dependencies
```

---

## Coding Standards

### Python

- Follow **PEP 8**
- Use **type hints** everywhere
- Use `snake_case` for functions/variables
- Use `PascalCase` for classes
- Prefix private methods with `_`

```python
from typing import Protocol, Optional

class CapabilityProvider(Protocol):
    def get_capability(self, name: str) -> Optional[Capability]: ...
```

### TypeScript

- Follow **Google TypeScript Style Guide**
- Use explicit return types for public functions
- Use `readonly` for immutable data

```typescript
export interface Capability {
  readonly name: string;
  readonly description: string;
  readonly kind: CapabilityKind;
}
```

### Testing

- Aim for >80% coverage on core packages
- Test happy path AND error cases
- Include edge cases

```python
def test_capability_validation_rejects_invalid_input():
    with pytest.raises(ValidationError) as exc_info:
        Capability(name="", kind=CapabilityKind.ACTION)
    assert exc_info.value.code == "missing_required_field"
```

---

## Protocol Changes (RFCs)

For changes to the AICP protocol, we use the **RFC process**:

### When to Submit an RFC

Required for:
- New capability kinds
- Policy contract changes
- Workflow model changes
- Breaking schema changes
- New transport protocols

### RFC Process

1. Create a new RFC in `/rfcs/`
2. Follow the RFC template
3. Submit as a PR for discussion
4. Address feedback
5. Merge when approved

See [/rfcs/README.md](../rfcs/README.md) for details.

---

## License

By contributing to AICP, you agree that your contributions will be licensed under the [Apache 2.0 License](../LICENSE).

---

## Questions?

- 💬 **Discord**: [Join our community](https://discord.gg/aicp)
- 🐛 **Issues**: [Report bugs](https://github.com/aicp-ai/aicp/issues)
- 💡 **Discussions**: [Feature discussions](https://github.com/aicp-ai/aicp/discussions)

---

<p align="center">
  <em>Thank you for contributing to AICP!</em>
</p>
