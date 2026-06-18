# GNOME Icon Normalizer

A small Python tool that normalizes icon padding for all apps in the GNOME Dock and app grid, so they look visually uniform.

## Problem

Application icons come from different vendors. Some fill the whole canvas (e.g. WeChat's green square), while others leave transparent margins. Even when GNOME places them in identically-sized slots, they appear to be different sizes.

This tool analyzes each icon's non-transparent content bounding box, scales it to a fixed ratio of the canvas (default **95%**), and centers it on a transparent 512×512 canvas. The result: every icon looks the same size.

## Features

- Automatically discovers Dock favorites and visible app-grid apps.
- Picks the largest available non-symbolic icon from the current theme.
- Generates user-local icon overrides with a `-normalized` suffix.
- Creates user-local `.desktop` overrides that only change `Icon=`, preserving `NoDisplay`, `OnlyShowIn`, and other fields.
- No new icons appear in the app grid.

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)
- GNOME / Ubuntu desktop

## Installation

```bash
git clone https://github.com/yourusername/gnome-icon-normalizer.git
cd gnome-icon-normalizer

uv venv
source .venv/bin/activate
uv pip install -e .
```

## Usage

Run the full pipeline (collect apps + normalize icons):

```bash
icon-normalizer
```

Or with `uv` without installing:

```bash
uv run icon-normalizer
```

Then refresh the icon cache and log out / log back in:

```bash
gtk-update-icon-cache -f ~/.local/share/icons/hicolor
```

> On Wayland you must log out and back in; `Alt+F2 r` does not work.

### Adjust icon size

Edit the ratio in `src/icon_normalizer/normalize.py`:

```python
TARGET_CONTENT_RATIO = 0.95  # content occupies 95% of canvas
```

- Higher value → larger, clearer icon content (smaller margins).
- Lower value → smaller content, larger margins.

Then re-run `icon-normalizer`.

## Project layout

```
gnome-icon-normalizer/
├── LICENSE
├── README.md
├── pyproject.toml
├── uv.lock
└── src/
    └── icon_normalizer/
        ├── __init__.py
        ├── __main__.py      # CLI entry point
        ├── apps.py          # Collect Dock + app-grid apps
        └── normalize.py     # Icon analysis and generation
```

Generated files at runtime:

- `~/.local/share/icon-normalizer/apps.json`
- `~/.local/share/icon-normalizer/results.json`
- `~/.local/share/icons/hicolor/512x512/apps/*-normalized.png`
- `~/.local/share/applications/<app>.desktop`

## Why `-normalized`?

GNOME resolves icons by looking at the current theme (e.g. Yaru) before falling back to `hicolor`. If we reused the original icon name, GNOME could still pick the theme's version. Using a unique `-normalized` name and pointing every `.desktop` file at it guarantees our icon is used.

## Rollback

Delete the generated icons and `.desktop` overrides, then log out / back in:

```bash
# Remove all normalized icons
rm -f ~/.local/share/icons/hicolor/512x512/apps/*-normalized.png

# Remove .desktop overrides created by this tool (Icon= ends with -normalized)
python3 - << 'PYEOF'
from pathlib import Path
app_dir = Path.home() / '.local/share/applications'
for f in app_dir.glob('*.desktop'):
    try:
        with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
            in_entry = False
            icon = None
            for line in fp:
                line = line.strip()
                if line.startswith('['):
                    in_entry = (line == '[Desktop Entry]')
                    continue
                if in_entry and line.startswith('Icon='):
                    icon = line.split('=', 1)[1]
                    break
            if icon and icon.endswith('-normalized'):
                f.unlink()
                print(f'removed {f.name}')
    except Exception as e:
        print(f'error reading {f}: {e}')
PYEOF
```

## License

MIT License — see [LICENSE](LICENSE).
