.PHONY: setup lint format format-fix check install-hooks

setup:
	@echo "==> Setting up Python virtual environment..."
	@if [ ! -d ".venv" ]; then \
		echo "  Creating .venv..."; \
		python3 -m venv .venv; \
	else \
		echo "  .venv already exists, skipping creation."; \
	fi
	@echo "==> Installing Python dev dependencies..."
	@./.venv/bin/pip install -e ".[dev]" --quiet
	@echo "==> Installing system tools (lefthook, convco, gitleaks)..."
	@set -e; \
	_detect_mgr() { \
		os=$$(uname -s); \
		if [ "$$os" = "Darwin" ]; then \
			echo brew; \
		elif [ "$$os" = "Linux" ] && [ -f /etc/os-release ]; then \
			. /etc/os-release; \
			case "$${ID:-} $${ID_LIKE:-}" in \
				*debian*|*ubuntu*) echo apt ;; \
				*fedora*|*rhel*|*centos*) echo dnf ;; \
				*arch*) echo pacman ;; \
				*) echo unknown ;; \
			esac; \
		else \
			echo unknown; \
		fi; \
	}; \
	_use_sudo() { \
		if [ "$$(id -u)" -ne 0 ] && command -v sudo > /dev/null 2>&1; then \
			echo sudo; \
		fi; \
	}; \
	_install_tool() { \
		tool=$$1; pkg_brew=$$2; pkg_apt=$$3; pkg_dnf=$$4; pkg_pac=$$5; \
		if command -v "$$tool" > /dev/null 2>&1; then \
			echo "  [ok] $$tool already installed."; \
			return 0; \
		fi; \
		mgr=$$(_detect_mgr); \
		echo "  [..] $$tool not found — attempting install via $$mgr..."; \
		SUDO=$$(_use_sudo); \
		case "$$mgr" in \
		brew) \
			if [ "$$pkg_brew" = "-" ]; then \
				echo "  [WARN] $$tool is not packaged for Homebrew. Install manually — see CONTRIBUTING.md."; \
			elif command -v brew > /dev/null 2>&1; then \
				echo "    Running: brew install $$pkg_brew"; \
				brew install "$$pkg_brew" || echo "  [WARN] brew install $$pkg_brew failed. Install manually — see CONTRIBUTING.md."; \
			else \
				echo "  [WARN] brew not found. Install Homebrew first — see https://brew.sh"; \
			fi ;; \
		apt) \
			if [ "$$pkg_apt" = "-" ]; then \
				echo "  [WARN] $$tool is not packaged in apt. Install manually — see CONTRIBUTING.md."; \
			else \
				echo "    Running: $${SUDO:+$$SUDO }apt-get install -y $$pkg_apt"; \
				$${SUDO:+$$SUDO }apt-get install -y "$$pkg_apt" 2>/dev/null \
					|| echo "  [WARN] apt-get install $$pkg_apt failed. Install manually — see CONTRIBUTING.md."; \
			fi ;; \
		dnf) \
			if [ "$$pkg_dnf" = "-" ]; then \
				echo "  [WARN] $$tool is not packaged in dnf. Install manually — see CONTRIBUTING.md."; \
			else \
				echo "    Running: $${SUDO:+$$SUDO }dnf install -y $$pkg_dnf"; \
				$${SUDO:+$$SUDO }dnf install -y "$$pkg_dnf" 2>/dev/null \
					|| echo "  [WARN] dnf install $$pkg_dnf failed. Install manually — see CONTRIBUTING.md."; \
			fi ;; \
		pacman) \
			if [ "$$pkg_pac" = "-" ]; then \
				echo "  [WARN] $$tool is not packaged in pacman. Install manually — see CONTRIBUTING.md."; \
			else \
				echo "    Running: $${SUDO:+$$SUDO }pacman -S --needed --noconfirm $$pkg_pac"; \
				$${SUDO:+$$SUDO }pacman -S --needed --noconfirm "$$pkg_pac" 2>/dev/null \
					|| echo "  [WARN] pacman install $$pkg_pac failed. Install manually — see CONTRIBUTING.md."; \
			fi ;; \
		*) \
			echo "  [WARN] Unrecognised OS/package manager. Install $$tool manually — see CONTRIBUTING.md." ;; \
		esac; \
	}; \
	_install_tool lefthook lefthook - - lefthook; \
	_install_tool convco  convco  -  - -; \
	_install_tool gitleaks gitleaks gitleaks gitleaks -
	@echo "==> Installing git hooks via lefthook..."
	@if command -v lefthook > /dev/null 2>&1; then \
		lefthook install; \
		echo "  [ok] Git hooks installed."; \
	else \
		echo "  [WARN] lefthook not found; skipping hook installation. Install lefthook and run 'lefthook install' manually — see CONTRIBUTING.md."; \
	fi
	@echo "==> Setup complete."

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
