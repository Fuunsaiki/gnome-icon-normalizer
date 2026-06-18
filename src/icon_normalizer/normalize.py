#!/usr/bin/env python3
"""Normalize icon padding for all visible app-grid and Dock apps."""

import json
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image
import cairosvg

HOME = Path.home()
WORK_DIR = HOME / '.local/share/icon-normalizer'
APPS_JSON = WORK_DIR / 'apps.json'
OUT_ICON_DIR = HOME / '.local/share/icons/hicolor/512x512/apps'
OUT_DESKTOP_DIR = HOME / '.local/share/applications'
TARGET_CONTENT_RATIO = 0.95  # content occupies 95% of canvas
CANVAS_SIZE = 512

ICON_SEARCH_PATHS = [
    HOME / '.local/share/icons',
    Path('/usr/local/share/icons'),
    Path('/usr/share/icons'),
    Path('/opt'),
]


def get_current_icon_theme():
    try:
        out = subprocess.check_output(
            ['gsettings', 'get', 'org.gnome.desktop.interface', 'icon-theme'],
            text=True,
        ).strip()
        return out.strip("'")
    except Exception:
        return 'Yaru'


def _parse_size_from_path(path):
    """Parse pixel size from icon theme directory path like '.../256x256@2x/categories/...'."""
    import re
    for part in path.parts:
        m = re.search(r'(\d+)x\1(?:@(\d+)x)?', part)
        if m:
            size = int(m.group(1))
            scale = int(m.group(2)) if m.group(2) else 1
            return size * scale
        if part == 'scalable':
            return 1024
    return 0


def find_icon_file(icon_value):
    """Resolve an Icon= value to the largest available non-symbolic image file."""
    if not icon_value:
        return None

    # Absolute path
    if icon_value.startswith('/'):
        p = Path(icon_value)
        if p.exists():
            return str(p)
        for ext in ['.png', '.svg', '.xpm']:
            if p.with_suffix(ext).exists():
                return str(p.with_suffix(ext))
        return None

    current_theme = get_current_icon_theme()
    themes_order = []
    if current_theme:
        themes_order.append(current_theme)
    themes_order.extend(['hicolor', 'Adwaita', 'Yaru', 'ubuntu-mono-dark'])

    # Collect all matching candidates across all themes and contexts
    candidates = []
    searched_themes = []
    for theme in themes_order:
        if theme in searched_themes:
            continue
        searched_themes.append(theme)
        for base in ICON_SEARCH_PATHS:
            theme_dir = base / theme
            if not theme_dir.exists():
                continue
            for ext in ['.svg', '.png', '.xpm']:
                for candidate in theme_dir.rglob(f'{icon_value}{ext}'):
                    if not candidate.is_file():
                        continue
                    size = _parse_size_from_path(candidate.relative_to(theme_dir))
                    is_symbolic = '-symbolic' in candidate.name
                    # Prefer current theme; encode preference by a large bonus
                    theme_bonus = 10_000_000 if theme == current_theme else 0
                    # Prefer non-symbolic by a big bonus
                    symbolic_penalty = 100_000_000 if is_symbolic else 0
                    # Prefer SVG slightly when sizes are equal
                    fmt_bonus = 1 if ext == '.svg' else 0
                    score = theme_bonus + size * 1000 + fmt_bonus - symbolic_penalty
                    candidates.append((score, str(candidate)))

    if candidates:
        candidates.sort(reverse=True, key=lambda x: x[0])
        return candidates[0][1]

    return None


def render_svg_to_png(svg_path):
    """Render SVG to a PIL RGBA image at CANVAS_SIZE."""
    png_bytes = cairosvg.svg2png(
        url=str(svg_path),
        output_width=CANVAS_SIZE,
        output_height=CANVAS_SIZE,
    )
    from io import BytesIO
    return Image.open(BytesIO(png_bytes)).convert('RGBA')


def load_icon(icon_path):
    """Load any supported icon to a square RGBA PIL image."""
    p = Path(icon_path)
    if p.suffix.lower() == '.svg':
        return render_svg_to_png(p)

    img = Image.open(p).convert('RGBA')
    w, h = img.size
    if w != h:
        size = max(w, h)
        canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        canvas.paste(img, ((size - w) // 2, (size - h) // 2), img)
        img = canvas
    return img


def compute_content_bbox(img, alpha_threshold=10):
    """Return bounding box (left, top, right, bottom) of non-transparent content."""
    alpha = img.split()[-1]
    bbox = alpha.getbbox()
    if bbox is None:
        return (0, 0, img.width, img.height)
    return bbox


def normalize_icon(src_path, dst_path):
    """Create a normalized icon with consistent content ratio."""
    img = load_icon(src_path)
    if img.size != (CANVAS_SIZE, CANVAS_SIZE):
        img = img.resize((CANVAS_SIZE, CANVAS_SIZE), Image.LANCZOS)

    bbox = compute_content_bbox(img)
    content_w = bbox[2] - bbox[0]
    content_h = bbox[3] - bbox[1]

    if content_w == 0 or content_h == 0:
        img.save(dst_path)
        return {'src': src_path, 'dst': dst_path, 'bbox': bbox, 'scale': 1.0}

    content = img.crop(bbox)
    target_content_size = int(CANVAS_SIZE * TARGET_CONTENT_RATIO)
    scale = target_content_size / max(content_w, content_h)
    new_w = max(1, int(content_w * scale))
    new_h = max(1, int(content_h * scale))
    scaled = content.resize((new_w, new_h), Image.LANCZOS)

    canvas = Image.new('RGBA', (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0, 0))
    x = (CANVAS_SIZE - new_w) // 2
    y = (CANVAS_SIZE - new_h) // 2
    canvas.paste(scaled, (x, y), scaled)

    Path(dst_path).parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dst_path)

    return {
        'src': str(src_path),
        'dst': str(dst_path),
        'bbox': bbox,
        'scale': scale,
        'new_size': (new_w, new_h),
    }


def build_desktop_override(src_path, dst_path, new_icon_name):
    """Copy .desktop and only change Icon= field."""
    with open(src_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    out_lines = []
    in_entry = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('['):
            in_entry = (stripped == '[Desktop Entry]')
            out_lines.append(line)
            continue
        if in_entry and stripped.startswith('Icon='):
            out_lines.append(f'Icon={new_icon_name}\n')
        else:
            out_lines.append(line)

    dst_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dst_path, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)


def derive_icon_name(icon_value):
    """Derive a unique icon name that won't collide with system theme icons."""
    if icon_value.startswith('/'):
        base = Path(icon_value).stem
    else:
        base = icon_value
    # Avoid double suffixing when re-running against our own .desktop overrides.
    if base.endswith('-normalized'):
        return base
    return base + '-normalized'


def main():
    with open(APPS_JSON, 'r', encoding='utf-8') as f:
        apps = json.load(f)

    OUT_ICON_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DESKTOP_DIR.mkdir(parents=True, exist_ok=True)

    # Auto-select: Dock favorites + all visible app-grid apps
    targets = {
        name: info for name, info in apps.items()
        if info.get('favorite') or info.get('visible')
    }

    results = []
    errors = []

    for desktop_name in sorted(targets):
        info = targets[desktop_name]
        src_path = info['path']
        icon_value = info['icon']
        app_name = info['name']

        if not src_path:
            errors.append(f'{desktop_name}: no .desktop path')
            continue

        print(f'\nProcessing {desktop_name} ({app_name})')
        print(f'  Icon={icon_value}')

        icon_file = find_icon_file(icon_value)
        if not icon_file:
            errors.append(f'{desktop_name}: cannot resolve icon {icon_value}')
            continue
        print(f'  Resolved icon: {icon_file}')

        out_icon_name = derive_icon_name(icon_value)
        dst_icon = OUT_ICON_DIR / f'{out_icon_name}.png'

        try:
            norm_info = normalize_icon(icon_file, dst_icon)
            print(f'  Normalized -> {dst_icon}')
        except Exception as e:
            errors.append(f'{desktop_name}: normalization failed: {e}')
            continue

        # Always create a user .desktop override with the unique icon name.
        # This ensures GNOME uses our icon instead of falling back to the
        # current system theme (e.g. Yaru) which has priority over hicolor.
        src_desktop = Path(src_path)
        dst_desktop = OUT_DESKTOP_DIR / desktop_name
        build_desktop_override(src_desktop, dst_desktop, out_icon_name)
        print(f'  Created .desktop override: {dst_desktop}')

        results.append({
            'desktop': desktop_name,
            'app_name': app_name,
            'icon_value': icon_value,
            'icon_file': icon_file,
            'out_icon': str(dst_icon),
            'desktop_override': True,
            'norm_info': norm_info,
        })

    summary_path = WORK_DIR / 'results.json'
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump({'results': results, 'errors': errors}, f, ensure_ascii=False, indent=2)

    print(f'\n=== Summary ===')
    print(f'Success: {len(results)}')
    print(f'Errors: {len(errors)}')
    if errors:
        for e in errors:
            print(f'  - {e}')
    print(f'Results written to {summary_path}')


if __name__ == '__main__':
    main()
