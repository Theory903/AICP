# Contributing to AICP

Thank you for your interest in contributing to AICP!

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/aicp.git`
3. Install dependencies: `pnpm install` (or see language-specific guides)

## Development Commands

### Python
```bash
pip install -e ".[dev]"
pytest
ruff check .
ruff format .
```

### TypeScript
```bash
npm install
npm test
npm run lint
npm run typecheck
```

## How to Contribute

### Bug Reports
- Use GitHub Issues
- Include reproduction steps
- Specify environment details

### Feature Requests
- Open an issue with `feature` label
- Describe the use case
- Explain how it fits AICP's design

### Spec Changes (RFCs)
For protocol changes, see `/rfcs/README.md`. RFCs required for:
- New capability kinds
- Policy contract changes
- Workflow model changes
- Breaking schema changes

### Pull Requests
1. Create a feature branch: `git checkout -b feat/your-feature`
2. Make changes with tests
3. Run lint/typecheck before committing
4. Commit with conventional commits: `feat: add capability validation`
5. Push and create PR

## Code Style

- Follow PEP 8 for Python
- Follow Google TypeScript Style Guide
- Use type hints everywhere
- Write tests for new features

## License

By contributing, you agree that your contributions will be licensed under Apache-2.0.
