from datetime import datetime, timezone

import pandas as pd

from pipeline.build_decodable_payloads import uploader


def test_rows_for_json_serializes_timestamps():
    df = pd.DataFrame(
        [
            {
                "Received time": pd.Timestamp("2026-05-02T17:39:47Z"),
                "timestamp_adcs": datetime(2026, 5, 2, 7, 36, 55, tzinfo=timezone.utc),
                "Data": "aabb",
            }
        ]
    )

    assert uploader._rows_for_json(df) == [
        {
            "Received time": "2026-05-02T17:39:47+00:00",
            "timestamp_adcs": "2026-05-02T07:36:55+00:00",
            "Data": "aabb",
        }
    ]


def test_upload_main_hk_payloads_posts_expected_payload(monkeypatch):
    posted = []
    df = pd.DataFrame([{"Received time": "received", "timestamp_obc": "obc", "Data": "aa"}])

    def fake_post_json(server_url, path, payload):
        posted.append((server_url, path, payload))
        return {"inserted": 3}

    monkeypatch.setattr(uploader, "_post_json", fake_post_json)

    inserted = uploader.upload_main_hk_payloads("http://127.0.0.1:8000", "110000", df)

    assert inserted == 3
    assert posted == [
        (
            "http://127.0.0.1:8000",
            "/payloads/main-hk",
            {
                "packet_id": "110000",
                "rows": [{"Received time": "received", "timestamp_obc": "obc", "Data": "aa"}],
            },
        )
    ]


def test_upload_adcs_hk_payloads_posts_expected_payload(monkeypatch):
    posted = []
    df = pd.DataFrame([{"Received time": "received", "timestamp_adcs": "adcs", "Data": "aa"}])

    def fake_post_json(server_url, path, payload):
        posted.append((server_url, path, payload))
        return {"inserted": 4}

    monkeypatch.setattr(uploader, "_post_json", fake_post_json)

    inserted = uploader.upload_adcs_hk_payloads("http://127.0.0.1:8000", "011000", df)

    assert inserted == 4
    assert posted == [
        (
            "http://127.0.0.1:8000",
            "/payloads/adcs-hk",
            {
                "packet_id": "011000",
                "rows": [{"Received time": "received", "timestamp_adcs": "adcs", "Data": "aa"}],
            },
        )
    ]
