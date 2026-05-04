from __future__ import annotations

import json
from datetime import datetime
from urllib import error, request
from urllib.parse import urljoin

import pandas as pd


def upload_main_hk_payloads(server_url: str, packet_id: str, df: pd.DataFrame) -> int:
    payload = {"packet_id": packet_id, "rows": _rows_for_json(df)}
    response = _post_json(server_url, "/payloads/main-hk", payload)
    return int(response["inserted"])


def upload_adcs_hk_payloads(server_url: str, packet_id: str, df: pd.DataFrame) -> int:
    payload = {"packet_id": packet_id, "rows": _rows_for_json(df)}
    response = _post_json(server_url, "/payloads/adcs-hk", payload)
    return int(response["inserted"])


def _rows_for_json(df: pd.DataFrame) -> list[dict]:
    return [
        {key: _json_value(value) for key, value in row.items()}
        for row in df.to_dict("records")
    ]


def _json_value(value):
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    return value


def _post_json(server_url: str, path: str, payload: dict) -> dict:
    url = urljoin(server_url.rstrip("/") + "/", path.lstrip("/"))
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"DB server rejected upload to {url}: {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Could not connect to DB server at {server_url}: {exc.reason}") from exc
