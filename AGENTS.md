# AGENTS.md — GNOME Icon Normalizer

This file contains instructions for AI coding agents working on this project.

## Project overview

A small Python CLI tool that normalizes icon padding for applications in the
GNOME Dock and app grid. It analyzes each icon's non-transparent content,
scales it to a consistent visual size, and creates user-local `.desktop`
overrides pointing at the generated icons.

## Tech stack

- Python 3.10+
- `uv` for dependency management and virtual environments
- `Pillow` for image processing
- `cairosvg` for SVG rendering
- `hatchling` as the build backend

## Project layout

```
gnome-icon-normalizer/
├── src/icon_normalizer/       # Main package
│   ├── __init__.py
│   ├── __main__.py            # CLI entry point (icon-normalizer)
│   ├── apps.py                # Discover Dock + app-grid applications
│   └── normalize.py           # Icon analysis, scaling, and override generation
├── README.md
├── LICENSE
├── pyproject.toml
└── uv.lock
```

Runtime-generated files (do not commit):

- `~/.local/share/icon-normalizer/apps.json`
- `~/.local/share/icon-normalizer/results.json`
- `~/.local/share/icons/hicolor/512x512/apps/*-normalized.png`
- `~/.local/share/applications/<app>.desktop` (overrides created by the tool)

## Development workflow

```bash
cd ~/.local/share/icon-normalizer

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Run the tool
uv run icon-normalizer

# Refresh GTK icon cache after changes
gtk-update-icon-cache -f ~/.local/share/icons/hicolor
```

## Coding guidelines

- Keep the tool simple and focused. Avoid heavy dependencies.
- Maintain idempotency: re-running the tool must not double-apply `-normalized`
  suffixes or create duplicate `.desktop` overrides.
- Preserve all original `.desktop` fields except `Icon=` when creating overrides.
- Do not introduce new app-menu entries; respect `NoDisplay`, `OnlyShowIn`,
  `Terminal`, and `ConsoleOnly`.
- Prefer type hints and clear docstrings for new functions.
- Update this file and `README.md` when adding new configuration options or
  changing the algorithm.

## Key tunables

In `src/icon_normalizer/normalize.py`:

```python
TARGET_CONTENT_RATIO = 0.90  # baseline side ratio for square-ish icons
MIN_CONTENT_RATIO = 0.75     # lower bound
MAX_CONTENT_RATIO = 1.00     # upper bound
ASPECT_AREA_BOOST = 0.35     # extra area for wide/tall icons
DENSITY_AREA_PENALTY = 0.12  # area penalty for very dense icons
```

When adjusting these, re-run the tool and inspect `results.json` to verify
`target_ratio` values are reasonable.

## Testing

There is no automated test suite yet. Manual verification steps:

1. Run `uv run icon-normalizer`.
2. Run `gtk-update-icon-cache -f ~/.local/share/icons/hicolor`.
3. Log out and log back in (required on Wayland).
4. Check the Dock and app grid for visual consistency.
5. Verify no unexpected icons appeared in the app grid.

## Release / Git

- Do not commit `.venv/`, `__pycache__/`, runtime JSON files, or generated
  icons/desktop overrides.
- Update `uv.lock` with `uv lock` after changing `pyproject.toml`.
- Keep commits atomic and write clear English commit messages.
