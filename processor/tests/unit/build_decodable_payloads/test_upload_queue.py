import json

from pipeline.build_decodable_payloads import upload_queue


def test_enqueue_upload_writes_pending_json(tmp_path):
    payload = {"packet_id": "011000", "rows": [{"Data": "aa"}]}

    path = upload_queue.enqueue_upload(tmp_path, "/payloads/adcs-hk", payload, "connection failed")

    assert path.exists()
    data = json.loads(path.read_text())
    assert data["endpoint"] == "/payloads/adcs-hk"
    assert data["payload"] == payload
    assert data["reason"] == "connection failed"
    assert data["created_at"]


def test_retry_pending_uploads_deletes_successful_uploads(tmp_path, monkeypatch):
    payload = {"packet_id": "011000", "rows": [{"Data": "aa"}]}
    path = upload_queue.enqueue_upload(tmp_path, "/payloads/adcs-hk", payload, "connection failed")
    calls = []

    monkeypatch.setattr(upload_queue, "upload_payload", lambda server_url, endpoint, upload_payload: calls.append((server_url, endpoint, upload_payload)))

    result = upload_queue.retry_pending_uploads(tmp_path, "http://127.0.0.1:8000")

    assert result == {"uploaded": 1, "failed": 0}
    assert calls == [("http://127.0.0.1:8000", "/payloads/adcs-hk", payload)]
    assert not path.exists()


def test_retry_pending_uploads_keeps_failed_uploads(tmp_path, monkeypatch):
    path = upload_queue.enqueue_upload(tmp_path, "/payloads/adcs-hk", {"packet_id": "011000", "rows": []}, "connection failed")

    def fail(server_url, endpoint, payload):
        raise RuntimeError("still down")

    monkeypatch.setattr(upload_queue, "upload_payload", fail)

    result = upload_queue.retry_pending_uploads(tmp_path, "http://127.0.0.1:8000")

    assert result == {"uploaded": 0, "failed": 1}
    assert path.exists()
