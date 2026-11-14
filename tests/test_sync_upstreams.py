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

    def test_light_webui_module_and_page_are_added_together(self) -> None:
        before = self.sources()
        source = self.desom / '示例' / 'LightPluginTemplate' / 'YourPluginName'
        write_file(source / 'main.py', 'from . import webui\n')
        write_file(source / 'webui.py', '# Light WebUI handler\n')
        write_file(source / 'webui' / 'index.html', '<p>Light settings</p>\n')
        commit(self.desom)
        self.sync()
        target = self.templates_target / 'light-plugin' / 'YourPluginName'
        for relative in ('main.py', 'webui.py', 'webui/index.html'):
            self.assertEqual((target / relative).read_bytes(), (source / relative).read_bytes())
        self.assertEqual(self.sources()[0], before[0])
        self.assertNotEqual(self.sources()[1], before[1])
        commit(self.repo)
        self.sync()
        self.assertEqual(git(self.repo, 'status', '--porcelain'), '')

    def test_missing_developer_webui_fails_instead_of_using_user_guide(self) -> None:
        (self.docs / 'docs' / 'DevPlugin' / 'WebUI.md').unlink()
        result = self.sync(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('WebUI.md', result.stderr)
        self.assertEqual(git(self.repo, 'status', '--porcelain'), '')



class RewriteDocLinksTest(unittest.TestCase):
    """快照里的相对链接必须是快照内可达的目标。

    上游写 `WebUI.md` / `/DevPlugin/UserModule/#_3`，快照统一存小写；
    在大小写敏感的文件系统上原样保留就是死链。
    """

    @classmethod
    def setUpClass(cls) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location('sync_upstreams', SYNC_SCRIPT)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.rewrite = staticmethod(module.rewrite_doc_links)
        cls.bundled = {'template.md', 'event.md', 'api.md', 'message.md', 'user-module.md', 'webui.md'}

    def check(self, text: str) -> str:
        return self.rewrite(text, self.bundled)

    def test_lowercases_bundled_doc_targets(self) -> None:
        self.assertEqual(self.check('[WebUI](WebUI.md)'), '[WebUI](webui.md)')
        self.assertEqual(self.check('[API](API.md#qqguildv2-send-message)'), '[API](api.md#qqguildv2-send-message)')
        self.assertEqual(self.check('[Event](./Event.md#button-click)'), '[Event](./event.md#button-click)')

    def test_maps_site_routes_to_bundled_docs(self) -> None:
        self.assertEqual(self.check('[x](/DevPlugin/UserModule/#_3)'), '[x](user-module.md#_3)')

    def test_keeps_unknown_site_routes_as_absolute_urls(self) -> None:
        self.assertEqual(
            self.check('[x](/OlivOS_DevDoc_Plugin_API/#_3)'),
            '[x](https://doc.olivos.wiki/OlivOS_DevDoc_Plugin_API/#_3)',
        )

    def test_points_unbundled_user_docs_at_upstream(self) -> None:
        self.assertEqual(
            self.check('[x](../User/WebUI.md#webui-configuration)'),
            '[x](https://github.com/OlivOS-Team/OlivOSDoc/blob/main/docs/User/WebUI.md#webui-configuration)',
        )

    def test_leaves_images_and_external_links_alone(self) -> None:
        for text in ('![senpai](img/senpai.png)', '[olivos](https://olivos.wiki)', '[anchor](#_3)'):
            self.assertEqual(self.check(text), text)


if __name__ == '__main__':
    unittest.main()
