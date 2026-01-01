# AICP Core

Core library for AI Capability Protocol (AICP).

## Installation

```bash
pip install aicp-core
```

## Usage

```python
from aicp import Capability, CapabilityKind

cap = Capability(
    name="payments.transfer",
    description="Transfer funds between accounts",
    kind=CapabilityKind.ACTION,
)
```

## License

MIT
