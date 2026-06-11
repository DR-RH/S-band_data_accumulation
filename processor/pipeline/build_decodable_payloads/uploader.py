from __future__ import annotations

import json
from datetime import datetime
from urllib import error, request
from urllib.parse import urljoin

import pandas as pd


class UploadRejectedError(RuntimeError):
    pass


class UploadConnectionError(RuntimeError):
    pass


def upload_main_hk_payloads(server_url: str, packet_id: str, df: pd.DataFrame, gse: str = "unknown") -> int:
    response = upload_payload(server_url, "/payloads/main-hk", payload_from_df(packet_id, df, gse))
    return int(response["inserted"])


def upload_adcs_hk_payloads(server_url: str, packet_id: str, df: pd.DataFrame, gse: str = "unknown") -> int:
    response = upload_payload(server_url, "/payloads/adcs-hk", payload_from_df(packet_id, df, gse))
    return int(response["inserted"])


def upload_realtime_hk_payloads(server_url: str, packet_id: str, df: pd.DataFrame, gse: str = "unknown") -> int:
    response = upload_payload(server_url, "/payloads/real-time-hk", payload_from_df(packet_id, df, gse))
    return int(response["inserted"])


def payload_from_df(packet_id: str, df: pd.DataFrame, gse: str = "unknown") -> dict:
    payload = {"packet_id": packet_id, "gse": gse, "rows": _rows_for_json(df)}
    return payload


def upload_payload(server_url: str, endpoint: str, payload: dict) -> dict:
    return _post_json(server_url, endpoint, payload)


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
        raise UploadRejectedError(f"DB server rejected upload to {url}: {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise UploadConnectionError(f"Could not connect to DB server at {server_url}: {exc.reason}") from exc
