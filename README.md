# ToDo管理CLI

Python 3.10以上で動作します。外部ライブラリのインストールは不要です。

```bash
python3 todo.py add "買い物"
python3 todo.py list
python3 todo.py done 1
python3 todo.py --help
```

`list` はID、完了状態、タイトルをID順に表示します。タイトル前後の空白は除去します。
完了済みのIDに再び `done` を実行しても正常終了します。

データは**実行時のカレントディレクトリ**の `todos.json` にUTF-8で保存します。
別のディレクトリから使う場合は、`python3 /path/to/croud_test/todo.py list` のように実行してください。
ファイルがなければ空の一覧として扱い、最初の追加時に作成します。
不正な引数、存在しないID、壊れたデータ、読み書き失敗では日本語のエラーを表示し非ゼロで終了します。
壊れたデータは上書きしません。

テストはリポジトリのルートで実行します。標準の `unittest` と一時ディレクトリを使用します。

```bash
python3 -m unittest discover -s tests -v
```

既存の `pyproject.toml` はPython 3.14以上のパッケージ雛形用です。
このCLIはパッケージをインストールせず、上記コマンドで直接実行できます。
