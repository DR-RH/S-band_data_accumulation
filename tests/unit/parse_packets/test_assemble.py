from pipeline.parse_packets import assemble


def test_load_structure_file_uses_kyutech_only_for_exact_match():
    kyutech = assemble.load_structure_file("Kyutech")
    unknown = assemble.load_structure_file("unknown")

    assert kyutech[2]["Name"] == "Frame counter, higher bits"
    assert unknown[2]["Name"] == "Demodulator symbol"


def test_build_dataframe_uses_packet_size_and_parser(monkeypatch):
    calls = []

    monkeypatch.setattr(assemble, "get_packet_size", lambda gse: 3)
    monkeypatch.setattr(assemble, "load_structure_file", lambda gse: [{"schema": gse}])

    def fake_parse_packet(packet, bit_map, index):
        calls.append((packet, bit_map, index))
        return {"index": index, "Data": packet}

    monkeypatch.setattr(assemble, "parse_packet", fake_parse_packet)

    df = assemble.build_dataframe(b"AAABBB", "ISAS")

    assert df["Data"].tolist() == [b"AAA", b"BBB"]
    assert calls == [
        (b"AAA", [{"schema": "ISAS"}], 0),
        (b"BBB", [{"schema": "ISAS"}], 1),
    ]
