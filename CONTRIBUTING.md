# Contributing to ha-octopus-intelligent-it

## Welcome

Thank you for your interest in contributing! This project is a [Home Assistant](https://www.home-assistant.io/) custom integration for Octopus Energy Italia (SmartFlex devices). Please read [README.md](README.md) first for a high-level overview of what the integration does.

---

## Prerequisites

- **Python 3.12+**
- **git**
- One of the supported package managers / distros:
  - macOS with [Homebrew](https://brew.sh)
  - Debian / Ubuntu (apt)
  - Fedora / RHEL (dnf)
  - Arch Linux (pacman / AUR)
  - **WSL2 users**: follow the Linux path that matches your WSL2 distro.

---

## Development environment setup

### Quick start

```bash
make setup   # auto-detects OS, installs system tools, creates .venv, installs git hooks
make check   # full gate: ruff lint + format check
```

`make setup` will:
1. Create `.venv` and install Python dev dependencies.
2. Detect your OS and install `lefthook`, `convco`, and `gitleaks` via the appropriate package manager.
3. Run `lefthook install` to activate pre-commit / pre-push / commit-msg hooks.

If a tool is not packaged for your system, `make setup` prints a `WARNING` and continues — it will never fail because of a missing package manager. Follow the manual steps below in that case.

### Manual setup per OS

#### macOS (Homebrew)

```bash
brew install lefthook convco gitleaks
make setup
```

#### Debian / Ubuntu

`lefthook` is published in the evilmartians apt repository:

```bash
curl -1sLf 'https://dl.cloudsmith.io/public/evilmartians/lefthook/setup.deb.sh' | sudo -E bash
sudo apt-get install -y lefthook

# gitleaks is in the standard repos on recent Ubuntu/Debian versions
sudo apt-get install -y gitleaks || true

# convco is not in apt; install via cargo (Rust toolchain required)
cargo install convco
```

If `cargo` is not available, install Rust first:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

Then run:

```bash
make setup
```

#### Fedora / RHEL / CentOS

`lefthook` and `gitleaks` are available in the default Fedora repos on recent versions. `convco` is not packaged; use `cargo`:

```bash
sudo dnf install -y lefthook gitleaks
cargo install convco   # requires: sudo dnf install -y rust cargo
make setup
```

#### Arch Linux

`lefthook` is in the community/extra repo; `gitleaks` and `convco` are AUR packages. Use your preferred AUR helper (e.g. `yay`):

```bash
sudo pacman -S --needed lefthook
yay -S gitleaks convco   # AUR
make setup
```

If you prefer not to use an AUR helper, install from source:

```bash
# gitleaks: download the release tarball from https://github.com/gitleaks/gitleaks/releases
# convco:   cargo install convco
```

---

## Development workflow

### Branching

Use short, descriptive branch names that reflect the change:

```
feat/add-battery-sensor
fix/token-refresh-retry
docs/update-contributing
```

### Running the integration locally in Home Assistant

```bash
# Symlink the custom component into your HA config directory
ln -s /path/to/ha-octopus-intelligent-it/custom_components/octopus_intelligent_it \
      <HA_CONFIG>/custom_components/octopus_intelligent_it

# Restart HA (or reload the integration from Settings → Integrations)
```

### API reference

The integration communicates with the Italian Kraken GraphQL API at [`https://api.oeit-kraken.energy/v1/graphql/`](https://api.oeit-kraken.energy/v1/graphql/). All queries and mutations are in `custom_components/octopus_intelligent_it/queries.py`.

### Reading HA logs

In HA's developer tools → Logs, filter by `octopus_intelligent_it`. For verbose output, add to `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.octopus_intelligent_it: debug
```

---

## Code style

- **Ruff** handles both linting and formatting; configuration lives in `pyproject.toml`.
- Pre-commit hooks auto-fix staged `.py` files on every `git commit` — no manual step needed.
- To fix everything locally before committing:
  ```bash
  make format-fix
  ```
- Never disable a Ruff warning without first evaluating a real fix. Blanket `# noqa` suppressions will be flagged in review.

---

## Commit messages

Commit messages must follow [Conventional Commits](https://www.conventionalcommits.org/) — enforced by `convco` in the `commit-msg` hook.

Allowed types:

| Type | When to use |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code restructure without behaviour change |
| `perf` | Performance improvement |
| `docs` | Documentation only |
| `chore` | Tooling, dependencies, config |
| `test` | Adding or updating tests |
| `build` | Build system changes |
| `ci` | CI/CD changes |
| `revert` | Revert a previous commit |

Commit type drives semver via [release-please](https://github.com/googleapis/release-please):
- `fix:` → patch bump
- `feat:` → minor bump
- `feat!:` / `BREAKING CHANGE:` footer → major bump

Example:

```
feat(sensor): add battery state-of-charge sensor
```

---

## Pull requests

- Open PRs against `main`.
- All CI jobs must pass: `lint`, `format`, `hacs`, `hassfest`.
- Keep PRs focused on a single concern; split unrelated changes into separate PRs.
- Add a short description of what changed and why.

---

## Release process

Releases are fully automated via [release-please](https://github.com/googleapis/release-please). You do not need to manually bump versions or create tags.

**How it works:**

1. Every merge to `main` triggers a release-please workflow run.
2. release-please opens (or updates) a **Release PR** titled `chore(main): release X.Y.Z`, which bumps `manifest.json` and updates `CHANGELOG.md`.
3. To cut a release: review and merge the Release PR. A second workflow run then creates the git tag, the GitHub Release, and attaches `octopus_intelligent_it.zip` as a release asset (consumed by HACS).

See [README.md](README.md) for the full release flow description.

---

## Troubleshooting

### lefthook hooks not running

Re-run:

```bash
lefthook install
```

Or use `make install-hooks`.

### gitleaks not found at commit time

Install gitleaks for your OS (see [Manual setup per OS](#manual-setup-per-os)) and then re-run `lefthook install`.

### convco not found at commit time

Install convco for your OS. If you need to commit urgently without it, you can bypass the hook with:

```bash
git commit --no-verify   # discouraged — use only as a last resort
```

### Activating `.venv` on different shells

| Shell | Command |
|---|---|
| bash / zsh | `source .venv/bin/activate` |
| fish | `source .venv/bin/activate.fish` |
| PowerShell (WSL) | `.venv\Scripts\Activate.ps1` |

---

## Getting help

Open an issue on [GitHub](https://github.com/david98/ha-octopus-intelligent-it/issues) and include:

- Your Home Assistant version.
- The relevant log lines from HA developer tools (filter by `octopus_intelligent_it`).
- Steps to reproduce the problem.
