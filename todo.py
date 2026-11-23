"""標準ライブラリのみで動作するToDo管理CLI。"""

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile


class TodoError(Exception):
    """利用者に表示するエラー。"""


class JapaneseParser(argparse.ArgumentParser):
    def format_usage(self):
        return super().format_usage().replace("usage: ", "使い方: ", 1)

    def format_help(self):
        return super().format_help().replace("usage: ", "使い方: ", 1)

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(2, "エラー: 引数が不正です。使い方は --help で確認してください。\n")


def load_tasks(path):
    try:
        with path.open(encoding="utf-8") as stream:
            tasks = json.load(stream)
    except FileNotFoundError:
        return []
    except (ValueError, UnicodeError) as exc:
        raise TodoError("保存データが壊れています。") from exc
    except OSError as exc:
        raise TodoError(f"保存データを読み込めません: {exc}") from exc
    if not isinstance(tasks, list):
        raise TodoError("保存データが壊れています: 一覧ではありません。")
    ids = set()
    for task in tasks:
        if (not isinstance(task, dict)
                or type(task.get("id")) is not int or task["id"] < 1
                or task["id"] in ids
                or not isinstance(task.get("title"), str)
                or not task["title"].strip()
                or type(task.get("completed")) is not bool):
            raise TodoError("保存データが壊れています: タスクの形式が不正です。")
        ids.add(task["id"])
    return tasks


def save_tasks(path, tasks):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                         dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(tasks, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    except OSError as exc:
        raise TodoError(f"保存データを書き込めません: {exc}") from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def make_parser():
    parser = JapaneseParser(description="ToDoタスクを管理します。", add_help=False,
                            usage="%(prog)s [-h] {add,list,done} ...")
    parser.add_argument("-h", "--help", action="help", help="使い方を表示して終了")
    parser._positionals.title = "操作"
    parser._optionals.title = "オプション"
    commands = parser.add_subparsers(dest="command", required=True, title="コマンド")
    for name, description, argument in (
        ("add", "未完了のタスクを追加", "title"),
        ("list", "タスクをID順に表示", None),
        ("done", "指定IDのタスクを完了", "id"),
    ):
        command = commands.add_parser(name, help=description, description=description,
                                      add_help=False)
        command._positionals.title = "引数"
        command._optionals.title = "オプション"
        command.add_argument("-h", "--help", action="help", help="使い方を表示して終了")
        if argument:
            command.add_argument(argument, metavar="タイトル" if argument == "title" else "ID",
                                 type=str if argument == "title" else int)
    return parser


def main(argv=None):
    args = make_parser().parse_args(argv)
    path = Path("todos.json")
    try:
        if args.command == "add" and not args.title.strip():
            raise TodoError("タイトルに空白以外の文字を入力してください。")
        tasks = load_tasks(path)
        if args.command == "add":
            task = {"id": max((t["id"] for t in tasks), default=0) + 1,
                    "title": args.title.strip(), "completed": False}
            tasks.append(task)
            save_tasks(path, tasks)
            print(f"タスクを追加しました: {task['id']} {task['title']}")
        elif args.command == "list":
            if not tasks:
                print("タスクはありません")
            for task in sorted(tasks, key=lambda task: task["id"]):
                state = "完了" if task["completed"] else "未完了"
                print(f"{task['id']} [{state}] {task['title']}")
        else:
            task = next((task for task in tasks if task["id"] == args.id), None)
            if task is None:
                raise TodoError(f"ID {args.id} のタスクは存在しません。")
            if task["completed"]:
                print(f"ID {args.id} のタスクは完了済みです。")
            else:
                task["completed"] = True
                save_tasks(path, tasks)
                print(f"ID {args.id} のタスクを完了にしました。")
    except TodoError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
