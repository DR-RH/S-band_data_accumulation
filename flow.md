# Pipeline Flow

```mermaid
flowchart TD
    A["Raw telemetry log (.txt)"] --> B["ingest_raw_log"]
    B --> C["verify_crc"]
    C --> D["parse_packets"]
    D --> E["build_decodable_payloads"]
    E --> F["decode_payloads"]
    F --> G["Decoded CSV outputs"]
```

The folder names describe each stage's responsibility, not its fixed position
in the pipeline. If the execution order changes, update the orchestration in
`app/main.py` and this flow document rather than renaming packages again.
