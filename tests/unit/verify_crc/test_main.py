from pathlib import Path

from pipeline.verify_crc import main as verify_main


def test_verify_crc_returns_valid_binary(monkeypatch):
    expected = b"valid packets"

    def fake_process_data(binary, gse_name):
        assert binary == b"raw packets"
        assert gse_name == "Kyutech"
        return expected

    monkeypatch.setattr(verify_main.verify_packets, "process_data", fake_process_data)

    result = verify_main.verify_crc(b"raw packets", "Kyutech")

    assert result == expected


def test_verify_crc_writes_output_when_save_filename_is_given(tmp_path, monkeypatch):
    expected = b"valid packets"

    monkeypatch.setattr(
        verify_main.verify_packets,
        "process_data",
        lambda binary, gse_name: expected,
    )

    out_dir = tmp_path / "sample"
    result = verify_main.verify_crc(b"raw packets", "ISAS", out_dir)

    out_path = out_dir / "step2_valid_packets.bin"
    assert result == expected
    assert out_path.read_bytes() == expected
