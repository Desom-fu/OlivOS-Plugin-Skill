#!/usr/bin/env python3
"""Sync bundled OlivOS docs and templates from checked-out upstream repos."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


DOC_MAPPINGS = {
    'Template': 'template',
    'Event': 'event',
    'API': 'api',
    'Message': 'message',
    'UserModule': 'user-module',
    'WebUI': 'webui',
}

IGNORED_NAMES = {
    '.git',
    '.pytest_cache',
    '__pycache__',
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Sync OlivOS docs and template snapshots.')
    parser.add_argument('--repo-root', default='.', help='This repository root.')
    parser.add_argument('--olivos-doc', required=True, help='Checked-out OlivOS-Team/OlivOSDoc path.')
    parser.add_argument('--official-template', required=True, help='Checked-out OlivOSPluginTemplate path.')
    parser.add_argument('--desom-plugin', required=True, help='Checked-out Desom-OlivaDice-Plugin path.')
    return parser.parse_args()


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ['git', '-C', str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
    )
    return result.stdout.strip()


def should_skip(path: Path) -> bool:
    return any(part in IGNORED_NAMES for part in path.parts)


def copy_existing_tree(source: Path, target: Path, extra_dirs: tuple[str, ...] = ()) -> list[str]:
    if not source.is_dir():
        raise SystemExit(f'Source directory not found: {source}')
    if not target.is_dir():
        raise SystemExit(f'Target directory not found: {target}')

    relative_paths = {path.relative_to(target) for path in target.rglob('*') if path.is_file()}
    # Include newly added WebUI assets, not just files already present in the snapshot.
    for directory in extra_dirs:
        relative_paths.update(
            path.relative_to(source) for path in (source / directory).rglob('*') if path.is_file()
        )

    updated: list[str] = []
    for relative_path in sorted(relative_paths):
        if should_skip(relative_path):
            continue

        source_file = source / relative_path
        if source_file.is_file():
            target_file = target / relative_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, target_file)
            updated.append(str(relative_path).replace('\\', '/'))
    return updated


def snapshot_content(directory: Path) -> dict[str, bytes]:
    """Compare bundled content without upstream revision metadata."""
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in directory.rglob('*')
        if path.is_file()
        and path != directory / 'SOURCES.md'
        and not should_skip(path.relative_to(directory))
    }


def sync_docs(olivos_doc: Path, target_dir: Path) -> list[tuple[str, str]]:
    source_dir = olivos_doc / 'docs' / 'DevPlugin'
    if not source_dir.is_dir():
        raise SystemExit(f'OlivOS DevPlugin docs directory not found: {source_dir}')

    markdown_dir = target_dir / 'markdown'
    if not markdown_dir.is_dir():
        raise SystemExit(f'Local markdown directory not found: {markdown_dir}')

    copied: list[tuple[str, str]] = []
    for upstream_name, local_name in sorted(DOC_MAPPINGS.items(), key=lambda item: item[1]):
        source = source_dir / f'{upstream_name}.md'
        if not source.is_file():
            raise SystemExit(f'OlivOS DevPlugin document not found: {source}')
        shutil.copy2(source, markdown_dir / f'{local_name}.md')
        copied.append((f'{local_name}.md', f'docs/DevPlugin/{source.name}'))
    return copied


def commit_date(repo: Path) -> str:
    return run_git(repo, 'show', '-s', '--format=%cI', 'HEAD')


def write_doc_sources(target_dir: Path, olivos_doc: Path, copied: list[tuple[str, str]]) -> None:
    commit = run_git(olivos_doc, 'rev-parse', 'HEAD')
    lines = [
        '# Official OlivOS Documentation Sources',
        '',
        f'Upstream commit date: {commit_date(olivos_doc)}',
        '',
        'GitHub Markdown source files are saved under `markdown/`.',
        'Markdown is the canonical local reference for development.',
        'Revision metadata is refreshed only when bundled documentation content changes.',
        '',
        'GitHub repository: <https://github.com/OlivOS-Team/OlivOSDoc>',
        'Branch: main',
        f'Commit: {commit}',
        '',
        'Documents:',
    ]
    for local_name, upstream_path in copied:
        lines.append(f'- {local_name}: {upstream_path}')
    lines.extend(['', 'Fetch status:', '- markdown: saved', ''])
    (target_dir / 'SOURCES.md').write_text('\n'.join(lines), encoding='utf-8')


def write_template_sources(target_dir: Path, official_template: Path, desom_plugin: Path) -> None:
    official_commit = run_git(official_template, 'rev-parse', 'HEAD')
    desom_commit = run_git(desom_plugin, 'rev-parse', 'HEAD')
    lines = [
        '# Template Sources',
        '',
        'Revision metadata is refreshed only when bundled template content changes.',
        '',
        f'Official template commit date: {commit_date(official_template)}',
        f'Desom template commit date: {commit_date(desom_plugin)}',
        '',
        '- official-native: <https://github.com/OlivOS-Team/OlivOSPluginTemplate>',
        '  branch: main',
        f'  commit: {official_commit}',
        '- light-plugin: <https://github.com/0Desom0/Desom-OlivaDice-Plugin/tree/main/%E7%A4%BA%E4%BE%8B/LightPluginTemplate>',
        '  branch: main',
        f'  commit: {desom_commit}',
        "- rule-plugin: <https://github.com/0Desom0/Desom-OlivaDice-Plugin/tree/main/%E7%A4%BA%E4%BE%8B/Desom%27s_OVO_PluginTemplate>",
        '  branch: main',
        f'  commit: {desom_commit}',
        '',
        'Local paths:',
        '- assets/templates/official-native',
        '- assets/templates/light-plugin',
        '- assets/templates/rule-plugin',
        '',
    ]
    (target_dir / 'SOURCES.md').write_text('\n'.join(lines), encoding='utf-8')


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    olivos_doc = Path(args.olivos_doc).resolve()
    official_template = Path(args.official_template).resolve()
    desom_plugin = Path(args.desom_plugin).resolve()

    skill_dir = repo_root / 'olivos-plugin-developer'
    docs_target = skill_dir / 'references' / 'official-docs'
    templates_target = skill_dir / 'assets' / 'templates'

    docs_before = snapshot_content(docs_target)
    templates_before = snapshot_content(templates_target)

    copied_docs = sync_docs(olivos_doc, docs_target)
    docs_changed = docs_before != snapshot_content(docs_target)
    if docs_changed or not (docs_target / 'SOURCES.md').is_file():
        write_doc_sources(docs_target, olivos_doc, copied_docs)

    example_dir = desom_plugin / '\u793a\u4f8b'
    official_updated = copy_existing_tree(
        official_template,
        templates_target / 'official-native',
        extra_dirs=('OlivOSPluginTemplate/webui',),
    )
    light_updated = copy_existing_tree(example_dir / 'LightPluginTemplate', templates_target / 'light-plugin')
    rule_updated = copy_existing_tree(example_dir / "Desom's_OVO_PluginTemplate", templates_target / 'rule-plugin')
    templates_changed = templates_before != snapshot_content(templates_target)
    if templates_changed or not (templates_target / 'SOURCES.md').is_file():
        write_template_sources(templates_target, official_template, desom_plugin)

    print(f'Synced {len(copied_docs)} OlivOS DevPlugin markdown files.')
    print(f'Synced {len(official_updated)} official-native template files (including WebUI assets).')
    print(f'Synced {len(light_updated)} existing light-plugin template files.')
    print(f'Synced {len(rule_updated)} existing rule-plugin template files.')
    print(f'Bundled content changed: docs={docs_changed}, templates={templates_changed}.')


if __name__ == '__main__':
    main()
