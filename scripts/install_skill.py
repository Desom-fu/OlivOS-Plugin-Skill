#!/usr/bin/env python3
"""Install the olivos-plugin-developer skill into every supported local client.

The repository's ``olivos-plugin-developer/`` directory is the single source of
truth. This script mirrors that directory into each client's personal skills
directory, backs up whatever it replaces, then verifies every copied file by
SHA-256 so a partial install can never pass silently.

Client skill locations (resolved against the user home):

    agents       ~/.agents/skills            shared convention, Grok/Antigravity read it
    codex        ~/.codex/skills             Codex
    claudecode   ~/.claude/skills            Claude Code (also scanned by Grok compat)
    grok         ~/.grok/skills              Grok CLI
    antigravity  ~/.gemini/config/skills     Antigravity global customization root
    workbuddy    ~/.workbuddy/skills         WorkBuddy
    dsh          ~/.dsh/skills               DSH
    qoderwork    ~/.qoderworkcn/skills       QoderWork CN

Examples:

    python scripts/install_skill.py --dry-run
    python scripts/install_skill.py
    python scripts/install_skill.py --verify
    python scripts/install_skill.py --only codex,claudecode,grok,antigravity,agents
    python scripts/install_skill.py --no-backup
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path


SKILL_NAME = 'olivos-plugin-developer'

# client key -> (skills directory relative to the user home, human label)
TARGETS: dict[str, tuple[str, str]] = {
    'agents': ('.agents/skills', 'Agents shared convention'),
    'codex': ('.codex/skills', 'Codex'),
    'claudecode': ('.claude/skills', 'Claude Code'),
    'grok': ('.grok/skills', 'Grok CLI'),
    'antigravity': ('.gemini/config/skills', 'Antigravity (global)'),
    'workbuddy': ('.workbuddy/skills', 'WorkBuddy'),
    'dsh': ('.dsh/skills', 'DSH'),
    'qoderwork': ('.qoderworkcn/skills', 'QoderWork CN'),
}

EXCLUDED_DIRS = {
    '.git',
    '.pytest_cache',
    '.ruff_cache',
    '__pycache__',
    '.venv',
}
EXCLUDED_FILES = {
    '.DS_Store',
    'Thumbs.db',
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Install or update the olivos-plugin-developer skill in local AI clients.'
    )
    parser.add_argument(
        '--repo-root',
        default=None,
        help='Repository root. Defaults to the parent directory of scripts/.',
    )
    parser.add_argument(
        '--only',
        default=None,
        help='Comma-separated client keys to install. Defaults to every known client.',
    )
    parser.add_argument(
        '--skip',
        default=None,
        help='Comma-separated client keys to leave untouched.',
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Delete an existing install instead of moving it to the backup directory.',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Report the planned actions without touching the filesystem.',
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Only compare each installed copy against the source, then exit.',
    )
    return parser.parse_args()


def split_keys(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


def resolve_clients(args: argparse.Namespace) -> list[str]:
    """Return the ordered client keys to process, validating every requested key."""
    unknown = [key for key in (*split_keys(args.only), *split_keys(args.skip)) if key not in TARGETS]
    if unknown:
        known = ', '.join(TARGETS)
        raise SystemExit(f'Unknown client key(s): {", ".join(unknown)}. Known keys: {known}')

    selected = split_keys(args.only) or list(TARGETS)
    skipped = set(split_keys(args.skip))
    return [key for key in selected if key not in skipped]


def should_include(path: Path) -> bool:
    if any(part in EXCLUDED_DIRS for part in path.parts):
        return False
    return path.name not in EXCLUDED_FILES


def iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for dirpath, dir_names, file_names in os.walk(root):
        current = Path(dirpath)
        dir_names[:] = sorted(name for name in dir_names if name not in EXCLUDED_DIRS)
        files.extend(current / name for name in sorted(file_names) if should_include(current / name))
    return files


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot(root: Path) -> dict[str, str]:
    """Map relative POSIX path -> content hash for every tracked file."""
    if not root.is_dir():
        return {}
    return {path.relative_to(root).as_posix(): sha256(path) for path in iter_files(root)}


def describe_diff(expected: dict[str, str], actual: dict[str, str]) -> list[str]:
    problems: list[str] = []
    for relative in sorted(set(expected) - set(actual)):
        problems.append(f'missing: {relative}')
    for relative in sorted(set(actual) - set(expected)):
        problems.append(f'unexpected: {relative}')
    for relative in sorted(set(expected) & set(actual)):
        if expected[relative] != actual[relative]:
            problems.append(f'content mismatch: {relative}')
    return problems


def remove_path(path: Path) -> None:
    """Remove a file, a symlink/junction, or a real directory tree."""
    if path.is_symlink() or os.path.islink(path):
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def install_one(
    key: str,
    source: Path,
    expected: dict[str, str],
    dest: Path,
    backup_root: Path,
    use_backup: bool,
    dry_run: bool,
) -> tuple[str, str]:
    """Install one client. Returns (status, detail) where status is OK/SKIP/FAIL."""
    existed = dest.exists()
    if dry_run:
        action = 'replace' if existed else 'create'
        return 'SKIP', f'dry-run: would {action} {dest}'

    dest.parent.mkdir(parents=True, exist_ok=True)

    backup_note = ''
    if existed:
        if use_backup:
            backup_dir = backup_root / key / SKILL_NAME
            backup_dir.parent.mkdir(parents=True, exist_ok=True)
            if backup_dir.exists():
                remove_path(backup_dir)
            shutil.move(str(dest), str(backup_dir))
            backup_note = 'backup kept'
        else:
            remove_path(dest)
            backup_note = 'no backup'

    shutil.copytree(
        source,
        dest,
        ignore=shutil.ignore_patterns(*EXCLUDED_DIRS, *EXCLUDED_FILES),
        dirs_exist_ok=True,
    )

    problems = describe_diff(expected, snapshot(dest))
    if problems:
        return 'FAIL', f'{len(problems)} verification problem(s): ' + '; '.join(problems[:5])

    action = 'replaced' if existed else 'created'
    detail = f'{action}, {len(expected)} files verified'
    if backup_note:
        detail += f', {backup_note}'
    return 'OK', detail


def verify_one(dest: Path, expected: dict[str, str]) -> tuple[str, str]:
    """Compare an installed copy against the source. Returns (status, detail)."""
    if not dest.is_dir():
        return 'FAIL', 'not installed'
    problems = describe_diff(expected, snapshot(dest))
    if problems:
        return 'FAIL', f'{len(problems)} problem(s): ' + '; '.join(problems[:5])
    return 'OK', f'{len(expected)} files match source'


def main() -> None:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='replace')
    args = parse_args()
    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parents[1]
    source = repo_root / SKILL_NAME

    if not (source / 'SKILL.md').is_file():
        raise SystemExit(f'Skill source not found: {source / "SKILL.md"}')

    frontmatter = (source / 'SKILL.md').read_text(encoding='utf-8-sig')
    if f'name: {SKILL_NAME}' not in frontmatter:
        raise SystemExit(f'SKILL.md frontmatter does not declare name: {SKILL_NAME}')

    expected = snapshot(source)
    clients = resolve_clients(args)
    home = Path.home()
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    backup_root = Path(tempfile.gettempdir()) / f'{SKILL_NAME}-backup-{stamp}'

    if args.verify and (args.dry_run or args.no_backup):
        raise SystemExit('--verify cannot be combined with --dry-run or --no-backup')

    print(f'Source   : {source}')
    print(f'Files    : {len(expected)}')
    print(f'Clients  : {", ".join(clients)}')
    if args.verify:
        print('Mode     : verify (nothing will be written)')
    elif args.dry_run:
        print('Mode     : dry-run (nothing will be written)')
    elif args.no_backup:
        print('Mode     : install (existing installs are deleted, no backup)')
    else:
        print(f'Backup   : {backup_root}')
    print()

    width = max(len(key) for key in clients) if clients else 6
    results: list[tuple[str, str, str]] = []

    for key in clients:
        rel, label = TARGETS[key]
        dest = home / rel / SKILL_NAME
        if args.verify:
            status, detail = verify_one(dest, expected)
        else:
            status, detail = install_one(
                key=key,
                source=source,
                expected=expected,
                dest=dest,
                backup_root=backup_root,
                use_backup=not args.no_backup,
                dry_run=args.dry_run,
            )
        results.append((status, key, detail))
        print(f'[{status:<4}] {key:<{width}}  ({label})')
        print(f'         -> {dest}')
        print(f'         {detail}')

    failed = [item for item in results if item[0] == 'FAIL']
    print()
    if args.verify:
        matched = len(results) - len(failed)
        print(f'Verified {matched}/{len(results)} client(s), {len(failed)} mismatch(es).')
    elif args.dry_run:
        print(f'Dry run complete: {len(results)} client(s) inspected, no changes written.')
    else:
        changed = len([item for item in results if item[0] == 'OK'])
        print(f'Installed {changed}/{len(results)} client(s), {len(failed)} failed.')
        if not args.no_backup and changed:
            print(f'Backups (previous installs): {backup_root}')

    if failed:
        sys.exit(1)


if __name__ == '__main__':
    main()
