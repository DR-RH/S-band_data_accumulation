# S-band DB Server

Standalone FastAPI server for storing and reading decoded S-band payload rows.

## Setup

```bash
python -m pip install -r requirements.txt
```

## Run Locally

```bash
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

The downloader UI lives in the separate `../downloader` project.

## Configure DB Path

By default, the server writes SQLite data to:

```text
data/payloads.sqlite
```

Override the DB path with:

```bash
S_BAND_DECODER_DB=/path/to/payloads.sqlite python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Windows PowerShell:

```powershell
$env:S_BAND_DECODER_DB="C:\path\to\payloads.sqlite"
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Listen on all network interfaces with:

```bash
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

## Pipeline Upload

From the processor project (`../processor`):

```bash
S_BAND_DECODER_DB_SERVER=http://127.0.0.1:8000 ./run
```

Windows PowerShell:

```powershell
$env:S_BAND_DECODER_DB_SERVER="http://127.0.0.1:8000"
python run
```

For EC2:

```bash
S_BAND_DECODER_DB_SERVER=http://EC2_PUBLIC_IP:8000 ./run
```

Windows PowerShell:

```powershell
$env:S_BAND_DECODER_DB_SERVER="http://EC2_PUBLIC_IP:8000"
python run
```

## Download Data

Download accumulated rows as CSV:

```text
http://127.0.0.1:8000/downloads/main-hk.csv
http://127.0.0.1:8000/downloads/adcs-hk.csv
http://127.0.0.1:8000/downloads/main-hk.csv?raw=true
http://127.0.0.1:8000/downloads/adcs-hk.csv?raw=true
```

Minimum search filters are available as query parameters:

```text
http://127.0.0.1:8000/downloads/adcs-hk.csv?raw=true&sampling_type=high
http://127.0.0.1:8000/downloads/adcs-hk.csv?raw=true&packet_id=0111010110100011&sampling_type=high
http://127.0.0.1:8000/downloads/main-hk.csv?raw=true&start=2026-05-01T00:00:00+00:00&end=2026-05-03T00:00:00+00:00
http://127.0.0.1:8000/downloads/main-hk.csv?raw=true&order=asc
```

Decoded download uses the latest shared decoder by default. Set `raw=true` to
download stored raw payload rows instead. Archived decoder versions are listed
for UI selection, but version-specific re-decoding is not implemented yet.

The same filters also work on the JSON read endpoints:

```text
http://127.0.0.1:8000/main-hk?packet_id=1101011001000101
http://127.0.0.1:8000/adcs-hk?sampling_type=normal
```
