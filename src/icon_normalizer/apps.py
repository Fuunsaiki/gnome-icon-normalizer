"""Collect Dock favorites and visible app-grid applications."""

import subprocess
from pathlib import Path

HOME = Path.home()
WORK_DIR = HOME / '.local/share/icon-normalizer'
APPS_JSON = WORK_DIR / 'apps.json'

SEARCH_PATHS = [
    Path('/usr/share/applications'),
    Path('/usr/local/share/applications'),
    HOME / '.local/share/applications',
    Path('/opt'),
]


def get_dock_favorites():
    try:
        out = subprocess.check_output(
            ['gsettings', 'get', 'org.gnome.shell', 'favorite-apps'],
            text=True,
        )
        return eval(out.strip())
    except Exception as e:
        print(f'Error getting favorites: {e}')
        return []


def parse_desktop(path):
    data = {}
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        in_entry = False
        for line in f:
            line = line.strip()
            if line.startswith('['):
                in_entry = (line == '[Desktop Entry]')
                continue
            if not in_entry or not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                data[k] = v
    return data


def is_visible(data):
    if data.get('NoDisplay', '').lower() == 'true':
        return False
    if data.get('Type', '') != 'Application':
        return False
    only_show = data.get('OnlyShowIn', '')
    if only_show and 'GNOME' not in only_show.split(';'):
        return False
    return True


def collect_apps():
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    favs = get_dock_favorites()

    desktop_files = {}
    # Search system paths first so later user-local overrides (including our
    # own generated ones) do not overwrite the original .desktop metadata.
    for sp in SEARCH_PATHS:
        if not sp.exists():
            continue
        for f in sp.rglob('*.desktop'):
            if f.name not in desktop_files:
                desktop_files[f.name] = str(f)

    apps = {}
    for name, path in desktop_files.items():
        try:
            data = parse_desktop(path)
            if data.get('Type') == 'Application':
                apps[name] = {
                    'path': path,
                    'name': data.get('Name', name),
                    'icon': data.get('Icon', ''),
                    'nodisplay': data.get('NoDisplay', 'false'),
                    'onlyshowin': data.get('OnlyShowIn', ''),
                    'visible': is_visible(data),
                    'favorite': name in favs,
                }
        except Exception as e:
            print(f'Error parsing {path}: {e}')

    for f in favs:
        if f not in apps:
            apps[f] = {
                'path': None,
                'favorite': True,
                'visible': False,
                'icon': '',
                'name': f,
            }

    import json
    with open(APPS_JSON, 'w', encoding='utf-8') as f:
        json.dump(apps, f, ensure_ascii=False, indent=2)

    visible = [k for k, v in apps.items() if v['visible']]
    favorites = [k for k, v in apps.items() if v['favorite']]
    print(f'Total apps: {len(apps)}')
    print(f'Visible in app grid: {len(visible)}')
    print(f'Dock favorites: {len(favorites)}')
    print(f'Favorites: {favorites}')
    return apps


def main():
    collect_apps()


if __name__ == '__main__':
    main()
