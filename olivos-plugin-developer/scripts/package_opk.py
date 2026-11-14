#!/usr/bin/env python3
"""Package an OlivOS plugin directory as an .opk archive.

An OPK is the plugin directory zipped with the plugin files at the archive root
(no wrapping folder) and the extension renamed from .zip to .opk, as produced by
the official template CI (https://github.com/OlivOS-Team/OlivOSPluginTemplate).

The packer validates the manifest before writing anything and re-opens the
archive afterwards, so a broken OPK is never reported as success.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

REQUIRED_FILES = ('app.json', '__init__.py', 'main.py')
MANIFEST_NAME = 'app.json'
UTF8_BOM = b'\xef\xbb\xbf'

EXCLUDED_DIRS = {
    '.git',
    '.hg',
    '.svn',
    '.idea',
    '.vscode',
    '.pytest_cache',
    '.ruff_cache',
    '.mypy_cache',
    '__pycache__',
    'venv',
    '.venv',
    'node_modules',
}
EXCLUDED_SUFFIXES = ('.pyc', '.pyo', '.bak', '.orig', '.rej', '.log', '.opk', '.zip')
EXCLUDED_NAMES = {'.DS_Store', 'Thumbs.db', 'desktop.ini'}


class PackError(Exception):
    """Raised when the plugin cannot be packaged safely."""


def say(message: str) -> None:
    print(message, flush=True)


def warn(message: str) -> None:
    print(f'[warn] {message}', flush=True)


def fail(message: str) -> None:
    print(f'[error] {message}', file=sys.stderr, flush=True)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(plugin_dir: Path) -> dict:
    """Read app.json and enforce the encoding rules OlivOS needs."""
    manifest_path = plugin_dir / MANIFEST_NAME
    if not manifest_path.is_file():
        raise PackError(f'{MANIFEST_NAME} is missing from {plugin_dir}')

    raw = manifest_path.read_bytes()
    if raw.startswith(UTF8_BOM):
        raise PackError(
            f'{MANIFEST_NAME} starts with a UTF-8 BOM (EF BB BF); OlivOS may fail to read the '
            'manifest. Rewrite it as UTF-8 without BOM.'
        )
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise PackError(f'{MANIFEST_NAME} is not valid UTF-8: {exc}') from exc

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PackError(f'{MANIFEST_NAME} is not valid JSON: {exc}') from exc

    if not isinstance(data, dict):
        raise PackError(f'{MANIFEST_NAME} must contain a JSON object')
    return data


def check_manifest(plugin_dir: Path, manifest: dict) -> None:
    """Report namespace problems that make the host reject the plugin."""
    namespace = manifest.get('namespace')
    if not isinstance(namespace, str) or not namespace.strip():
        raise PackError(f'{MANIFEST_NAME} has no usable "namespace" field')
    if namespace != plugin_dir.name:
        warn(
            f'namespace "{namespace}" differs from the directory name "{plugin_dir.name}"; '
            'OlivOS loads plugins by namespace, so the folder and the field should match'
        )


def check_required_files(plugin_dir: Path, allow_missing: bool) -> list[str]:
    missing = [name for name in REQUIRED_FILES if not (plugin_dir / name).is_file()]
    if missing and not allow_missing:
        raise PackError(f'missing required file(s): {", ".join(missing)}')
    if missing:
        warn(f'missing required file(s): {", ".join(missing)} (allowed by --allow-missing)')
    return missing


def iter_plugin_files(plugin_dir: Path) -> list[Path]:
    """Collect packable files in a stable order, dropping caches and leftovers."""
    files: list[Path] = []
    for path in sorted(plugin_dir.rglob('*')):
        relative = path.relative_to(plugin_dir)
        if any(part in EXCLUDED_DIRS for part in relative.parts[:-1]):
            continue
        if relative.name in EXCLUDED_DIRS:
            continue
        if not path.is_file() or path.is_symlink():
            continue
        if relative.name in EXCLUDED_NAMES:
            continue
        if relative.suffix.lower() in EXCLUDED_SUFFIXES:
            continue
        files.append(path)
    return files


def archive_member_name(plugin_dir: Path, source: Path) -> str:
    """Archive names are always relative and forward-slashed, so the root stays flat."""
    return source.relative_to(plugin_dir).as_posix()


def write_archive(plugin_dir: Path, files: list[Path], opk_path: Path) -> None:
    with ZipFile(opk_path, 'w', compression=ZIP_DEFLATED) as archive:
        for source in files:
            member = archive_member_name(plugin_dir, source)
            info = ZipInfo(filename=member, date_time=_zip_timestamp(source))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            info.create_system = 3
            archive.writestr(info, source.read_bytes())


def _zip_timestamp(source: Path) -> tuple[int, int, int, int, int, int]:
    return tuple(time.localtime(source.stat().st_mtime)[:6])  # type: ignore[return-value]


def verify_archive(plugin_dir: Path, opk_path: Path, expect_files: list[str]) -> None:
    """Re-open the archive and prove it is flat and complete."""
    if not opk_path.is_file() or opk_path.stat().st_size == 0:
        raise PackError(f'{opk_path.name} was not written or is empty')

    with ZipFile(opk_path) as archive:
        names = archive.namelist()
        if not names:
            raise PackError(f'{opk_path.name} contains no entries')

        wrapper = f'{plugin_dir.name}/'
        wrapped = [name for name in names if name.startswith(wrapper)]
        if wrapped:
            raise PackError(
                f'{opk_path.name} nests the plugin inside "{wrapper}"; an OPK must keep its '
                'files at the archive root (zip the contents, not the folder)'
            )

        missing = [name for name in expect_files if name not in names]
        if missing:
            raise PackError(f'{opk_path.name} is missing archive entries: {", ".join(missing)}')

        bad = archive.testzip()
        if bad is not None:
            raise PackError(f'{opk_path.name} failed its CRC check at {bad}')

        if names.count(MANIFEST_NAME) != 1:
            raise PackError(f'{opk_path.name} must contain exactly one {MANIFEST_NAME} at the root')


def package(
    plugin_dir: Path,
    out_dir: Path,
    name: str | None = None,
    allow_missing: bool = False,
    force: bool = False,
    sha256: bool = False,
    check_only: bool = False,
) -> Path | None:
    if not plugin_dir.is_dir():
        raise PackError(f'not a directory: {plugin_dir}')

    manifest = None
    if (plugin_dir / MANIFEST_NAME).is_file():
        manifest = load_manifest(plugin_dir)
        check_manifest(plugin_dir, manifest)
    elif not allow_missing:
        raise PackError(f'{MANIFEST_NAME} is missing from {plugin_dir}')

    check_required_files(plugin_dir, allow_missing)
    files = iter_plugin_files(plugin_dir)
    if not files:
        raise PackError(f'no packable files found in {plugin_dir}')

    stem = name or plugin_dir.name
    opk_path = out_dir / f'{stem}.opk'

    expected = [archive_member_name(plugin_dir, plugin_dir / item) for item in REQUIRED_FILES]
    present = {archive_member_name(plugin_dir, item) for item in files}

    if manifest is not None:
        say(
            f'[manifest] name={manifest.get("name", "?")} namespace={manifest.get("namespace", "?")} '
            f'version={manifest.get("version", "?")} message_mode={manifest.get("message_mode", "?")}'
        )

    if check_only:
        for item in expected:
            if item not in present:
                warn(f'missing required entry: {item}')
        say(f'[ok] {plugin_dir.name} looks packable ({len(files)} files)')
        return None

    out_dir.mkdir(parents=True, exist_ok=True)
    if opk_path.exists():
        if not force:
            raise PackError(f'{opk_path} already exists; pass --force to overwrite')

    write_archive(plugin_dir, files, opk_path)
    verify_archive(plugin_dir, opk_path, [item for item in expected if item in present])

    say(f'[ok] wrote {opk_path} ({len(files)} files, {opk_path.stat().st_size} bytes)')
    for item in sorted(present):
        say(f'  {item}')
    if sha256:
        digest = sha256_of(opk_path)
        sidecar = opk_path.with_suffix('.opk.sha256')
        sidecar.write_text(f'{digest}  {opk_path.name}\n', encoding='utf-8')
        say(f'[sha256] {digest}')
    say('[next] drop the .opk into plugin/app/ (no same-named folder there), then restart the host')
    return opk_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Package an OlivOS plugin directory as an .opk archive (official layout).'
    )
    parser.add_argument('plugin_dir', help='Plugin directory containing app.json, __init__.py, main.py')
    parser.add_argument('-o', '--out-dir', default='.', help='Directory for the .opk (default: current directory)')
    parser.add_argument('--name', default=None, help='Archive base name (default: plugin directory name)')
    parser.add_argument('--allow-missing', action='store_true', help='Downgrade missing required files to warnings')
    parser.add_argument('--force', action='store_true', help='Overwrite an existing .opk')
    parser.add_argument('--sha256', action='store_true', help='Also write a .opk.sha256 sidecar')
    parser.add_argument('--check-only', action='store_true', help='Validate the plugin without writing an archive')
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        package(
            plugin_dir=Path(args.plugin_dir).resolve(),
            out_dir=Path(args.out_dir).resolve(),
            name=args.name,
            allow_missing=args.allow_missing,
            force=args.force,
            sha256=args.sha256,
            check_only=args.check_only,
        )
    except PackError as exc:
        fail(str(exc))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
