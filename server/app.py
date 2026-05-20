from __future__ import annotations

import csv
import sys
from io import StringIO
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field

from decoder_catalog import list_decoders
from db import ADCS_HK_TABLE, MAIN_HK_TABLE, ensure_payload_schema, store_adcs_hk_payloads, store_main_hk_payloads
from settings import db_path, decoder_dir
from sqlite_utils import connect, require_table


tags_metadata = [
    {
        "name": "Status",
        "description": "Server health and database table inspection.",
    },
    {
        "name": "Decoders",
        "description": "Decoder version discovery for downloader UI.",
    },
    {
        "name": "Read Payloads",
        "description": "Read accumulated Main HK and ADCS HK payload rows.",
    },
    {
        "name": "Downloads",
        "description": "Download accumulated payload rows as CSV with simple search filters.",
    },
    {
        "name": "Upload Payloads",
        "description": "Upload decodable payload rows produced by the S-band decoder pipeline.",
    },
]

app = FastAPI(
    title="S-band Decoder DB Server",
    summary="Standalone API for accumulating decoded S-band telemetry payloads.",
    description=(
        "Receives payload rows from the decoder pipeline, stores them in SQLite, "
        "and provides simple read endpoints for Main HK and ADCS HK data."
    ),
    version="0.1.0",
    openapi_tags=tags_metadata,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class PayloadUpload(BaseModel):
    packet_id: str = Field(
        examples=["0111010110100011"],
        description="Full packet ID from the parsed telemetry row.",
    )
    gse: str = Field(
        default="unknown",
        examples=["Kyutech"],
        description="Ground station / GSE format used by the processor for this source file.",
    )
    rows: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Rows from a step4 decodable payload CSV. Main HK rows require "
            "`Received time`, `timestamp_obc`, and `Data`; ADCS rows require "
            "`Received time`, `timestamp_adcs`, and `Data`."
        ),
        examples=[
            [
                {
                    "Received time": "2026-05-02T17:41:35+00:00",
                    "timestamp_adcs": "2026-05-02T08:21:26+00:00",
                    "Data": "aabbcc",
                }
            ]
        ],
    )


class HealthResponse(BaseModel):
    status: str
    db_path: str
    db_exists: bool


class TablesResponse(BaseModel):
    tables: list[str]


class DecodersResponse(BaseModel):
    decoders: list[dict[str, str]]


class RowsResponse(BaseModel):
    rows: list[dict[str, Any]]
    limit: int
    offset: int
    total: int


class AdcsRowsResponse(RowsResponse):
    sampling_type: str | None


class UploadResponse(BaseModel):
    inserted: int


MAIN_HK_COLUMNS = [
    "reception_id",
    "unit_id",
    "gse",
    "packet_id",
    "received_time",
    "timestamp_obc",
    "timestamp_obc_unix",
    "data_hex",
]
ADCS_HK_COLUMNS = [
    "reception_id",
    "unit_id",
    "gse",
    "packet_id",
    "sampling_type",
    "received_time",
    "timestamp_adcs",
    "timestamp_adcs_unix",
    "data_hex",
]


def time_options(step_minutes: int = 30) -> str:
    return "\n".join(
        f'<option value="{hour:02d}:{minute:02d}">{hour:02d}:{minute:02d}</option>'
        for hour in range(24)
        for minute in range(0, 60, step_minutes)
    )


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/downloader", response_class=HTMLResponse, include_in_schema=False)
def downloader_window():
    return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>S-band Downloader</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --line: #d7dce2;
      --text: #18212f;
      --muted: #697386;
      --accent: #1463ff;
      --accent-soft: #e7efff;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .shell {
      width: min(1120px, calc(100vw - 32px));
      margin: 32px auto;
    }

    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 18px;
    }

    h1 {
      margin: 0;
      font-size: 24px;
      font-weight: 650;
      letter-spacing: 0;
    }

    .status {
      color: var(--muted);
      font-size: 14px;
    }

    .main-cell {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 12px 30px rgba(24, 33, 47, 0.06);
    }

    .tabs {
      display: flex;
      border-bottom: 1px solid var(--line);
      background: #fbfcfe;
    }

    .tab {
      appearance: none;
      border: 0;
      border-right: 1px solid var(--line);
      background: transparent;
      color: var(--muted);
      min-width: 132px;
      height: 46px;
      padding: 0 18px;
      font: inherit;
      font-weight: 600;
      cursor: pointer;
    }

    .tab[aria-selected="true"] {
      color: var(--accent);
      background: var(--accent-soft);
    }

    .pane {
      display: none;
      padding: 22px;
    }

    .pane.active {
      display: block;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      align-items: end;
    }

    label {
      display: grid;
      gap: 7px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 600;
    }

    .range-column {
      display: grid;
      grid-column: span 2;
      gap: 8px;
    }

    .field-title {
      color: var(--muted);
      font-size: 13px;
      font-weight: 600;
    }

    .range-row {
      display: grid;
      grid-template-columns: 44px minmax(0, 1fr) 92px;
      gap: 8px;
      align-items: center;
    }

    .range-row span {
      color: var(--muted);
      font-size: 13px;
      font-weight: 600;
    }

    .filter-spacer {
      min-height: 62px;
    }

    .checkline {
      display: flex;
      align-items: center;
      gap: 8px;
      min-height: 38px;
      color: var(--text);
      font-size: 14px;
      font-weight: 600;
    }

    .checkline input {
      width: 16px;
      height: 16px;
      margin: 0;
    }

    input,
    select {
      width: 100%;
      height: 38px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 10px;
      color: var(--text);
      background: #ffffff;
      font: inherit;
      font-size: 14px;
    }

    .actions {
      display: flex;
      justify-content: flex-end;
      align-items: end;
      gap: 14px;
      margin-top: 18px;
      padding-top: 18px;
      border-top: 1px solid var(--line);
    }

    .pager {
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 600;
    }

    .page-input {
      width: 64px;
      text-align: right;
    }

    .download-cell {
      display: grid;
      justify-items: end;
      gap: 8px;
    }

    button.action {
      height: 38px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 14px;
      background: #ffffff;
      color: var(--text);
      font: inherit;
      font-weight: 600;
    }

    button.primary {
      border-color: var(--accent);
      background: var(--accent);
      color: #ffffff;
    }

    button:disabled {
      opacity: 0.55;
      cursor: not-allowed;
    }

    .preview {
      margin-top: 18px;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      font-size: 13px;
    }

    th,
    td {
      height: 38px;
      padding: 0 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    th {
      color: var(--muted);
      background: #fbfcfe;
      font-weight: 650;
    }

    @media (max-width: 820px) {
      .shell {
        width: calc(100vw - 20px);
        margin: 16px auto;
      }

      .topbar {
        align-items: flex-start;
        flex-direction: column;
      }

      .tabs {
        overflow-x: auto;
      }

      .grid {
        grid-template-columns: 1fr;
      }

      .range-column {
        grid-column: span 1;
      }

      .range-row {
        grid-template-columns: 1fr;
      }

      .filter-spacer {
        display: none;
      }
    }
  </style>
</head>
<body>
  <main class="shell">
    <div class="topbar">
      <h1>S-band Downloader</h1>
      <div class="status">Search and download controls are layout-only.</div>
    </div>

    <section class="main-cell">
      <div class="tabs" role="tablist" aria-label="Downloader datasets">
        <button class="tab" role="tab" id="tab-main-hk" aria-controls="pane-main-hk" aria-selected="true">Main HK</button>
        <button class="tab" role="tab" id="tab-adcs" aria-controls="pane-adcs" aria-selected="false">ADCS</button>
      </div>

      <section class="pane active" id="pane-main-hk" role="tabpanel" aria-labelledby="tab-main-hk">
        <div class="grid">
          <div class="range-column">
            <span class="field-title">OBC Time Range</span>
            <label class="range-row">
              <span>Start</span>
              <input type="date" value="2026-01-01">
              <input type="time" min="00:00" max="23:59" step="60" value="00:00">
            </label>
            <label class="range-row">
              <span>End</span>
              <input type="date" value="2026-12-31">
              <input type="time" min="00:00" max="23:59" step="60" value="00:00">
            </label>
          </div>
          <div class="range-column">
            <span class="field-title">Received Time Range</span>
            <label class="range-row">
              <span>Start</span>
              <input type="date">
              <input type="time" min="00:00" max="23:59" step="60" value="00:00">
            </label>
            <label class="range-row">
              <span>End</span>
              <input type="date">
              <input type="time" min="00:00" max="23:59" step="60" value="23:59">
            </label>
          </div>
          <label>
            GSE
            <select>
              <option value="">All</option>
              <option value="Kyutech">Kyutech</option>
              <option value="ISAS">ISAS</option>
              <option value="unknown">unknown</option>
            </select>
          </label>
          <label>
            Limit
            <input type="number" value="1000" min="1" max="100000">
          </label>
          <label>
            Order
            <select>
              <option value="desc" selected>Descending</option>
              <option value="asc">Ascending</option>
            </select>
          </label>
          <label>
            Decoder
            <select>
              <option value="latest" selected>latest</option>
              <option value="YYYYMMDD">YYYYMMDD</option>
            </select>
          </label>
          <div class="filter-spacer" aria-hidden="true"></div>
        </div>
        <div class="actions">
          <div class="pager">
            <button class="action" disabled>First</button>
            <button class="action" disabled>Back</button>
            <input class="page-input" type="number" min="1" value="1" disabled>
            <span>/ 0</span>
            <button class="action" disabled>Forward</button>
            <button class="action" disabled>End</button>
          </div>
          <button class="action" disabled>Search</button>
          <div class="download-cell">
            <label class="checkline">
              <input type="checkbox">
              Raw download
            </label>
            <button class="action primary" disabled>Download CSV</button>
          </div>
        </div>
        <div class="preview">
          <table>
            <thead>
              <tr>
                <th>gse</th>
                <th>packet_id</th>
                <th>received_time</th>
                <th>timestamp_obc</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td colspan="4">No preview loaded.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="pane" id="pane-adcs" role="tabpanel" aria-labelledby="tab-adcs">
        <div class="grid">
          <div class="range-column">
            <span class="field-title">ADCS Time Range</span>
            <label class="range-row">
              <span>Start</span>
              <input type="date" value="2026-01-01">
              <input type="time" min="00:00" max="23:59" step="60" value="00:00">
            </label>
            <label class="range-row">
              <span>End</span>
              <input type="date" value="2026-12-31">
              <input type="time" min="00:00" max="23:59" step="60" value="00:00">
            </label>
          </div>
          <div class="range-column">
            <span class="field-title">Received Time Range</span>
            <label class="range-row">
              <span>Start</span>
              <input type="date">
              <input type="time" min="00:00" max="23:59" step="60" value="00:00">
            </label>
            <label class="range-row">
              <span>End</span>
              <input type="date">
              <input type="time" min="00:00" max="23:59" step="60" value="23:59">
            </label>
          </div>
          <label>
            GSE
            <select>
              <option value="">All</option>
              <option value="Kyutech">Kyutech</option>
              <option value="ISAS">ISAS</option>
              <option value="unknown">unknown</option>
            </select>
          </label>
          <label>
            Limit
            <input type="number" value="1000" min="1" max="100000">
          </label>
          <label>
            Order
            <select>
              <option value="desc" selected>Descending</option>
              <option value="asc">Ascending</option>
            </select>
          </label>
          <label>
            Decoder
            <select>
              <option value="latest" selected>latest</option>
              <option value="YYYYMMDD">YYYYMMDD</option>
            </select>
          </label>
          <label>
            Sampling
            <select>
              <option value="">All</option>
              <option value="high">High</option>
              <option value="normal">Normal</option>
            </select>
          </label>
        </div>
        <div class="actions">
          <div class="pager">
            <button class="action" disabled>First</button>
            <button class="action" disabled>Back</button>
            <input class="page-input" type="number" min="1" value="1" disabled>
            <span>/ 0</span>
            <button class="action" disabled>Forward</button>
            <button class="action" disabled>End</button>
          </div>
          <button class="action" disabled>Search</button>
          <div class="download-cell">
            <label class="checkline">
              <input type="checkbox">
              Raw download
            </label>
            <button class="action primary" disabled>Download CSV</button>
          </div>
        </div>
        <div class="preview">
          <table>
            <thead>
              <tr>
                <th>gse</th>
                <th>packet_id</th>
                <th>sampling_type</th>
                <th>received_time</th>
                <th>timestamp_adcs</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td colspan="5">No preview loaded.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </section>
  </main>

  <script>
    const tabs = document.querySelectorAll('[role="tab"]');
    const panes = document.querySelectorAll('[role="tabpanel"]');

    tabs.forEach((tab) => {
      tab.addEventListener('click', () => {
        tabs.forEach((item) => item.setAttribute('aria-selected', 'false'));
        panes.forEach((pane) => pane.classList.remove('active'));
        tab.setAttribute('aria-selected', 'true');
        document.getElementById(tab.getAttribute('aria-controls')).classList.add('active');
      });
    });
  </script>
</body>
</html>
"""


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Status"],
    summary="Check server and DB status",
)
def health():
    path = db_path()
    return {"status": "ok", "db_path": str(path), "db_exists": path.exists()}


@app.get(
    "/tables",
    response_model=TablesResponse,
    tags=["Status"],
    summary="List SQLite tables",
)
def tables():
    with connect() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()

    return {"tables": [row["name"] for row in rows]}


@app.get(
    "/decoders",
    response_model=DecodersResponse,
    tags=["Decoders"],
    summary="List available decoder versions",
)
def decoders():
    return {"decoders": list_decoders(decoder_dir())}


@app.get(
    "/main-hk",
    response_model=RowsResponse,
    tags=["Read Payloads"],
    summary="Read accumulated Main HK payload rows",
)
def main_hk(
    gse: str | None = Query(None, description="Optional GSE filter."),
    packet_id: str | None = Query(None, description="Optional exact packet ID filter."),
    start: str | None = Query(None, description="Optional start timestamp_obc filter, ISO format."),
    end: str | None = Query(None, description="Optional end timestamp_obc filter, ISO format."),
    received_start: str | None = Query(None, description="Optional start received_time filter, ISO format."),
    received_end: str | None = Query(None, description="Optional end received_time filter, ISO format."),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Timestamp sort order."),
    limit: int = Query(100, ge=1, le=1000, description="Maximum rows to return."),
    offset: int = Query(0, ge=0, description="Rows to skip for pagination."),
):
    with connect() as conn:
        require_table(conn, MAIN_HK_TABLE)
        ensure_payload_schema(conn, MAIN_HK_TABLE)
        rows = select_main_hk_preview_rows(conn, gse, packet_id, start, end, received_start, received_end, order, limit, offset)
        total = count_main_hk_preview_rows(conn, gse, packet_id, start, end, received_start, received_end)

    return {"rows": [dict(row) for row in rows], "limit": limit, "offset": offset, "total": total}


@app.get(
    "/adcs-hk",
    response_model=AdcsRowsResponse,
    tags=["Read Payloads"],
    summary="Read accumulated ADCS HK payload rows",
)
def adcs_hk(
    gse: str | None = Query(None, description="Optional GSE filter."),
    packet_id: str | None = Query(None, description="Optional exact packet ID filter."),
    sampling_type: str | None = Query(
        None,
        pattern="^(normal|high)$",
        description="Optional filter for ADCS sampling type.",
    ),
    start: str | None = Query(None, description="Optional start timestamp_adcs filter, ISO format."),
    end: str | None = Query(None, description="Optional end timestamp_adcs filter, ISO format."),
    received_start: str | None = Query(None, description="Optional start received_time filter, ISO format."),
    received_end: str | None = Query(None, description="Optional end received_time filter, ISO format."),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Timestamp sort order."),
    limit: int = Query(100, ge=1, le=1000, description="Maximum rows to return."),
    offset: int = Query(0, ge=0, description="Rows to skip for pagination."),
):
    with connect() as conn:
        require_table(conn, ADCS_HK_TABLE)
        ensure_payload_schema(conn, ADCS_HK_TABLE)
        rows = select_adcs_hk_preview_rows(conn, gse, packet_id, sampling_type, start, end, received_start, received_end, order, limit, offset)
        total = count_adcs_hk_preview_rows(conn, gse, packet_id, sampling_type, start, end, received_start, received_end)

    return {
        "rows": [dict(row) for row in rows],
        "sampling_type": sampling_type,
        "limit": limit,
        "offset": offset,
        "total": total,
    }


@app.get(
    "/downloads/main-hk.csv",
    tags=["Downloads"],
    summary="Download Main HK payload rows as CSV",
)
def download_main_hk_csv(
    gse: str | None = Query(None, description="Optional GSE filter."),
    packet_id: str | None = Query(None, description="Optional exact packet ID filter."),
    start: str | None = Query(None, description="Optional start timestamp_obc filter, ISO format."),
    end: str | None = Query(None, description="Optional end timestamp_obc filter, ISO format."),
    received_start: str | None = Query(None, description="Optional start received_time filter, ISO format."),
    received_end: str | None = Query(None, description="Optional end received_time filter, ISO format."),
    raw: bool = Query(False, description="Download raw payload rows instead of decoded rows."),
    decoder: str = Query("latest", description="Decoder version set for decoded download."),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Timestamp sort order."),
    limit: int = Query(10000, ge=1, le=100000, description="Maximum rows to download."),
    offset: int = Query(0, ge=0, description="Rows to skip for pagination."),
):
    with connect() as conn:
        require_table(conn, MAIN_HK_TABLE)
        ensure_payload_schema(conn, MAIN_HK_TABLE)
        rows = select_main_hk_rows(conn, gse, packet_id, start, end, received_start, received_end, order, limit, offset)

    if raw:
        return csv_response("raw_main_hk_payloads.csv", MAIN_HK_COLUMNS, rows)
    return decoded_csv_response(
        decoded_filename("main_hk", decoder),
        decode_main_hk_rows(rows, decoder),
    )


@app.get(
    "/downloads/adcs-hk.csv",
    tags=["Downloads"],
    summary="Download ADCS HK payload rows as CSV",
)
def download_adcs_hk_csv(
    gse: str | None = Query(None, description="Optional GSE filter."),
    packet_id: str | None = Query(None, description="Optional exact packet ID filter."),
    sampling_type: str | None = Query(
        None,
        pattern="^(normal|high)$",
        description="Optional filter for ADCS sampling type.",
    ),
    start: str | None = Query(None, description="Optional start timestamp_adcs filter, ISO format."),
    end: str | None = Query(None, description="Optional end timestamp_adcs filter, ISO format."),
    received_start: str | None = Query(None, description="Optional start received_time filter, ISO format."),
    received_end: str | None = Query(None, description="Optional end received_time filter, ISO format."),
    raw: bool = Query(False, description="Download raw payload rows instead of decoded rows."),
    decoder: str = Query("latest", description="Decoder version set for decoded download."),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Timestamp sort order."),
    limit: int = Query(10000, ge=1, le=100000, description="Maximum rows to download."),
    offset: int = Query(0, ge=0, description="Rows to skip for pagination."),
):
    with connect() as conn:
        require_table(conn, ADCS_HK_TABLE)
        ensure_payload_schema(conn, ADCS_HK_TABLE)
        rows = select_adcs_hk_rows(conn, gse, packet_id, sampling_type, start, end, received_start, received_end, order, limit, offset)

    if raw:
        return csv_response("raw_adcs_hk_payloads.csv", ADCS_HK_COLUMNS, rows)
    return decoded_csv_response(
        decoded_filename("adcs_hk", decoder),
        decode_adcs_hk_rows(rows, decoder),
    )


@app.post(
    "/payloads/main-hk",
    response_model=UploadResponse,
    tags=["Upload Payloads"],
    summary="Upload Main HK payload rows",
)
def upload_main_hk(payload: PayloadUpload):
    inserted = store_main_hk_payloads(db_path(), payload.packet_id, pd.DataFrame(payload.rows), payload.gse)
    return {"inserted": inserted}


@app.post(
    "/payloads/adcs-hk",
    response_model=UploadResponse,
    tags=["Upload Payloads"],
    summary="Upload ADCS HK payload rows",
)
def upload_adcs_hk(payload: PayloadUpload):
    inserted = store_adcs_hk_payloads(db_path(), payload.packet_id, pd.DataFrame(payload.rows), payload.gse)
    return {"inserted": inserted}


def select_main_hk_rows(
    conn,
    gse: str | None,
    packet_id: str | None,
    start: str | None,
    end: str | None,
    received_start: str | None,
    received_end: str | None,
    order: str,
    limit: int,
    offset: int,
):
    where, params = build_filters(
        gse=gse,
        packet_id=packet_id,
        start=start,
        end=end,
        received_start=received_start,
        received_end=received_end,
        timestamp_column="timestamp_obc",
    )
    direction = sql_order_direction(order)
    params.extend([limit, offset])
    return conn.execute(
        f"""
        SELECT {", ".join(MAIN_HK_COLUMNS)}
        FROM {MAIN_HK_TABLE}
        {where}
        ORDER BY timestamp_obc_unix {direction}, received_time {direction}
        LIMIT ? OFFSET ?
        """,
        params,
    ).fetchall()


def select_main_hk_preview_rows(
    conn,
    gse: str | None,
    packet_id: str | None,
    start: str | None,
    end: str | None,
    received_start: str | None,
    received_end: str | None,
    order: str,
    limit: int,
    offset: int,
):
    where, params = build_filters(
        gse=gse,
        packet_id=packet_id,
        start=start,
        end=end,
        received_start=received_start,
        received_end=received_end,
        timestamp_column="timestamp_obc",
    )
    direction = sql_order_direction(order)
    params.extend([limit, offset])
    return conn.execute(
        f"""
        SELECT
            unit_id,
            GROUP_CONCAT(DISTINCT gse) AS gse,
            MIN(packet_id) AS packet_id,
            MIN(received_time) AS received_time,
            MIN(timestamp_obc) AS timestamp_obc,
            MIN(timestamp_obc_unix) AS sort_timestamp
        FROM {MAIN_HK_TABLE}
        {where}
        GROUP BY unit_id
        ORDER BY sort_timestamp {direction}
        LIMIT ? OFFSET ?
        """,
        params,
    ).fetchall()


def count_main_hk_preview_rows(
    conn,
    gse: str | None,
    packet_id: str | None,
    start: str | None,
    end: str | None,
    received_start: str | None,
    received_end: str | None,
) -> int:
    where, params = build_filters(
        gse=gse,
        packet_id=packet_id,
        start=start,
        end=end,
        received_start=received_start,
        received_end=received_end,
        timestamp_column="timestamp_obc",
    )
    return conn.execute(
        f"""
        SELECT COUNT(*) FROM (
            SELECT unit_id
            FROM {MAIN_HK_TABLE}
            {where}
            GROUP BY unit_id
        )
        """,
        params,
    ).fetchone()[0]


def select_adcs_hk_rows(
    conn,
    gse: str | None,
    packet_id: str | None,
    sampling_type: str | None,
    start: str | None,
    end: str | None,
    received_start: str | None,
    received_end: str | None,
    order: str,
    limit: int,
    offset: int,
):
    where, params = build_filters(
        gse=gse,
        packet_id=packet_id,
        sampling_type=sampling_type,
        start=start,
        end=end,
        received_start=received_start,
        received_end=received_end,
        timestamp_column="timestamp_adcs",
    )
    direction = sql_order_direction(order)
    params.extend([limit, offset])
    return conn.execute(
        f"""
        SELECT {", ".join(ADCS_HK_COLUMNS)}
        FROM {ADCS_HK_TABLE}
        {where}
        ORDER BY timestamp_adcs_unix {direction}, received_time {direction}
        LIMIT ? OFFSET ?
        """,
        params,
    ).fetchall()


def select_adcs_hk_preview_rows(
    conn,
    gse: str | None,
    packet_id: str | None,
    sampling_type: str | None,
    start: str | None,
    end: str | None,
    received_start: str | None,
    received_end: str | None,
    order: str,
    limit: int,
    offset: int,
):
    where, params = build_filters(
        gse=gse,
        packet_id=packet_id,
        sampling_type=sampling_type,
        start=start,
        end=end,
        received_start=received_start,
        received_end=received_end,
        timestamp_column="timestamp_adcs",
    )
    direction = sql_order_direction(order)
    params.extend([limit, offset])
    return conn.execute(
        f"""
        SELECT
            unit_id,
            GROUP_CONCAT(DISTINCT gse) AS gse,
            MIN(packet_id) AS packet_id,
            MIN(sampling_type) AS sampling_type,
            MIN(received_time) AS received_time,
            MIN(timestamp_adcs) AS timestamp_adcs,
            MIN(timestamp_adcs_unix) AS sort_timestamp
        FROM {ADCS_HK_TABLE}
        {where}
        GROUP BY unit_id
        ORDER BY sort_timestamp {direction}
        LIMIT ? OFFSET ?
        """,
        params,
    ).fetchall()


def count_adcs_hk_preview_rows(
    conn,
    gse: str | None,
    packet_id: str | None,
    sampling_type: str | None,
    start: str | None,
    end: str | None,
    received_start: str | None,
    received_end: str | None,
) -> int:
    where, params = build_filters(
        gse=gse,
        packet_id=packet_id,
        sampling_type=sampling_type,
        start=start,
        end=end,
        received_start=received_start,
        received_end=received_end,
        timestamp_column="timestamp_adcs",
    )
    return conn.execute(
        f"""
        SELECT COUNT(*) FROM (
            SELECT unit_id
            FROM {ADCS_HK_TABLE}
            {where}
            GROUP BY unit_id
        )
        """,
        params,
    ).fetchone()[0]


def build_filters(
    *,
    gse: str | None = None,
    packet_id: str | None = None,
    sampling_type: str | None = None,
    start: str | None = None,
    end: str | None = None,
    received_start: str | None = None,
    received_end: str | None = None,
    timestamp_column: str,
):
    clauses = []
    params: list[object] = []

    if gse is not None:
        clauses.append("gse = ?")
        params.append(gse)
    if packet_id is not None:
        clauses.append("packet_id = ?")
        params.append(packet_id)
    if sampling_type is not None:
        clauses.append("sampling_type = ?")
        params.append(sampling_type)
    if start is not None:
        clauses.append(f"{timestamp_column} >= ?")
        params.append(start)
    if end is not None:
        clauses.append(f"{timestamp_column} <= ?")
        params.append(end)
    if received_start is not None:
        clauses.append("received_time >= ?")
        params.append(received_start)
    if received_end is not None:
        clauses.append("received_time <= ?")
        params.append(received_end)

    if not clauses:
        return "", params
    return "WHERE " + " AND ".join(clauses), params


def sql_order_direction(order: str) -> str:
    return "ASC" if order == "asc" else "DESC"


def csv_response(filename: str, columns: list[str], rows):
    stream = StringIO()
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow({column: row[column] for column in columns})

    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def decoded_csv_response(filename: str, decoded_rows: list[dict]):
    df = pd.DataFrame(decoded_rows)
    stream = StringIO()
    df.to_csv(stream, index=False)
    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def decoded_filename(dataset: str, decoder: str) -> str:
    return f"decoded_{dataset}_{safe_filename_part(decoder)}.csv"


def safe_filename_part(value: str) -> str:
    return "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in value).strip("_") or "decoder"


def decode_main_hk_rows(rows, decoder: str) -> list[dict]:
    require_latest_decoder(decoder)
    from decoder import decoder_main_HK

    return decoder_main_HK.decode(join_data_hex(rows))


def decode_adcs_hk_rows(rows, decoder: str) -> list[dict]:
    require_latest_decoder(decoder)
    from decoder import decoder_adcs_HK

    return decoder_adcs_HK.decode(join_data_hex(rows))


def join_data_hex(rows) -> bytes:
    return bytes.fromhex("".join(row["data_hex"] for row in rows))


def require_latest_decoder(decoder: str) -> None:
    if decoder == "latest":
        ensure_decoder_import_path()
        return
    raise HTTPException(
        status_code=501,
        detail=f"Decoded download for decoder version '{decoder}' is not implemented yet.",
    )


def ensure_decoder_import_path() -> None:
    root = decoder_dir().parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
