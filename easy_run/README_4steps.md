# Simple 4-step runner

このフォルダは、初心者向けの簡易実行用フォルダです。

## 初回だけ実行

最初に1回だけ、環境作成用ファイルを実行する。

- Windows: `00_setup_all.bat`
- macOS: `00_setup_all.command`

これは各ソフトの `.venv` を作成し、各 `requirements.txt` をインストールする。
すでに `.venv` がある場合は再利用する。

## 毎回の4ステップ

1. `00_TLM_INPUT_ALIAS_PLACEHOLDER.txt` を、あとで TLM 投入フォルダのエイリアスに置き換える。
   - エイリアスの向き先: `../processor/input/unprocessed/`
   - 運用時は、そのエイリアスへ TLM の `.txt` ファイルを入れる。
2. サーバを起動する。
   - Windows: `01_start_server.bat`
   - macOS: `01_start_server.command`
3. processor を実行する。
   - Windows: `02_run_processor.bat`
   - macOS: `02_run_processor.command`
4. viewer を開く。
   - `../downloader/index.html` を開く。
   - 便利用: Windows は `03_open_viewer.bat`、macOS は `03_open_viewer.command` でも開ける。

## 注意

- サーバ起動ファイルは起動したままにする。閉じると viewer から DB を見られない。
- processor は `../processor/input/unprocessed/` にある `.txt` を処理する。
- `02_run_processor` は `--no-move` 付きで実行するため、投入した TLM ファイルは処理後も残る。
- `.venv` と `requirements.txt` は各ソフトのフォルダ内にある前提。
- `.venv` がない場合は、先に `00_setup_all` を実行する。
