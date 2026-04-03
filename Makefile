# AICP Makefile

# Default PYTHONPATH to include packages
PYTHONPATH := $(shell pwd)/packages/core/src:$(PYTHONPATH)

# === Installation ===

.PHONY: install
install:
	@echo "Installing AICP core..."
	@cd packages/core && pip install -e .

.PHONY: install-ci
install-ci:
	@echo "Installing all local AICP packages for CI..."
	@pip install -e ./packages/core \
		-e ./packages/runtime \
		-e ./adapters/framework/fastapi \
		-e ./adapters/protocol/openapi \
		-e ./adapters/protocol/mcp \
		-e ./adapters/importers/postman \
		-e ./adapters/importers/har \
		-e ./adapters/importers/curl \
		-e ./packages/cli

# === Tests ===

.PHONY: test
test:
	@echo "Running full test suite..."
	@python -m pytest packages/ --tb=short -q

.PHONY: test-conformance
test-conformance:
	@echo "Running conformance tests..."
	@python -m pytest spec/tests/ packages/runtime/tests/conformance/ --tb=short -q

.PHONY: test-bench
test-bench:
	@echo "Running benchmark tests..."
	@python -m pytest packages/core/tests/benchmarks/ --tb=short -q

.PHONY: test-unit
test-unit:
	@echo "Running core unit tests..."
	@python -m pytest packages/core/tests/test_*.py --tb=short -q

.PHONY: test-runtime
test-runtime:
	@echo "Running runtime tests..."
	@python -m pytest packages/runtime/tests/ --tb=short -q

.PHONY: test-cli
test-cli:
	@echo "Running CLI tests..."
	@python -m pytest packages/cli/tests/ --tb=short -q

# === Linting ===

.PHONY: lint
lint:
	@echo "Running ruff check..."
	@ruff check .

.PHONY: format
format:
	@echo "Running ruff format..."
	@ruff format .

.PHONY: format-check
format-check:
	@echo "Checking formatting..."
	@ruff format --check .

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
	@echo "  install-ci    - Install all packages for CI"
	@echo ""
	@echo "=== Tests ==="
	@echo "  test           - Run full test suite (all packages)"
	@echo "  test-conformance - Run spec + L3/L4 conformance tests"
	@echo "  test-bench     - Run benchmark tests"
	@echo "  test-unit      - Run core unit tests only"
	@echo "  test-runtime   - Run runtime tests"
	@echo "  test-cli       - Run CLI tests"
	@echo ""
	@echo "=== Linting ==="
	@echo "  lint           - Run ruff check"
	@echo "  format         - Run ruff format (fix)"
	@echo "  format-check   - Run ruff format --check"
	@echo ""
	@echo "=== Examples ==="
	@echo "  demo-food      - Run food ordering demo"
	@echo "  demo-payment   - Run payment transfer demo"
	@echo "  demo-fastapi   - Run FastAPI demo (blocking)"
	@echo "  demos          - Run all demos"
	@echo ""
	@echo "=== CI ==="
	@echo "  smoke          - Run lint + unit + conformance + demos"
	@echo "  ci             - Run lint + full tests + benchmarks"
