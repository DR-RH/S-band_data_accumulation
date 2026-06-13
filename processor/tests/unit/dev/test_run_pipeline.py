from dev import run_pipeline


def test_retry_pending_uploads_if_enabled_uses_server_url(tmp_path, monkeypatch, capsys):
    calls = []

    def fake_retry(queue_dir, server_url):
        calls.append((queue_dir, server_url))
        return {"uploaded": 2, "failed": 1}

    monkeypatch.setattr(run_pipeline, "retry_pending_uploads", fake_retry)

    result = run_pipeline.retry_pending_uploads_if_enabled("http://127.0.0.1:8000", tmp_path)

    assert result == {"uploaded": 2, "failed": 1}
    assert calls == [(tmp_path, "http://127.0.0.1:8000")]
    assert "pending_uploads uploaded=2 failed=1" in capsys.readouterr().out


def test_retry_pending_uploads_if_enabled_skips_without_server_url(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(run_pipeline, "retry_pending_uploads", lambda *args: calls.append(args))

    result = run_pipeline.retry_pending_uploads_if_enabled(None, tmp_path)

    assert result is None
    assert calls == []

