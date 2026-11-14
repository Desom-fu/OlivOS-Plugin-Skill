"""Exercise the OPK packer against throwaway plugin directories."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile


SCRIPT = Path(__file__).resolve().parents[1] / 'olivos-plugin-developer' / 'scripts' / 'package_opk.py'
SPEC = importlib.util.spec_from_file_location('package_opk', SCRIPT)
assert SPEC and SPEC.loader
package_opk = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package_opk)


MANIFEST = {
    'name': '演示插件',
    'author': 'Tester',
    'namespace': 'Demo',
    'message_mode': 'olivos_string',
    'info': 'fixture',
    'version': '1.0.0',
    'svn': 1,
    'compatible_svn': 190,
    'priority': 30000,
}


def write_text(path: Path, text: str, encoding: str = 'utf-8') -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=encoding)


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


class PackageOpkTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix='olivos-opk-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plugin = self.root / 'Demo'
        self.out = self.root / 'dist'
        write_text(self.plugin / 'app.json', json.dumps(MANIFEST, ensure_ascii=False), 'utf-8')
        write_text(self.plugin / '__init__.py', 'from . import main\n')
        write_text(self.plugin / 'main.py', 'class Event(object):\n    pass\n')
        write_text(self.plugin / 'webui' / 'index.html', '<html></html>')

    def run_main(self, *args: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = package_opk.main(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def pack(self, *extra: str) -> tuple[int, str, str]:
        return self.run_main(str(self.plugin), '-o', str(self.out), *extra)

    def names(self, opk: Path) -> list[str]:
        with ZipFile(opk) as archive:
            return archive.namelist()

    def test_packs_flat_archive_with_required_files(self) -> None:
        code, out, _ = self.pack()
        self.assertEqual(code, 0, out)
        opk = self.out / 'Demo.opk'
        self.assertTrue(opk.is_file())
        names = self.names(opk)
        for expected in ('app.json', '__init__.py', 'main.py', 'webui/index.html'):
            self.assertIn(expected, names)
        self.assertFalse([name for name in names if name.startswith('Demo/')], names)
        self.assertIn('namespace=Demo', out)

    def test_missing_required_file_fails(self) -> None:
        (self.plugin / 'main.py').unlink()
        code, _, err = self.pack()
        self.assertEqual(code, 1)
        self.assertIn('main.py', err)
        self.assertFalse((self.out / 'Demo.opk').exists())

    def test_allow_missing_downgrades_to_warning(self) -> None:
        (self.plugin / 'main.py').unlink()
        code, out, _ = self.pack('--allow-missing')
        self.assertEqual(code, 0, out)
        self.assertIn('[warn]', out)
        self.assertTrue((self.out / 'Demo.opk').is_file())

    def test_bom_manifest_is_rejected(self) -> None:
        write_text(self.plugin / 'app.json', json.dumps(MANIFEST, ensure_ascii=False), 'utf-8-sig')
        code, _, err = self.pack()
        self.assertEqual(code, 1)
        self.assertIn('BOM', err)
        self.assertFalse((self.out / 'Demo.opk').exists())

    def test_invalid_json_manifest_is_rejected(self) -> None:
        write_text(self.plugin / 'app.json', '{"name": "Demo",}')
        code, _, err = self.pack()
        self.assertEqual(code, 1)
        self.assertIn('JSON', err)

    def test_namespace_must_exist(self) -> None:
        write_text(self.plugin / 'app.json', json.dumps({'name': 'Demo'}))
        code, _, err = self.pack()
        self.assertEqual(code, 1)
        self.assertIn('namespace', err)

    def test_namespace_mismatch_warns_but_packs(self) -> None:
        manifest = dict(MANIFEST, namespace='SomethingElse')
        write_text(self.plugin / 'app.json', json.dumps(manifest, ensure_ascii=False), 'utf-8')
        code, out, _ = self.pack()
        self.assertEqual(code, 0, out)
        self.assertIn('[warn]', out)
        self.assertIn('namespace "SomethingElse"', out)
        self.assertTrue((self.out / 'Demo.opk').is_file())

    def test_excludes_caches_vcs_and_leftovers(self) -> None:
        write_bytes(self.plugin / '__pycache__' / 'main.cpython-311.pyc', b'\x00')
        write_text(self.plugin / '.git' / 'config', '[core]\n')
        write_bytes(self.plugin / 'old.opk', b'stale')
        write_bytes(self.plugin / 'notes.zip', b'stale')
        write_text(self.plugin / 'main.py.bak', 'old')
        write_bytes(self.plugin / 'Thumbs.db', b'\x00')
        code, _, _ = self.pack()
        self.assertEqual(code, 0)
        names = self.names(self.out / 'Demo.opk')
        for excluded in ('__pycache__/main.cpython-311.pyc', '.git/config', 'old.opk', 'notes.zip',
                         'main.py.bak', 'Thumbs.db'):
            self.assertNotIn(excluded, names)

    def test_check_only_writes_nothing(self) -> None:
        code, out, _ = self.pack('--check-only')
        self.assertEqual(code, 0, out)
        self.assertIn('[ok]', out)
        self.assertFalse(self.out.exists())

    def test_sha256_sidecar_matches_archive(self) -> None:
        code, out, _ = self.pack('--sha256')
        self.assertEqual(code, 0, out)
        opk = self.out / 'Demo.opk'
        sidecar = self.out / 'Demo.opk.sha256'
        self.assertTrue(sidecar.is_file())
        digest = hashlib.sha256(opk.read_bytes()).hexdigest()
        self.assertEqual(sidecar.read_text(encoding='utf-8').split()[0], digest)

    def test_refuses_overwrite_without_force(self) -> None:
        self.assertEqual(self.pack()[0], 0)
        code, _, err = self.pack()
        self.assertEqual(code, 1)
        self.assertIn('--force', err)
        self.assertEqual(self.pack('--force')[0], 0)

    def test_custom_archive_name(self) -> None:
        code, _, _ = self.pack('--name', 'CustomName')
        self.assertEqual(code, 0)
        self.assertTrue((self.out / 'CustomName.opk').is_file())

    def test_not_a_directory(self) -> None:
        code, _, err = self.run_main(str(self.root / 'missing'), '-o', str(self.out))
        self.assertEqual(code, 1)
        self.assertIn('not a directory', err)


if __name__ == '__main__':
    unittest.main()
