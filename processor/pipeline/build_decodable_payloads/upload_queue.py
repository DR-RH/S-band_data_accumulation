from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pipeline.build_decodable_payloads.uploader import upload_payload


def enqueue_upload(queue_dir: Path, endpoint: str, payload: dict, reason: str) -> Path:
    queue_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    packet_id = payload.get("packet_id", "unknown")
    kind = endpoint.strip("/").replace("/", "_")
    path = queue_dir / f"{now.strftime('%Y%m%dT%H%M%S%fZ')}_{kind}_{packet_id}_{uuid4().hex[:8]}.json"
    data = {
        "endpoint": endpoint,
        "payload": payload,
        "reason": reason,
        "created_at": now.isoformat(),
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def pending_upload_files(queue_dir: Path) -> list[Path]:
    if not queue_dir.exists():
        return []
    return sorted(queue_dir.glob("*.json"))


def retry_pending_uploads(queue_dir: Path, server_url: str) -> dict:
    uploaded = 0
    failed = 0

    for path in pending_upload_files(queue_dir):
        data = json.loads(path.read_text(encoding="utf-8"))
        try:
            upload_payload(server_url, data["endpoint"], data["payload"])
        except Exception:
            failed += 1
            continue
        path.unlink()
        uploaded += 1

    return {"uploaded": uploaded, "failed": failed}
