.PHONY: setup lint format format-fix check install-hooks

setup:
	@if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv .venv; \
	fi
	@echo "Installing dev dependencies..."
	@./.venv/bin/pip install -e ".[dev]" --quiet
	@echo "Installing lefthook hooks..."
	@if command -v lefthook > /dev/null 2>&1; then \
		lefthook install; \
	else \
		echo "WARNING: lefthook not found. Install with: brew install lefthook convco"; \
	fi
	@if ! command -v convco > /dev/null 2>&1; then \
		echo "WARNING: convco not found. Install with: brew install lefthook convco"; \
	fi
	@command -v gitleaks >/dev/null 2>&1 || brew install gitleaks
	@echo "Setup complete."

lint:
	./.venv/bin/ruff check custom_components

format:
	./.venv/bin/ruff format --check custom_components

format-fix:
	./.venv/bin/ruff check --fix custom_components
	./.venv/bin/ruff format custom_components

check: lint format

install-hooks:
	lefthook install
