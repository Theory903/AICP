# Examples

This directory contains working examples of AICP in action.

## Available Examples

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

Payment transfer capabilities with:
- Input/output schema validation
- Error handling with fix hints
- Execution result normalization

```bash
pip install -e ./examples/payment-transfer
python -m payment_transfer.demo
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
