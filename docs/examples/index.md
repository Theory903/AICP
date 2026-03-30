# Examples

This directory contains working examples of AICP in action.

## Available Examples

## Platform-Level Walkthrough

- [Platform Demo](PLATFORM_DEMO.md) - the current end-to-end Runtime + Connect + CLI + Studio path

### Food Ordering
Location: `/examples/food-ordering/`

A complete food ordering workflow demonstrating:
- Multi-step workflows
- Capability registration
- Policy-based access control

```bash
pip install -e ./examples/food-ordering
python -m food_ordering.demo
```

### Payment Transfer
Location: `/examples/payment-transfer/`

Payment transfer example with two paths:
- original simulator demo
- newer runtime-backed platform demo with approvals, audit, and durable state

```bash
pip install -e ./examples/payment-transfer
python -m payment_transfer.demo
```

Runtime-backed version:

```bash
PYTHONPATH="packages/core/src:packages/runtime/src:examples/payment-transfer/src" python -m payment_transfer.platform_demo
```

### FastAPI Adapter Demo
Location: `/examples/fastapi-demo/`

Demonstrates the FastAPI adapter:
- Auto-discovery of routes
- Pydantic model extraction
- Overlay configuration

```bash
cd examples/fastapi-demo
python server.py
```
