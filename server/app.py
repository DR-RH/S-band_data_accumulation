from __future__ import annotations

import csv
import json
import math
import sys
from io import StringIO
from typing import Annotated, Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field

from decoder_catalog import list_decoders
from db import (
    ADCS_HK_TABLE,
    MAIN_HK_TABLE,
    REALTIME_HK_TABLE,
    ensure_payload_schema,
    store_adcs_hk_payloads,
    store_main_hk_payloads,
    store_realtime_hk_payloads,
)
from raw_prefilters import (
    RawPrefilter,
    build_main_hk_raw_prefilter,
    can_decode_main_hk_single_columns,
    decode_main_hk_single_rows,
)
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
        "description": "Read accumulated Main HK, Real Time HK, and ADCS HK payload rows.",
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
        "and provides simple read endpoints for Main HK, Real Time HK, and ADCS HK data."
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


class GraphColumnsResponse(BaseModel):
    x: str
    y1: list[str]
    y2: list[str]


class GraphRowsResponse(RowsResponse):
    columns: GraphColumnsResponse
    decode_mode: str


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
REALTIME_HK_COLUMNS = [
    "reception_id",
    "unit_id",
    "gse",
    "packet_id",
    "received_time",
    "timestamp_obc",
    "timestamp_obc_unix",
    "data_hex",
]
GSE_REPORT_STATION_ORDER = ["ISAS", "Kyutech", "unknown"]
GSE_REPORT_FIELDS = ["packet_id", "received_time"]
DECODE_FILTER_SCAN_CHUNK_SIZE = 500
MAIN_HK_GRAPH_BASE_COLUMNS = {
    "unit_id",
    "gse",
    "packet_id",
    "received_time",
    "timestamp_obc",
    "sort_timestamp",
}


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
    value_filters: str | None = Query(None, description="JSON encoded decoded value filters."),
    value_columns: str | None = Query(None, description="JSON encoded decoded value columns to include."),
    decoder: str = Query("latest", description="Decoder version set for decoded value filters."),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Timestamp sort order."),
    exact_total: bool = Query(True, description="Scan all decoded matches to return an exact total."),
    limit: int = Query(100, ge=1, le=100000, description="Maximum rows to return."),
    offset: int = Query(0, ge=0, description="Rows to skip for pagination."),
):
    decoded_filters = parse_value_filters(value_filters)
    requested_columns = parse_value_columns(value_columns)
    with connect() as conn:
        require_table(conn, MAIN_HK_TABLE)
        ensure_payload_schema(conn, MAIN_HK_TABLE)
        if decoded_filters:
            raw_prefilter = build_main_hk_raw_prefilter(decoded_filters)
            if raw_prefilter.supported_count == len(decoded_filters):
                rows, total = select_decoded_page_rows(
                    conn=conn,
                    selector=select_main_hk_decode_candidate_rows,
                    selector_args=(gse, packet_id, start, end, received_start, received_end, order),
                    count=count_main_hk_preview_rows,
                    count_args=(gse, packet_id, start, end, received_start, received_end),
                    decoder=decoder,
                    decode_rows=decode_main_hk_rows,
                    value_columns=unique_elements(unique_filter_elements(decoded_filters), requested_columns),
                    limit=limit,
                    offset=offset,
                    raw_prefilter=raw_prefilter,
                    value_filters=decoded_filters,
                )
            else:
                rows, total = select_decoded_preview_rows(
                    conn=conn,
                    selector=select_main_hk_decode_candidate_rows,
                    selector_args=(gse, packet_id, start, end, received_start, received_end, order),
                    decoder=decoder,
                    decode_rows=decode_main_hk_rows,
                    value_filters=decoded_filters,
                    value_columns=requested_columns,
                    exact_total=exact_total,
                    limit=limit,
                    offset=offset,
                    raw_prefilter=raw_prefilter,
                )
        elif requested_columns:
            rows, total = select_decoded_page_rows(
                conn=conn,
                selector=select_main_hk_decode_candidate_rows,
                selector_args=(gse, packet_id, start, end, received_start, received_end, order),
                count=count_main_hk_preview_rows,
                count_args=(gse, packet_id, start, end, received_start, received_end),
                decoder=decoder,
                decode_rows=decode_main_hk_rows,
                value_columns=requested_columns,
                limit=limit,
                offset=offset,
            )
        else:
            rows = [dict(row) for row in select_main_hk_preview_rows(conn, gse, packet_id, start, end, received_start, received_end, order, limit, offset)]
            total = count_main_hk_preview_rows(conn, gse, packet_id, start, end, received_start, received_end)

    return {"rows": rows, "limit": limit, "offset": offset, "total": total}


@app.get(
    "/graphs/main-hk",
    response_model=GraphRowsResponse,
    tags=["Read Payloads"],
    summary="Read lightweight Main HK graph rows",
)
def graph_main_hk(
    gse: Annotated[str | None, Query(description="Optional GSE filter.")] = None,
    packet_id: Annotated[str | None, Query(description="Optional exact packet ID filter.")] = None,
    start: Annotated[str | None, Query(description="Optional start timestamp_obc filter, ISO format.")] = None,
    end: Annotated[str | None, Query(description="Optional end timestamp_obc filter, ISO format.")] = None,
    received_start: Annotated[str | None, Query(description="Optional start received_time filter, ISO format.")] = None,
    received_end: Annotated[str | None, Query(description="Optional end received_time filter, ISO format.")] = None,
    value_filters: Annotated[str | None, Query(description="JSON encoded decoded value filters.")] = None,
    decoder: Annotated[str, Query(description="Decoder version set for decoded value filters.")] = "latest",
    order: Annotated[str, Query(pattern="^(asc|desc)$", description="Timestamp sort order.")] = "desc",
    limit: Annotated[int, Query(ge=1, le=100000, description="Maximum rows to return.")] = 100,
    offset: Annotated[int, Query(ge=0, description="Rows to skip for pagination.")] = 0,
    x: Annotated[str, Query(description="Graph x-axis column name.")] = "timestamp_obc",
    y1: Annotated[str | None, Query(description="JSON encoded y1 column names.")] = None,
    y2: Annotated[str | None, Query(description="JSON encoded y2 column names.")] = None,
):
    x_column = parse_graph_x_column(x)
    y1_columns = parse_graph_columns(y1, "y1")
    y2_columns = parse_graph_columns(y2, "y2")
    graph_columns = {"x": x_column, "y1": y1_columns, "y2": y2_columns}
    requested_columns = unique_elements([x_column], y1_columns, y2_columns)
    decoded_filters = parse_value_filters(value_filters)
    needs_decoding = bool(decoded_filters) or any(
        column not in MAIN_HK_GRAPH_BASE_COLUMNS for column in requested_columns
    )
    single_decode_columns = unique_elements(unique_filter_elements(decoded_filters), requested_columns)
    decode_mode = "base"

    with connect() as conn:
        require_table(conn, MAIN_HK_TABLE)
        ensure_payload_schema(conn, MAIN_HK_TABLE)
        if needs_decoding and can_decode_main_hk_single_columns(single_decode_columns):
            rows, total = select_main_hk_single_graph_rows(
                conn=conn,
                selector_args=(gse, packet_id, start, end, received_start, received_end, order),
                count_args=(gse, packet_id, start, end, received_start, received_end),
                decoder=decoder,
                value_filters=decoded_filters,
                value_columns=single_decode_columns,
                limit=limit,
                offset=offset,
            )
            decode_mode = "single"
        elif decoded_filters:
            raw_prefilter = build_main_hk_raw_prefilter(decoded_filters)
            if raw_prefilter.supported_count == len(decoded_filters):
                rows, total = select_decoded_page_rows(
                    conn=conn,
                    selector=select_main_hk_decode_candidate_rows,
                    selector_args=(gse, packet_id, start, end, received_start, received_end, order),
                    count=count_main_hk_preview_rows,
                    count_args=(gse, packet_id, start, end, received_start, received_end),
                    decoder=decoder,
                    decode_rows=decode_main_hk_rows,
                    value_columns=unique_elements(unique_filter_elements(decoded_filters), requested_columns),
                    limit=limit,
                    offset=offset,
                    raw_prefilter=raw_prefilter,
                    value_filters=decoded_filters,
                )
            else:
                rows, total = select_decoded_preview_rows(
                    conn=conn,
                    selector=select_main_hk_decode_candidate_rows,
                    selector_args=(gse, packet_id, start, end, received_start, received_end, order),
                    decoder=decoder,
                    decode_rows=decode_main_hk_rows,
                    value_filters=decoded_filters,
                    value_columns=requested_columns,
                    exact_total=False,
                    limit=limit,
                    offset=offset,
                    raw_prefilter=raw_prefilter,
                )
            decode_mode = "full"
        elif needs_decoding:
            rows, total = select_decoded_page_rows(
                conn=conn,
                selector=select_main_hk_decode_candidate_rows,
                selector_args=(gse, packet_id, start, end, received_start, received_end, order),
                count=count_main_hk_preview_rows,
                count_args=(gse, packet_id, start, end, received_start, received_end),
                decoder=decoder,
                decode_rows=decode_main_hk_rows,
                value_columns=requested_columns,
                limit=limit,
                offset=offset,
            )
            decode_mode = "full"
        else:
            rows = [
                dict(row)
                for row in select_main_hk_preview_rows(
                    conn,
                    gse,
                    packet_id,
                    start,
                    end,
                    received_start,
                    received_end,
                    order,
                    limit,
                    offset,
                )
            ]
            total = count_main_hk_preview_rows(conn, gse, packet_id, start, end, received_start, received_end)

    return {
        "rows": project_graph_rows(rows, requested_columns),
        "limit": limit,
        "offset": offset,
        "total": total,
        "columns": graph_columns,
        "decode_mode": decode_mode,
    }


@app.get(
    "/real-time-hk",
    response_model=RowsResponse,
    tags=["Read Payloads"],
    summary="Read accumulated Real Time HK payload rows",
)
def real_time_hk(
    gse: str | None = Query(None, description="Optional GSE filter."),
    packet_id: str | None = Query(None, description="Optional exact packet ID filter."),
    start: str | None = Query(None, description="Optional start timestamp_obc filter, ISO format."),
    end: str | None = Query(None, description="Optional end timestamp_obc filter, ISO format."),
    received_start: str | None = Query(None, description="Optional start received_time filter, ISO format."),
    received_end: str | None = Query(None, description="Optional end received_time filter, ISO format."),
    value_filters: str | None = Query(None, description="JSON encoded decoded value filters."),
    value_columns: str | None = Query(None, description="JSON encoded decoded value columns to include."),
    decoder: str = Query("latest", description="Decoder version set for decoded value filters."),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Timestamp sort order."),
    exact_total: bool = Query(True, description="Scan all decoded matches to return an exact total."),
    limit: int = Query(100, ge=1, le=100000, description="Maximum rows to return."),
    offset: int = Query(0, ge=0, description="Rows to skip for pagination."),
):
    decoded_filters = parse_value_filters(value_filters)
    requested_columns = parse_value_columns(value_columns)
    with connect() as conn:
        ensure_payload_schema(conn, REALTIME_HK_TABLE)
        require_table(conn, REALTIME_HK_TABLE)
        if decoded_filters:
            rows, total = select_decoded_preview_rows(
                conn=conn,
                selector=select_realtime_hk_decode_candidate_rows,
                selector_args=(gse, packet_id, start, end, received_start, received_end, order),
                decoder=decoder,
                decode_rows=decode_realtime_hk_rows,
                value_filters=decoded_filters,
                value_columns=requested_columns,
                exact_total=exact_total,
                limit=limit,
                offset=offset,
            )
        elif requested_columns:
            rows, total = select_decoded_page_rows(
                conn=conn,
                selector=select_realtime_hk_decode_candidate_rows,
                selector_args=(gse, packet_id, start, end, received_start, received_end, order),
                count=count_realtime_hk_preview_rows,
                count_args=(gse, packet_id, start, end, received_start, received_end),
                decoder=decoder,
                decode_rows=decode_realtime_hk_rows,
                value_columns=requested_columns,
                limit=limit,
                offset=offset,
            )
        else:
            rows = [dict(row) for row in select_realtime_hk_preview_rows(conn, gse, packet_id, start, end, received_start, received_end, order, limit, offset)]
            total = count_realtime_hk_preview_rows(conn, gse, packet_id, start, end, received_start, received_end)

    return {"rows": rows, "limit": limit, "offset": offset, "total": total}


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
    value_filters: str | None = Query(None, description="JSON encoded decoded value filters."),
    value_columns: str | None = Query(None, description="JSON encoded decoded value columns to include."),
    decoder: str = Query("latest", description="Decoder version set for decoded value filters."),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Timestamp sort order."),
    exact_total: bool = Query(True, description="Scan all decoded matches to return an exact total."),
    limit: int = Query(100, ge=1, le=100000, description="Maximum rows to return."),
    offset: int = Query(0, ge=0, description="Rows to skip for pagination."),
):
    decoded_filters = parse_value_filters(value_filters)
    requested_columns = parse_value_columns(value_columns)
    with connect() as conn:
        require_table(conn, ADCS_HK_TABLE)
        ensure_payload_schema(conn, ADCS_HK_TABLE)
        if decoded_filters:
            rows, total = select_decoded_preview_rows(
                conn=conn,
                selector=select_adcs_hk_decode_candidate_rows,
                selector_args=(gse, packet_id, sampling_type, start, end, received_start, received_end, order),
                decoder=decoder,
                decode_rows=decode_adcs_hk_rows,
                value_filters=decoded_filters,
                value_columns=requested_columns,
                exact_total=exact_total,
                limit=limit,
                offset=offset,
            )
        elif requested_columns:
            rows, total = select_decoded_page_rows(
                conn=conn,
                selector=select_adcs_hk_decode_candidate_rows,
                selector_args=(gse, packet_id, sampling_type, start, end, received_start, received_end, order),
                count=count_adcs_hk_preview_rows,
                count_args=(gse, packet_id, sampling_type, start, end, received_start, received_end),
                decoder=decoder,
                decode_rows=decode_adcs_hk_rows,
                value_columns=requested_columns,
                limit=limit,
                offset=offset,
            )
        else:
            rows = [dict(row) for row in select_adcs_hk_preview_rows(conn, gse, packet_id, sampling_type, start, end, received_start, received_end, order, limit, offset)]
            total = count_adcs_hk_preview_rows(conn, gse, packet_id, sampling_type, start, end, received_start, received_end)

    return {
        "rows": rows,
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
    gse_report: bool = Query(False, description="Download compact GSE reception report rows."),
    decoder: str = Query("latest", description="Decoder version set for decoded download."),
    value_filters: str | None = Query(None, description="JSON encoded decoded value filters."),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Timestamp sort order."),
    limit: int = Query(10000, ge=1, le=100000, description="Maximum rows to download."),
    offset: int = Query(0, ge=0, description="Rows to skip for pagination."),
):
    decoded_filters = parse_value_filters(value_filters)
    decoded_rows = None
    with connect() as conn:
        require_table(conn, MAIN_HK_TABLE)
        ensure_payload_schema(conn, MAIN_HK_TABLE)
        if decoded_filters:
            raw_prefilter = build_main_hk_raw_prefilter(decoded_filters)
            if raw_prefilter.supported_count == len(decoded_filters):
                rows = select_main_hk_rows(
                    conn,
                    gse,
                    packet_id,
                    start,
                    end,
                    received_start,
                    received_end,
                    order,
                    limit,
                    offset,
                    raw_prefilter,
                )
                decoded_rows = decode_main_hk_rows(rows, decoder)
                filtered_pairs = [
                    (row, decoded_row)
                    for row, decoded_row in zip(rows, decoded_rows)
                    if decoded_row_matches_filters(decoded_row, decoded_filters)
                ]
                rows = [row for row, _ in filtered_pairs]
                decoded_rows = [decoded_row for _, decoded_row in filtered_pairs]
            else:
                rows, decoded_rows = select_decoded_download_rows(
                    conn=conn,
                    selector=select_main_hk_rows,
                    selector_args=(gse, packet_id, start, end, received_start, received_end, order),
                    decoder=decoder,
                    decode_rows=decode_main_hk_rows,
                    value_filters=decoded_filters,
                    limit=limit,
                    offset=offset,
                    raw_prefilter=raw_prefilter,
                )
        else:
            rows = select_main_hk_rows(conn, gse, packet_id, start, end, received_start, received_end, order, limit, offset)

    if gse_report:
        return gse_report_csv_response("main_hk", gse, rows)
    if raw:
        return csv_response("raw_main_hk_payloads.csv", MAIN_HK_COLUMNS, rows)
    return decoded_csv_response(
        decoded_filename("main_hk", decoder),
        decoded_rows if decoded_rows is not None else decode_main_hk_rows(rows, decoder),
    )


@app.get(
    "/downloads/real-time-hk.csv",
    tags=["Downloads"],
    summary="Download Real Time HK payload rows as CSV",
)
def download_real_time_hk_csv(
    gse: str | None = Query(None, description="Optional GSE filter."),
    packet_id: str | None = Query(None, description="Optional exact packet ID filter."),
    start: str | None = Query(None, description="Optional start timestamp_obc filter, ISO format."),
    end: str | None = Query(None, description="Optional end timestamp_obc filter, ISO format."),
    received_start: str | None = Query(None, description="Optional start received_time filter, ISO format."),
    received_end: str | None = Query(None, description="Optional end received_time filter, ISO format."),
    raw: bool = Query(False, description="Download raw payload rows instead of decoded rows."),
    gse_report: bool = Query(False, description="Download compact GSE reception report rows."),
    decoder: str = Query("latest", description="Decoder version set for decoded download."),
    value_filters: str | None = Query(None, description="JSON encoded decoded value filters."),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Timestamp sort order."),
    limit: int = Query(10000, ge=1, le=100000, description="Maximum rows to download."),
    offset: int = Query(0, ge=0, description="Rows to skip for pagination."),
):
    decoded_filters = parse_value_filters(value_filters)
    decoded_rows = None
    with connect() as conn:
        ensure_payload_schema(conn, REALTIME_HK_TABLE)
        require_table(conn, REALTIME_HK_TABLE)
        if decoded_filters:
            rows, decoded_rows = select_decoded_download_rows(
                conn=conn,
                selector=select_realtime_hk_rows,
                selector_args=(gse, packet_id, start, end, received_start, received_end, order),
                decoder=decoder,
                decode_rows=decode_realtime_hk_rows,
                value_filters=decoded_filters,
                limit=limit,
                offset=offset,
            )
        else:
            rows = select_realtime_hk_rows(conn, gse, packet_id, start, end, received_start, received_end, order, limit, offset)

    if gse_report:
        return gse_report_csv_response("real_time_hk", gse, rows)
    if raw:
        return csv_response("raw_real_time_hk_payloads.csv", REALTIME_HK_COLUMNS, rows)
    return decoded_csv_response(
        decoded_filename("real_time_hk", decoder),
        decoded_rows if decoded_rows is not None else decode_realtime_hk_rows(rows, decoder),
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
    gse_report: bool = Query(False, description="Download compact GSE reception report rows."),
    decoder: str = Query("latest", description="Decoder version set for decoded download."),
    value_filters: str | None = Query(None, description="JSON encoded decoded value filters."),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Timestamp sort order."),
    limit: int = Query(10000, ge=1, le=100000, description="Maximum rows to download."),
    offset: int = Query(0, ge=0, description="Rows to skip for pagination."),
):
    decoded_filters = parse_value_filters(value_filters)
    decoded_rows = None
    with connect() as conn:
        require_table(conn, ADCS_HK_TABLE)
        ensure_payload_schema(conn, ADCS_HK_TABLE)
        if decoded_filters:
            rows, decoded_rows = select_decoded_download_rows(
                conn=conn,
                selector=select_adcs_hk_rows,
                selector_args=(gse, packet_id, sampling_type, start, end, received_start, received_end, order),
                decoder=decoder,
                decode_rows=decode_adcs_hk_rows,
                value_filters=decoded_filters,
                limit=limit,
                offset=offset,
            )
        else:
            rows = select_adcs_hk_rows(conn, gse, packet_id, sampling_type, start, end, received_start, received_end, order, limit, offset)

    if gse_report:
        return gse_report_csv_response("adcs_hk", gse, rows)
    if raw:
        return csv_response("raw_adcs_hk_payloads.csv", ADCS_HK_COLUMNS, rows)
    return decoded_csv_response(
        decoded_filename("adcs_hk", decoder),
        decoded_rows if decoded_rows is not None else decode_adcs_hk_rows(rows, decoder),
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
    "/payloads/real-time-hk",
    response_model=UploadResponse,
    tags=["Upload Payloads"],
    summary="Upload Real Time HK payload rows",
)
def upload_real_time_hk(payload: PayloadUpload):
    inserted = store_realtime_hk_payloads(db_path(), payload.packet_id, pd.DataFrame(payload.rows), payload.gse)
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
    raw_prefilter: RawPrefilter | None = None,
):
    where, params = build_filters(
        gse=gse,
        packet_id=packet_id,
        start=start,
        end=end,
        received_start=received_start,
        received_end=received_end,
        timestamp_column="timestamp_obc",
        extra_clauses=raw_prefilter.clauses if raw_prefilter else None,
        extra_params=raw_prefilter.params if raw_prefilter else None,
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


def select_main_hk_decode_candidate_rows(
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
    raw_prefilter: RawPrefilter | None = None,
):
    where, params = build_filters(
        gse=gse,
        packet_id=packet_id,
        start=start,
        end=end,
        received_start=received_start,
        received_end=received_end,
        timestamp_column="timestamp_obc",
        extra_clauses=raw_prefilter.clauses if raw_prefilter else None,
        extra_params=raw_prefilter.params if raw_prefilter else None,
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
            MIN(timestamp_obc_unix) AS sort_timestamp,
            MIN(data_hex) AS data_hex
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
    raw_prefilter: RawPrefilter | None = None,
) -> int:
    where, params = build_filters(
        gse=gse,
        packet_id=packet_id,
        start=start,
        end=end,
        received_start=received_start,
        received_end=received_end,
        timestamp_column="timestamp_obc",
        extra_clauses=raw_prefilter.clauses if raw_prefilter else None,
        extra_params=raw_prefilter.params if raw_prefilter else None,
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


def select_realtime_hk_rows(
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
        SELECT {", ".join(REALTIME_HK_COLUMNS)}
        FROM {REALTIME_HK_TABLE}
        {where}
        ORDER BY timestamp_obc_unix {direction}, received_time {direction}
        LIMIT ? OFFSET ?
        """,
        params,
    ).fetchall()


def select_realtime_hk_preview_rows(
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
        FROM {REALTIME_HK_TABLE}
        {where}
        GROUP BY unit_id
        ORDER BY sort_timestamp {direction}
        LIMIT ? OFFSET ?
        """,
        params,
    ).fetchall()


def select_realtime_hk_decode_candidate_rows(
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
            MIN(timestamp_obc_unix) AS sort_timestamp,
            MIN(data_hex) AS data_hex
        FROM {REALTIME_HK_TABLE}
        {where}
        GROUP BY unit_id
        ORDER BY sort_timestamp {direction}
        LIMIT ? OFFSET ?
        """,
        params,
    ).fetchall()


def count_realtime_hk_preview_rows(
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
            FROM {REALTIME_HK_TABLE}
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


def select_adcs_hk_decode_candidate_rows(
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
            MIN(timestamp_adcs_unix) AS sort_timestamp,
            MIN(data_hex) AS data_hex
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


def parse_value_filters(value_filters: str | None) -> list[dict[str, Any]]:
    if not value_filters:
        return []
    try:
        decoded = json.loads(value_filters)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid value_filters JSON: {exc.msg}") from exc
    if not isinstance(decoded, list):
        raise HTTPException(status_code=400, detail="value_filters must be a JSON array.")

    filters: list[dict[str, Any]] = []
    for item in decoded:
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail="Each value filter must be an object.")
        element = str(item.get("element") or "").strip()
        if not element:
            continue
        lower = parse_filter_bound(item.get("lower"), "lower", element)
        upper = parse_filter_bound(item.get("upper"), "upper", element)
        if lower is None and upper is None:
            continue
        if lower is not None and upper is not None and lower > upper:
            lower, upper = upper, lower
        filters.append({"element": element, "lower": lower, "upper": upper})
    return filters


def parse_value_columns(value_columns: str | None) -> list[str]:
    if not value_columns:
        return []
    try:
        decoded = json.loads(value_columns)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid value_columns JSON: {exc.msg}") from exc
    if not isinstance(decoded, list):
        raise HTTPException(status_code=400, detail="value_columns must be a JSON array.")

    columns: list[str] = []
    for item in decoded:
        column = str(item or "").strip()
        if column and column != "row_index" and column not in columns:
            columns.append(column)
    return columns


def parse_graph_x_column(x: str) -> str:
    column = str(x or "").strip()
    if not column:
        raise HTTPException(status_code=400, detail="x must be a non-empty column name.")
    if column == "row_index":
        raise HTTPException(status_code=400, detail="x cannot be row_index.")
    return column


def parse_graph_columns(value: str | None, field_name: str) -> list[str]:
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name} JSON: {exc.msg}") from exc
    if not isinstance(decoded, list):
        raise HTTPException(status_code=400, detail=f"{field_name} must be a JSON array.")

    columns: list[str] = []
    for item in decoded:
        column = str(item or "").strip()
        if column and column != "row_index" and column not in columns:
            columns.append(column)
    return columns


def project_graph_rows(rows: list[dict[str, Any]], columns: list[str]) -> list[dict[str, Any]]:
    return [{column: row_value(row, column) for column in columns} for row in rows]


def parse_filter_bound(value: Any, field: str, element: str) -> float | None:
    if value is None or value == "":
        return None
    try:
        bound = float(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"value_filters {field} for '{element}' must be numeric.",
        ) from exc
    if not math.isfinite(bound):
        raise HTTPException(
            status_code=400,
            detail=f"value_filters {field} for '{element}' must be finite.",
        )
    return bound


def select_decoded_preview_rows(
    *,
    conn,
    selector,
    selector_args: tuple,
    decoder: str,
    decode_rows,
    value_filters: list[dict[str, Any]],
    value_columns: list[str],
    exact_total: bool,
    limit: int,
    offset: int,
    raw_prefilter: RawPrefilter | None = None,
) -> tuple[list[dict[str, Any]], int]:
    require_latest_decoder(decoder)
    selected_elements = unique_elements(unique_filter_elements(value_filters), value_columns)
    matched_rows: list[dict[str, Any]] = []
    matched_total = 0
    candidate_offset = 0

    while True:
        candidates = select_decoded_candidates(
            selector,
            conn,
            selector_args,
            DECODE_FILTER_SCAN_CHUNK_SIZE,
            candidate_offset,
            raw_prefilter,
        )
        if not candidates:
            break

        decoded_candidates = decode_rows_aligned(candidates, decoder, decode_rows)
        for candidate, decoded_candidate in zip(candidates, decoded_candidates):
            if not decoded_row_matches_filters(decoded_candidate, value_filters):
                continue
            if matched_total >= offset and len(matched_rows) < limit:
                matched_rows.append(build_decoded_preview_row(candidate, decoded_candidate, selected_elements))
            matched_total += 1
            if not exact_total and len(matched_rows) >= limit:
                return matched_rows, matched_total

        candidate_offset += len(candidates)

    return matched_rows, matched_total


def select_decoded_page_rows(
    *,
    conn,
    selector,
    selector_args: tuple,
    count,
    count_args: tuple,
    decoder: str,
    decode_rows,
    value_columns: list[str],
    limit: int,
    offset: int,
    raw_prefilter: RawPrefilter | None = None,
    value_filters: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    require_latest_decoder(decoder)
    candidates = select_decoded_candidates(selector, conn, selector_args, limit, offset, raw_prefilter)
    decoded_candidates = decode_rows_aligned(candidates, decoder, decode_rows)
    rows = []
    for candidate, decoded_candidate in zip(candidates, decoded_candidates):
        if value_filters is not None and not decoded_row_matches_filters(decoded_candidate, value_filters):
            continue
        rows.append(build_decoded_preview_row(candidate, decoded_candidate, value_columns))
    if raw_prefilter is None:
        return rows, count(conn, *count_args)
    return rows, count(conn, *count_args, raw_prefilter)


def select_main_hk_single_graph_rows(
    *,
    conn,
    selector_args: tuple,
    count_args: tuple,
    decoder: str,
    value_filters: list[dict[str, Any]],
    value_columns: list[str],
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    require_latest_decoder(decoder)

    if not value_filters:
        candidates = select_main_hk_decode_candidate_rows(conn, *selector_args, limit, offset)
        decoded_candidates = decode_main_hk_single_rows(candidates, value_columns)
        rows = [
            build_decoded_preview_row(candidate, decoded_candidate, value_columns)
            for candidate, decoded_candidate in zip(candidates, decoded_candidates)
        ]
        return rows, count_main_hk_preview_rows(conn, *count_args)

    raw_prefilter = build_main_hk_raw_prefilter(value_filters)
    if raw_prefilter.supported_count == len(value_filters):
        candidates = select_main_hk_decode_candidate_rows(conn, *selector_args, limit, offset, raw_prefilter)
        decoded_candidates = decode_main_hk_single_rows(candidates, value_columns)
        rows = [
            build_decoded_preview_row(candidate, decoded_candidate, value_columns)
            for candidate, decoded_candidate in zip(candidates, decoded_candidates)
            if decoded_row_matches_filters(decoded_candidate, value_filters)
        ]
        return rows, count_main_hk_preview_rows(conn, *count_args, raw_prefilter)

    candidate_prefilter = raw_prefilter if raw_prefilter.supported_count else None
    matched_rows: list[dict[str, Any]] = []
    matched_total = 0
    candidate_offset = 0

    while len(matched_rows) < limit:
        candidates = select_decoded_candidates(
            select_main_hk_decode_candidate_rows,
            conn,
            selector_args,
            DECODE_FILTER_SCAN_CHUNK_SIZE,
            candidate_offset,
            candidate_prefilter,
        )
        if not candidates:
            break

        decoded_candidates = decode_main_hk_single_rows(candidates, value_columns)
        for candidate, decoded_candidate in zip(candidates, decoded_candidates):
            if not decoded_row_matches_filters(decoded_candidate, value_filters):
                continue
            if matched_total >= offset and len(matched_rows) < limit:
                matched_rows.append(build_decoded_preview_row(candidate, decoded_candidate, value_columns))
            matched_total += 1

        candidate_offset += len(candidates)

    return matched_rows, matched_total


def select_decoded_download_rows(
    *,
    conn,
    selector,
    selector_args: tuple,
    decoder: str,
    decode_rows,
    value_filters: list[dict[str, Any]],
    limit: int,
    offset: int,
    raw_prefilter: RawPrefilter | None = None,
) -> tuple[list[Any], list[dict[str, Any]]]:
    require_latest_decoder(decoder)
    filtered_rows: list[Any] = []
    filtered_decoded_rows: list[dict[str, Any]] = []
    matched_total = 0
    candidate_offset = 0

    while len(filtered_rows) < limit:
        candidates = select_decoded_candidates(
            selector,
            conn,
            selector_args,
            DECODE_FILTER_SCAN_CHUNK_SIZE,
            candidate_offset,
            raw_prefilter,
        )
        if not candidates:
            break

        decoded_candidates = decode_rows_aligned(candidates, decoder, decode_rows)
        for candidate, decoded_candidate in zip(candidates, decoded_candidates):
            if not decoded_row_matches_filters(decoded_candidate, value_filters):
                continue
            if matched_total >= offset and len(filtered_rows) < limit:
                filtered_rows.append(candidate)
                filtered_decoded_rows.append(decoded_candidate)
            matched_total += 1

        candidate_offset += len(candidates)

    return filtered_rows, filtered_decoded_rows


def select_decoded_candidates(selector, conn, selector_args: tuple, limit: int, offset: int, raw_prefilter: RawPrefilter | None):
    if raw_prefilter is None:
        return selector(conn, *selector_args, limit, offset)
    return selector(conn, *selector_args, limit, offset, raw_prefilter)


def unique_filter_elements(value_filters: list[dict[str, Any]]) -> list[str]:
    elements: list[str] = []
    for value_filter in value_filters:
        element = value_filter["element"]
        if element not in elements:
            elements.append(element)
    return elements


def unique_elements(*element_groups: list[str]) -> list[str]:
    elements: list[str] = []
    for element_group in element_groups:
        for element in element_group:
            if element not in elements:
                elements.append(element)
    return elements


def decode_rows_aligned(rows, decoder: str, decode_rows) -> list[dict[str, Any]]:
    try:
        decoded_rows = decode_rows(rows, decoder)
    except HTTPException:
        raise
    except Exception:
        return [decode_single_row(row, decoder, decode_rows) for row in rows]
    if len(decoded_rows) == len(rows):
        return decoded_rows
    return [decode_single_row(row, decoder, decode_rows) for row in rows]


def decode_single_row(row, decoder: str, decode_rows) -> dict[str, Any]:
    try:
        decoded_rows = decode_rows([row], decoder)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to decode telemetry row.") from exc
    return decoded_rows[0] if decoded_rows else {}


def decoded_row_matches_filters(decoded_row: dict[str, Any], value_filters: list[dict[str, Any]]) -> bool:
    for value_filter in value_filters:
        numeric = numeric_decoded_value(decoded_row.get(value_filter["element"]))
        if numeric is None:
            return False
        lower = value_filter["lower"]
        upper = value_filter["upper"]
        if lower is not None and numeric < lower:
            return False
        if upper is not None and numeric > upper:
            return False
    return True


def numeric_decoded_value(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def build_decoded_preview_row(row, decoded_row: dict[str, Any], selected_elements: list[str]) -> dict[str, Any]:
    preview_row = dict(row)
    preview_row.pop("data_hex", None)
    for element in selected_elements:
        if element not in preview_row:
            preview_row[element] = decoded_row.get(element, "")
    return preview_row


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
    extra_clauses: list[str] | None = None,
    extra_params: list[object] | None = None,
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
    if extra_clauses:
        clauses.extend(extra_clauses)
        params.extend(extra_params or [])

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
        writer.writerow({column: row_value(row, column) for column in columns})

    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def row_value(row, column: str):
    try:
        return row[column]
    except (KeyError, IndexError):
        return ""


def decoded_csv_response(filename: str, decoded_rows: list[dict]):
    df = pd.DataFrame(decoded_rows)
    stream = StringIO()
    df.to_csv(stream, index=False)
    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def gse_report_csv_response(dataset: str, gse: str | None, rows):
    columns, report_rows = build_gse_report_rows(rows, gse)
    return csv_response(gse_report_filename(dataset, gse), columns, report_rows)


def build_gse_report_rows(rows, requested_gse: str | None) -> tuple[list[str], list[dict]]:
    grouped: dict[str, dict] = {}
    station_names = {requested_gse} if requested_gse else {"ISAS", "Kyutech"}

    for row in rows:
        unit_id = row["unit_id"]
        station = row["gse"] or "unknown"
        station_names.add(station)
        report_row = grouped.setdefault(unit_id, {"unit_id": unit_id})
        prefix = safe_column_prefix(station)
        report_row[f"{prefix}_packet_id"] = row["packet_id"]
        report_row[f"{prefix}_received_time"] = row["received_time"]

    stations = ordered_station_names(station_names)
    columns = ["unit_id"]
    for station in stations:
        prefix = safe_column_prefix(station)
        columns.extend(f"{prefix}_{field}" for field in GSE_REPORT_FIELDS)

    return columns, list(grouped.values())


def ordered_station_names(station_names: set[str]) -> list[str]:
    ordered = [station for station in GSE_REPORT_STATION_ORDER if station in station_names]
    ordered.extend(sorted(station for station in station_names if station not in GSE_REPORT_STATION_ORDER))
    return ordered


def decoded_filename(dataset: str, decoder: str) -> str:
    return f"decoded_{dataset}_{safe_filename_part(decoder)}.csv"


def gse_report_filename(dataset: str, gse: str | None) -> str:
    station = safe_filename_part(gse or "all_gse")
    return f"gse_reception_{dataset}_{station}.csv"


def safe_column_prefix(value: str) -> str:
    return safe_filename_part(value)


def safe_filename_part(value: str) -> str:
    return "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in value).strip("_") or "decoder"


def decode_main_hk_rows(rows, decoder: str) -> list[dict]:
    require_latest_decoder(decoder)
    from decoder import decoder_main_HK

    return decoder_main_HK.decode(join_data_hex(rows))


def decode_realtime_hk_rows(rows, decoder: str) -> list[dict]:
    require_latest_decoder(decoder)
    from decoder import decoder_real_time_telemetry

    return decoder_real_time_telemetry.decode(join_data_hex(rows))


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
        detail=f"Decoded values for decoder version '{decoder}' are not implemented yet.",
    )


def ensure_decoder_import_path() -> None:
    root = decoder_dir().parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
