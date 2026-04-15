```mermaid
flowchart TD
    A[read_file] --> B[decode_binary]
    B --> C[map_to_db_schema]
    C --> D[insert_records]
```