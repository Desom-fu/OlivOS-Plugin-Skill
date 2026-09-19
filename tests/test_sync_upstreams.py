"""Exercise synchronization against isolated upstream Git repositories."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SYNC_SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'sync_upstreams.py'


def write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ['git', '-C', str(repo), *args], check=True, capture_output=True, text=True, encoding='utf-8'
    )
    return result.stdout.strip()


def commit(repo: Path) -> None:
    git(repo, 'add', '.')
    git(
        repo, '-c', 'user.name=Sync Test', '-c', 'user.email=sync-test@example.invalid',
        '-c', 'commit.gpgsign=false',
        'commit', '--allow-empty', '-m', 'Fixture update',
    )


class SyncUpstreamsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix='olivos-sync-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'skill-repo'
        self.docs = self.root / 'OlivOSDoc'
        self.official = self.root / 'OlivOSPluginTemplate'
        self.desom = self.root / 'Desom-OlivaDice-Plugin'
        self.skill = self.repo / 'olivos-plugin-developer'
        self.docs_target = self.skill / 'references' / 'official-docs'
        self.templates_target = self.skill / 'assets' / 'templates'
        self.webui_target = self.templates_target / 'official-native' / 'OlivOSPluginTemplate' / 'webui'

        for repo in (self.repo, self.docs, self.official, self.desom):
            repo.mkdir()
            git(repo, 'init', '-q')
            git(repo, 'config', 'core.autocrlf', 'false')

        for name in ('Template', 'Event', 'API', 'Message', 'UserModule', 'WebUI'):
            write_file(self.docs / 'docs' / 'DevPlugin' / f'{name}.md', f'# Developer {name}\n')
        write_file(self.docs / 'docs' / 'User' / 'WebUI.md', '# User guide; do not bundle\n')
        (self.docs_target / 'markdown').mkdir(parents=True)
        for upstream, source_path, target_path in (
            (self.official, 'OlivOSPluginTemplate/main.py', 'official-native/OlivOSPluginTemplate/main.py'),
            (self.desom, '示例/LightPluginTemplate/YourPluginName/main.py', 'light-plugin/YourPluginName/main.py'),
            (self.desom, "示例/Desom's_OVO_PluginTemplate/YourPluginName/main.py", 'rule-plugin/YourPluginName/main.py'),
        ):
            write_file(upstream / source_path, '# Current template\n')
            write_file(self.templates_target / target_path, '# Old snapshot\n')
        write_file(self.official / 'OlivOSPluginTemplate' / 'webui' / 'index.html', '<p>WebUI</p>\n')
        for repo in (self.docs, self.official, self.desom):
            commit(repo)

        self.sync()
        commit(self.repo)

    def sync(self, *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable, str(SYNC_SCRIPT), '--repo-root', str(self.repo),
                '--olivos-doc', str(self.docs), '--official-template', str(self.official),
                '--desom-plugin', str(self.desom),
            ],
            check=check, capture_output=True, text=True, encoding='utf-8',
        )

    def sources(self) -> tuple[bytes, bytes]:
        return (
            (self.docs_target / 'SOURCES.md').read_bytes(),
            (self.templates_target / 'SOURCES.md').read_bytes(),
        )

    def test_bundles_developer_webui_and_missing_template_assets(self) -> None:
        self.assertEqual(
            (self.docs_target / 'markdown' / 'webui.md').read_text(encoding='utf-8'), '# Developer WebUI\n'
        )
        self.assertEqual((self.webui_target / 'index.html').read_text(encoding='utf-8'), '<p>WebUI</p>\n')
        self.assertIn(b'webui.md: docs/DevPlugin/WebUI.md', self.sources()[0])

    def test_repeated_sync_leaves_no_changes(self) -> None:
        before = self.sources()
        self.sync()
        self.assertEqual(self.sources(), before)
        self.assertEqual(git(self.repo, 'status', '--porcelain'), '')

    def test_revision_only_and_unrelated_changes_leave_no_changes(self) -> None:
        before = self.sources()
        for repo in (self.docs, self.official, self.desom):
            old_commit = git(repo, 'rev-parse', 'HEAD')
            commit(repo)
            self.assertNotEqual(git(repo, 'rev-parse', 'HEAD'), old_commit)
        self.sync()
        self.assertEqual(self.sources(), before)
        self.assertEqual(git(self.repo, 'status', '--porcelain'), '')

        for repo in (self.docs, self.official, self.desom):
            write_file(repo / 'README.md', 'Unrelated upstream change\n')
            commit(repo)
        write_file(self.docs / 'docs' / 'User' / 'WebUI.md', '# Updated user guide\n')
        commit(self.docs)
        self.sync()
        self.assertEqual(self.sources(), before)
        self.assertEqual(git(self.repo, 'status', '--porcelain'), '')

    def test_webui_document_change_refreshes_only_document_sources(self) -> None:
        before = self.sources()
        write_file(self.docs / 'docs' / 'DevPlugin' / 'WebUI.md', '# Updated interface\n')
        commit(self.docs)
        self.sync()
        self.assertEqual(
            (self.docs_target / 'markdown' / 'webui.md').read_text(encoding='utf-8'), '# Updated interface\n'
        )
        self.assertIn(git(self.docs, 'rev-parse', 'HEAD').encode(), self.sources()[0])
        self.assertNotEqual(self.sources()[0], before[0])
        self.assertEqual(self.sources()[1], before[1])

    def test_template_change_refreshes_only_template_sources(self) -> None:
        before = self.sources()
        write_file(self.desom / '示例' / 'LightPluginTemplate' / 'YourPluginName' / 'main.py', '# Changed\n')
        commit(self.desom)
        self.sync()
        self.assertEqual(
            (self.templates_target / 'light-plugin' / 'YourPluginName' / 'main.py').read_text(encoding='utf-8'),
            '# Changed\n',
        )
        self.assertEqual(self.sources()[0], before[0])
        self.assertIn(git(self.desom, 'rev-parse', 'HEAD').encode(), self.sources()[1])
        self.assertNotEqual(self.sources()[1], before[1])

    def test_new_webui_asset_is_synced(self) -> None:
        before = self.sources()
        write_file(self.official / 'OlivOSPluginTemplate' / 'webui' / 'assets' / 'page.js', 'const page = 1;\n')
        commit(self.official)
        self.sync()
        self.assertEqual(
            (self.webui_target / 'assets' / 'page.js').read_text(encoding='utf-8'), 'const page = 1;\n'
        )
        self.assertIn('?? ', git(self.repo, 'status', '--porcelain'))
        self.assertEqual(self.sources()[0], before[0])
        self.assertNotEqual(self.sources()[1], before[1])

    def test_missing_developer_webui_fails_instead_of_using_user_guide(self) -> None:
        (self.docs / 'docs' / 'DevPlugin' / 'WebUI.md').unlink()
        result = self.sync(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('WebUI.md', result.stderr)
        self.assertEqual(git(self.repo, 'status', '--porcelain'), '')


if __name__ == '__main__':
    unittest.main()
