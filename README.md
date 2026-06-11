# S-band Workspace

This folder groups the S-band tools while keeping each app independent.

```text
s_band/
  processor/      # telemetry pipeline and development entries
  server/         # FastAPI DB/API server. this is for the test development. it will not be used in product version
  downloader/     # standalone browser downloader/viewer
  decoder_core/   # shared decoder package used by processor and server
```

## Run server

```bash
cd server
python -m uvicorn app:app --reload
```

Open http://127.0.0.1:8000/docs.

## Run downloader

```bash
cd downloader
python -m http.server 8080
```

Open http://127.0.0.1:8080.

## Run processor

```bash
cd processor
python -m dev.run_pipeline
```

Raw telemetry input goes in `processor/input/unprocessed/`.

## Windows Notes

Use Python 3.11. From PowerShell:

```powershell
cd processor
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m dev.run_pipeline
```

The Unix-style `./run` shortcut can also be launched as `python run` on
Windows.
