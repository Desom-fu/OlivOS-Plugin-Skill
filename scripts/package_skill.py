#!/usr/bin/env python3
"""Package a Codex skill directory as a release zip."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


DEFAULT_SKILL_DIR = 'olivos-plugin-developer'
DEFAULT_OUT_DIR = 'dist'
ZIP_NAME = 'olivos-plugin-developer.zip'

EXCLUDED_DIRS = {
    '.git',
    '.pytest_cache',
    '__pycache__',
}
EXCLUDED_FILES = {
    '.DS_Store',
    'Thumbs.db',
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Package olivos-plugin-developer as a zip release asset.')
    parser.add_argument('--skill-dir', default=DEFAULT_SKILL_DIR, help='Skill directory to package.')
    parser.add_argument('--out-dir', default=DEFAULT_OUT_DIR, help='Directory where release assets are written.')
    return parser.parse_args()


def ensure_skill_dir(skill_dir: Path) -> None:
    if not skill_dir.is_dir():
        raise SystemExit(f'Skill directory not found: {skill_dir}')

    skill_file = skill_dir / 'SKILL.md'
    if not skill_file.is_file():
        raise SystemExit(f'SKILL.md not found in skill directory: {skill_file}')

    text = skill_file.read_text(encoding='utf-8-sig')
    if 'name: olivos-plugin-developer' not in text:
        raise SystemExit('SKILL.md frontmatter does not contain name: olivos-plugin-developer')


def should_include(path: Path) -> bool:
    if any(part in EXCLUDED_DIRS for part in path.parts):
        return False
    if path.name in EXCLUDED_FILES:
        return False
    return True


def iter_files(skill_dir: Path) -> list[Path]:
    files: list[Path] = []
    for root, dir_names, file_names in os.walk(skill_dir):
        root_path = Path(root)
        dir_names[:] = [name for name in sorted(dir_names) if should_include(root_path / name)]
        for file_name in sorted(file_names):
            path = root_path / file_name
            if should_include(path):
                files.append(path)
    return files


def add_file(zip_file: ZipFile, source: Path, arcname: Path) -> None:
    info = ZipInfo(str(arcname).replace('\\', '/'))
    info.date_time = (1980, 1, 1, 0, 0, 0)
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    zip_file.writestr(info, source.read_bytes())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write_notes(out_dir: Path, zip_path: Path, checksum: str, file_count: int) -> None:
    notes = out_dir / 'olivos-plugin-developer-release-notes.md'
    notes.write_text(
        '\n'.join(
            [
                '# olivos-plugin-developer latest',
                '',
                'This release is generated automatically from the `olivos-plugin-developer/` directory.',
                '',
                f'- Asset: `{zip_path.name}`',
                f'- Files packaged: `{file_count}`',
                f'- SHA256: `{checksum}`',
                '',
            ]
        ),
        encoding='utf-8',
    )


def main() -> None:
    args = parse_args()
    skill_dir = Path(args.skill_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    ensure_skill_dir(skill_dir)

    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / ZIP_NAME
    files = iter_files(skill_dir)

    with ZipFile(zip_path, 'w', compression=ZIP_DEFLATED) as zip_file:
        for source in files:
            arcname = Path(skill_dir.name) / source.relative_to(skill_dir)
            add_file(zip_file, source, arcname)

    checksum = sha256(zip_path)
    (out_dir / f'{ZIP_NAME}.sha256').write_text(f'{checksum}  {ZIP_NAME}\n', encoding='utf-8')
    write_notes(out_dir, zip_path, checksum, len(files))
    print(f'Packaged {len(files)} files into {zip_path}')
    print(f'SHA256: {checksum}')


if __name__ == '__main__':
    main()
