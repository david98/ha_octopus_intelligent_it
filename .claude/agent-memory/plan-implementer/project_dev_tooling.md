---
name: project-dev-tooling
description: Dev tooling setup for ha-octopus-intelligent-it — lefthook + Ruff + convco; pyproject.toml needs setuptools package discovery config to avoid requests/ directory conflict
metadata:
  type: project
---

The ha-octopus-intelligent-it project uses lefthook + Ruff (lint + format) + convco for pre-commit gating.

Key files:
- `pyproject.toml` — Ruff config (py312, select = E/W/F/I/B/UP/SIM/C4/PIE/RUF/ASYNC/PTH, ignore E501)
- `lefthook.yml` — pre-commit: ruff format + ruff check --fix on staged files (stage_fixed: true); pre-push: make lint + make format; commit-msg: convco
- `Makefile` — targets: setup, lint, format, format-fix, check, install-hooks
- `CONTRIBUTING.md` — full developer guide for macOS, Ubuntu/Debian, Fedora, Arch; covers manual install per OS for lefthook/convco/gitleaks

Makefile `setup` target is cross-platform: detects OS via `uname -s` + `/etc/os-release`, installs system tools (lefthook, convco, gitleaks) via brew/apt/dnf/pacman, warns instead of failing when a tool is unavailable. Helper shell functions defined inline in a single recipe block (using `_detect_mgr`, `_use_sudo`, `_install_tool` function definitions) — avoids Make `define` macro with `$(shell ...)` which flattens newlines and breaks shell syntax.

**Why:** `requests/` directory in project root conflicts with setuptools auto-discovery when using `pip install -e ".[dev]"`. Must include `[tool.setuptools.packages.find] where = ["custom_components"]` in pyproject.toml or install fails with "Multiple top-level packages discovered".

**How to apply:** Always add the `[tool.setuptools.packages.find]` block when creating pyproject.toml for this project. Run `.venv/bin/pip install -e ".[dev]"` after creating pyproject.toml, then `.venv/bin/ruff format` + `.venv/bin/ruff check --fix` for the baseline pass before committing.

Cross-platform Makefile lesson: Do NOT use `define`/`endef` macros with `$(shell ...)` for multi-line detection logic — the shell content gets flattened into one line and breaks. Embed all multi-line shell logic directly in the recipe, using shell function definitions (e.g. `_myfn() { ... }`) within a single `\`-continued block.
