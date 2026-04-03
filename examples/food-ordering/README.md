# Food Ordering Reference Example

End-to-end reference application for **AICP v0.2.0 Phase 2** primitives.

Demonstrates in a single, runnable codebase:

| Primitive | Where used |
|-----------|-----------|
| `CapabilityProvider` | `src/food_ordering/provider.py` |
| YAML Workflow DSL | `aicp/workflows/food_order.yaml` |
| `EventWaiter` (event-driven flows) | `src/food_ordering/event_flow.py` |
| LangChain adapter | `src/food_ordering/langchain_agent.py` |
| LangGraph adapter | `src/food_ordering/langgraph_flow.py` |

---

## Structure

```
examples/food-ordering/
├── aicp/
│   └── workflows/
│       └── food_order.yaml         # YAML DSL workflow definition
├── src/
│   └── food_ordering/
│       ├── capabilities.py         # Capability definitions + FoodOrderSimulator
│       ├── provider.py             # FoodOrderProvider (CapabilityProvider impl)
│       ├── event_flow.py           # EventWaiter order-confirmation flow
│       ├── langchain_agent.py      # LangChain tool builder
│       ├── langgraph_flow.py       # LangGraph node builder
│       └── demo.py                 # Original step-by-step demo
└── tests/
    └── test_food_ordering.py       # 32 TDD tests (all green)
```

---

## Capabilities

| Name | Kind | Description |
|------|------|-------------|
| `food.list_menu` | query | Return all menu items |
| `food.add_to_cart` | action | Add item + quantity to cart |
| `food.view_cart` | query | Inspect cart (subtotal, tax, total) |
| `food.checkout` | action | Place order (policy-gated for >$20) |
| `food.clear_cart` | action | Empty the cart |

---

## Quick start

```python
# Install
pip install -e "packages/core[dev]" -e packages/runtime \
    -e adapters/agent/langchain \
    -e adapters/agent/langgraph \
    -e examples/food-ordering

# Run the original demo
python -m food_ordering.demo
```

---

## FoodOrderProvider

A `CapabilityProvider` with fully isolated per-instance cart state:

```python
from food_ordering.provider import FoodOrderProvider

provider = FoodOrderProvider()

# Discover capabilities
caps = await provider.discover()

# Execute a capability
menu = await provider.execute("food.list_menu", {})
await provider.execute("food.add_to_cart", {"item_id": "burger", "quantity": 2})
order = await provider.execute(
    "food.checkout",
    {"delivery_address": "1 Main St", "payment_method": "card"},
)
```

---

## YAML DSL Workflow

`aicp/workflows/food_order.yaml` defines the four-step ordering flow:

```yaml
name: food_order
steps:
  - id: list_menu
    type: capability
    capability_name: food.list_menu
  - id: add_to_cart
    type: capability
    capability_name: food.add_to_cart
    arguments:
      item_id: burger
      quantity: 1
  - id: view_cart
    type: capability
    capability_name: food.view_cart
  - id: checkout
    type: capability
    capability_name: food.checkout
    arguments:
      delivery_address: "123 Main St"
      payment_method: card
```

Parse it with `WorkflowDSLParser`:

```python
from aicp_runtime.workflow.dsl import WorkflowDSLParser

parser = WorkflowDSLParser()
workflow = parser.parse_file("aicp/workflows/food_order.yaml")
print([s.id for s in workflow.steps])  # ['list_menu', 'add_to_cart', 'view_cart', 'checkout']
```

---

## Event-Driven Flow (EventWaiter)

`event_flow.py` demonstrates waiting for an external `order.confirmed` event after checkout:

```python
from food_ordering.event_flow import run_event_flow

result = await run_event_flow()
print(result)
# {'event_name': 'order.confirmed', 'payload': {'order_id': 'abc12345', 'status': 'confirmed'}}
```

---

## LangChain Integration

```python
from food_ordering.provider import FoodOrderProvider
from food_ordering.langchain_agent import build_langchain_tools

provider = FoodOrderProvider()
tools = await build_langchain_tools(provider)

# tools is a list of 5 AicpCapabilityTool instances (BaseTool subclasses)
# Pass to any LangChain agent:
# agent = initialize_agent(tools, llm, agent=AgentType.OPENAI_FUNCTIONS)
```

---

## LangGraph Integration

```python
from food_ordering.provider import FoodOrderProvider
from food_ordering.langgraph_flow import build_langgraph_nodes, build_tool_node

provider = FoodOrderProvider()

# One node function per capability
nodes = await build_langgraph_nodes(provider)

# Single dispatch node (reads state["capability_name"])
tool_node = await build_tool_node(provider)

# Use in a StateGraph:
# for name, fn in nodes.items():
#     graph.add_node(name, fn)
# graph.add_node("tool", tool_node)
```

---

## Running tests

```bash
# From repo root
python -m pytest examples/food-ordering/tests/ --tb=short -q
```

Expected output: **32 passed**.
