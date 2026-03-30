# Payment Transfer Demo

This example now has two modes:

- `demo.py` - the original simulator-heavy walkthrough
- `platform_demo.py` - the newer runtime-backed walkthrough that uses:
  - runtime workflow services
  - approval service
  - audit service
  - file-backed persistence

## Run the platform-backed demo

From the repository root:

```bash
PYTHONPATH="packages/core/src:packages/runtime/src:examples/payment-transfer/src" python -m payment_transfer.platform_demo
```

This runs a high-value transfer flow that:

1. creates a workflow
2. triggers policy-driven approval
3. records an approval request
4. approves the request
5. resumes the workflow
6. leaves durable audit and workflow state on disk

It is the current flagship example for showing AICP as a governed runtime rather than just a protocol shape.
