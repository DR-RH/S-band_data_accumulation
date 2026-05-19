
def run(path):
    raw = read_file(path)
    records = decode_binary(raw)
    rows = map_to_db_schema(records)
    insert_records(rows)