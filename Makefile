# AICP Makefile

# Default PYTHONPATH to include packages
PYTHONPATH := $(shell pwd)/packages/core/src:$(PYTHONPATH)

# === Installation ===

.PHONY: install
install:
	@echo "Installing AICP core..."
	@cd packages/core && pip install -e .

# === Tests ===

.PHONY: test
test:
	@cd packages/core && python -m pytest tests/ -v

.PHONY: test-conformance
test-conformance:
	@echo "Running conformance tests..."
	@cd packages/core && python -m pytest tests/conformance/ -v

.PHONY: test-bench
test-bench:
	@echo "Running benchmark tests..."
	@cd packages/core && python -m pytest tests/benchmarks/ -v

.PHONY: test-unit
test-unit:
	@cd packages/core && python -m pytest tests/test_*.py -v

# === Linting ===

.PHONY: lint
lint:
	@cd packages/core && ruff check src/aicp/

# === Examples / Demos ===

.PHONY: demo-food
demo-food:
	@echo "Running Food Ordering Demo..."
	@cd examples/food-ordering/src && PYTHONPATH=$(PYTHONPATH) python -m food_ordering.demo

.PHONY: demo-payment
demo-payment:
	@echo "Running Payment Transfer Demo..."
	@cd examples/payment-transfer/src && PYTHONPATH=$(PYTHONPATH) python -m payment_transfer.demo

.PHONY: demo-fastapi
demo-fastapi:
	@echo "Running FastAPI Demo..."
	@cd examples/fastapi-demo && PYTHONPATH=$(PYTHONPATH) python -m uvicorn server:app --host 0.0.0.0 --port 8000

.PHONY: demos
demos: demo-food demo-payment
	@echo ""
	@echo "All demos completed!"

# === Smoke Tests ===

.PHONY: smoke
smoke: lint test-unit test-conformance demo-food demo-payment
	@echo ""
	@echo "All smoke tests passed!"

# === CI ===

.PHONY: ci
ci: lint test test-bench
	@echo ""
	@echo "CI checks passed!"

# === Help ===

.PHONY: help
help:
	@echo "AICP Makefile"
	@echo ""
	@echo "=== Installation ==="
	@echo "  install       - Install AICP core package"
	@echo ""
	@echo "=== Tests ==="
	@echo "  test           - Run all tests"
	@echo "  test-conformance - Run conformance tests only"
	@echo "  test-bench     - Run benchmark tests only"
	@echo "  test-unit      - Run unit tests only"
	@echo ""
	@echo "=== Linting ==="
	@echo "  lint           - Run linter"
	@echo ""
	@echo "=== Examples ==="
	@echo "  demo-food      - Run food ordering demo"
	@echo "  demo-payment   - Run payment transfer demo"
	@echo "  demo-fastapi   - Run FastAPI demo (blocking)"
	@echo "  demos          - Run all demos"
	@echo ""
	@echo "=== CI ==="
	@echo "  smoke          - Run lint + unit + conformance + demos"
	@echo "  ci             - Run lint + tests + benchmarks"
