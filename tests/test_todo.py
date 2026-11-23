import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import todo


SCRIPT = Path(todo.__file__).resolve()


class TodoTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.data = self.root / "todos.json"

    def run_cli(self, *args, success=True):
        result = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.root,
                                text=True, encoding="utf-8", capture_output=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("エラー", result.stderr)
        return result

    def test_empty_and_missing_file(self):
        self.assertEqual(self.run_cli("list").stdout.strip(), "タスクはありません")
        self.assertFalse(self.data.exists())
        self.run_cli("done", "1", success=False)
        self.assertFalse(self.data.exists())

    def test_persistence_and_completion_across_processes(self):
        self.run_cli("add", "  買い物  ")
        self.run_cli("add", "掃除")
        self.assertEqual(self.run_cli("list").stdout, "1 [未完了] 買い物\n2 [未完了] 掃除\n")
        self.run_cli("done", "1")
        self.assertIn("1 [完了] 買い物", self.run_cli("list").stdout)
        before = self.data.read_bytes()
        self.assertIn("完了済み", self.run_cli("done", "1").stdout)
        self.assertEqual(before, self.data.read_bytes())
        self.assertEqual(json.loads(before)[0], {"id": 1, "title": "買い物", "completed": True})

    def test_order_and_maximum_id(self):
        self.data.write_text(json.dumps([
            {"id": 8, "title": "後", "completed": False},
            {"id": 3, "title": "先", "completed": True}]), encoding="utf-8")
        self.run_cli("add", "追加")
        self.assertEqual(self.run_cli("list").stdout.splitlines(),
                         ["3 [完了] 先", "8 [未完了] 後", "9 [未完了] 追加"])

    def test_invalid_arguments_and_blank_title(self):
        for args in [(), ("unknown",), ("add",), ("add", " \t "),
                     ("list", "extra"), ("done",), ("done", "abc"), ("done", "0")]:
            with self.subTest(args=args):
                self.run_cli(*args, success=False)
        self.assertFalse(self.data.exists())

    def test_missing_id_preserves_file(self):
        self.run_cli("add", "保存")
        before = self.data.read_bytes()
        self.assertIn("存在しません", self.run_cli("done", "99", success=False).stderr)
        self.assertEqual(before, self.data.read_bytes())

    def test_corrupt_data_is_never_overwritten(self):
        valid = {"id": 1, "title": "タスク", "completed": False}
        bad_values = ["{", "{}", "null", '[1]',
                      json.dumps([dict(valid, id=True)]),
                      json.dumps([dict(valid, id=0)]),
                      json.dumps([dict(valid, title=" ")]),
                      json.dumps([dict(valid, completed=1)]),
                      json.dumps([dict(valid, title=2)]),
                      json.dumps([{"id": 1}]), json.dumps([valid, valid])]
        for raw in [s.encode() for s in bad_values] + [b'\xff']:
            self.data.write_bytes(raw)
            for args in [("list",), ("add", "追加"), ("done", "1")]:
                with self.subTest(raw=raw, args=args):
                    self.assertIn("壊れています", self.run_cli(*args, success=False).stderr)
                    self.assertEqual(raw, self.data.read_bytes())

    def test_help(self):
        for args in [("--help",), ("add", "--help"), ("done", "--help")]:
            self.assertIn("使い方", self.run_cli(*args).stdout)
        self.assertFalse(self.data.exists())

    def test_read_failure(self):
        self.data.mkdir()
        self.assertIn("読み込めません", self.run_cli("list", success=False).stderr)

    def test_write_failure_preserves_original_and_cleans_temporary(self):
        self.data.write_text("[]", encoding="utf-8")
        with patch("todo.os.replace", side_effect=PermissionError("書き込み禁止")):
            with self.assertRaisesRegex(todo.TodoError, "書き込めません"):
                todo.save_tasks(self.data, [{"id": 1, "title": "追加", "completed": False}])
        self.assertEqual(self.data.read_text(), "[]")
        self.assertEqual(list(self.root.iterdir()), [self.data])

    def test_write_failure_returns_nonzero(self):
        with patch("todo.load_tasks", return_value=[]), patch(
                "todo.tempfile.NamedTemporaryFile", side_effect=OSError("書き込み禁止")):
            with contextlib.redirect_stderr(io.StringIO()) as error:
                self.assertEqual(todo.main(["add", "追加"]), 1)
        self.assertIn("書き込めません", error.getvalue())


if __name__ == "__main__":
    unittest.main()
