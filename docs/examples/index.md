# Examples

> Working reference applications demonstrating AICP capabilities, governance, and workflows.

---

## Platform Demo

- [Platform Demo](PLATFORM_DEMO.md) — End-to-end Runtime + Connect + CLI + Studio walkthrough

---

## Reference Applications

### Food Ordering

**Location:** `/examples/food-ordering/`

A complete food ordering workflow demonstrating:
- Multi-step workflows
- Capability registration
- Policy-based access control
- Approval checkpoints

```bash
pip install -e ./examples/food-ordering
python -m food_ordering.demo
```

---

### Payment Transfer

**Location:** `/examples/payment-transfer/`

Payment transfer example with two paths:
- Original simulator demo
- Runtime-backed platform demo with approvals, audit, and durable state

```bash
# Simulator demo
pip install -e ./examples/payment-transfer
python -m payment_transfer.demo

# Runtime-backed version
PYTHONPATH="packages/core/src:packages/runtime/src:examples/payment-transfer/src" \
  python -m payment_transfer.platform_demo
```

---

### FastAPI Adapter Demo

**Location:** `/examples/fastapi-demo/`

Demonstrates the FastAPI adapter:
- Auto-discovery of routes
- Pydantic model extraction
- Overlay configuration

```bash
cd examples/fastapi-demo
python server.py
```

---

## What These Examples Demonstrate

| Example | Demonstrates |
|---------|--------------|
| Food Ordering | Multi-step workflow, sequential progression, state tracking |
| Payment Transfer | Policy-based approval, risk scoring, audit trail |
| FastAPI Adapter | Connect import path, auto-discovery from existing apps |

---

## Running All Examples

```bash
# Install all examples
pip install -e ./examples/food-ordering
pip install -e ./examples/payment-transfer
pip install -e ./examples/fastapi-demo

# Run demos
make demo-food
make demo-payment
```

---

## See Also

- [PLATFORM_DEMO.md](./PLATFORM_DEMO.md) — Full platform walkthrough
- [USE_CASES.md](../overview/USE_CASES.md] — Use case documentation