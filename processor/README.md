# S-band Decoder

This repository decodes S-band telemetry logs into structured decoded outputs.
The pipeline folders are named by responsibility instead of execution order so
the flow can change without forcing folder renames.

## Pipeline Flow

```mermaid
flowchart TD
    A["Raw telemetry log (.txt)"] --> B["ingest_raw_log"]
    B --> C["verify_crc"]
    C --> D["parse_packets"]
    D --> E["build_decodable_payloads"]
    E --> F["decode_payloads"]
    F --> G["Decoded CSV outputs"]
```

## Stages

| Stage | Folder | Purpose |
| --- | --- | --- |
| Ingest raw log | `pipeline/ingest_raw_log/` | Reads raw telemetry text, normalizes it, extracts timestamps, and builds timestamp-injected binary data. |
| Verify CRC | `pipeline/verify_crc/` | Splits packet-like binary data and keeps packets whose CRC is valid for the selected GSE format. |
| Parse packets | `pipeline/parse_packets/` | Converts verified packets into structured rows using packet structure JSON files from `config/`. |
| Build decodable payloads | `pipeline/build_decodable_payloads/` | Sorts packets, detects missing packets, reconstructs payload chunks, and writes intermediate decodable data. |
| Decode payloads | `pipeline/decode_payloads/` | Dispatches decodable chunks to the appropriate domain decoder and writes decoded CSV outputs. |

## Main Entry Point

`app/main.py` is the current orchestration entry point. Conceptually, it runs:

```python
timestamped_binary = build_timestamped_binary_from_log(path)
valid_binary = verify_crc(timestamped_binary, gse, file_name)
packets_df = parse_into_df(valid_binary, gse, file_name)
decodable_dir = process_decodable_df(packets_df, file_name)
decode.run(decodable_dir)
```

## Development Entries

Use the `dev/` scripts when developing or debugging one stage at a time. They
are thin wrappers around the real pipeline modules and print the next artifact
path after each run.

Run the full pipeline for one log:

```bash
python dev/run_pipeline.py input/unprocessed/example.txt
```

Short form:

```bash
./run input/unprocessed/example.txt
```

On Windows PowerShell, use:

```powershell
python run input/unprocessed/example.txt
```

If you keep raw `.txt` logs in `input/unprocessed/`, `./run` runs every `.txt`
file in that folder and moves each successfully processed file to
`input/processed/`:

```bash
./run
```

Keep input files in place for repeatable development runs:

```bash
./run --no-move
```

By default, payload rows are uploaded to the DB server over HTTP. The default
server URL is `http://127.0.0.1:8000`; override it with an environment variable
or a command option:

```bash
S_BAND_DECODER_DB_SERVER=http://EC2_PUBLIC_IP:8000 ./run
./run input/unprocessed/example.txt --db-server http://EC2_PUBLIC_IP:8000
```

Windows PowerShell:

```powershell
$env:S_BAND_DECODER_DB_SERVER="http://EC2_PUBLIC_IP:8000"
python run
python run input/unprocessed/example.txt --db-server http://EC2_PUBLIC_IP:8000
```

If the DB server cannot be reached, upload payloads are saved as JSON files in
`output/pending_uploads/` instead of being dropped. Retry them after the server
is available:

```bash
python -m dev.retry_uploads
python -m dev.retry_uploads --db-server http://EC2_PUBLIC_IP:8000
```

Write to local SQLite only when explicitly requested:

```bash
./run --local-db
```

Windows PowerShell:

```powershell
python run --local-db
```

Run the full pipeline for every `.txt` file in a folder:

```bash
python dev/run_pipeline.py input/unprocessed/
```

Run individual stages:

```bash
python dev/run_ingest_raw_log.py input/unprocessed/example.txt
python dev/run_verify_crc.py output/intermediate/example/step1_timestamp_injected.bin
python dev/run_parse_packets.py output/intermediate/example/step2_valid_packets.bin
python dev/run_build_decodable_payloads.py output/intermediate/example/step3_decode_ready.csv
python dev/run_decode_payloads.py output/intermediate/example
```

All stage entries accept `--name` when you want to override the artifact folder
name. CRC and packet parsing entries also accept `--gse auto|ISAS|Kyutech`.

## Data And Config

- `input/unprocessed/`: raw telemetry logs waiting to be processed.
- `input/processed/`: raw telemetry logs moved here after successful processing.
- `output/intermediate/`: intermediate pipeline artifacts.
- `output/decoded/`: decoded CSV outputs.
- `output/accumulated/`: accumulated HK and ADCS payload database files.
- `config/`: packet structure definitions used during parsing.
- `../decoder_core/decoder/`: shared domain-specific payload decoders used by `pipeline/decode_payloads/`.
- `tests/`: pytest test suite, organized to mirror pipeline responsibilities.

## Development Checks

Collect tests:

```bash
python -m pytest --collect-only -q
```

Run tests:

```bash
python -m pytest -q
```
