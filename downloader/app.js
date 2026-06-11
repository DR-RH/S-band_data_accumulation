const state = {
  activeTab: "main",
  offsets: {
    main: 0,
    adcs: 0,
    realtime: 0,
  },
  totals: {
    main: 0,
    adcs: 0,
    realtime: 0,
  },
};

const PAGE_SIZE = 200;

const FILTER_CACHE_KEY = "s-band-downloader-filters-v1";
const DEFAULT_RANGE = {
  startDate: "2026-01-01",
  startTime: "00:00",
  endDate: "2026-12-31",
  endTime: "00:00",
  receivedStartDate: "",
  receivedStartTime: "00:00",
  receivedEndDate: "",
  receivedEndTime: "23:59",
};
const DEFAULT_SHARED_VALUES = {
  ...DEFAULT_RANGE,
  gse: "",
  limit: "1000",
  order: "desc",
  decoder: "latest",
};
const SHARED_QUERY_FIELDS = [
  "startDate",
  "startTime",
  "endDate",
  "endTime",
  "receivedStartDate",
  "receivedStartTime",
  "receivedEndDate",
  "receivedEndTime",
  "gse",
  "limit",
  "order",
  "decoder",
];

const apiBase = document.querySelector("#apiBase");
const serverState = document.querySelector("#serverState");

loadCachedFilters();

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    const nextTab = tab.dataset.tab;
    state.activeTab = nextTab;
    document.querySelectorAll(".tab").forEach((item) => {
      item.setAttribute("aria-selected", String(item.dataset.tab === nextTab));
    });
    document.querySelectorAll(".pane").forEach((pane) => {
      pane.classList.toggle("active", pane.dataset.pane === nextTab);
    });
  });
});

document.querySelectorAll("[data-action='search']").forEach((button) => {
  button.addEventListener("click", () => {
    state.offsets[button.dataset.kind] = 0;
    searchRows(button.dataset.kind);
  });
});

document.querySelectorAll("[data-action='download']").forEach((button) => {
  button.addEventListener("click", () => downloadCsv(button.dataset.kind));
});

document.querySelectorAll("[data-page]").forEach((button) => {
  button.addEventListener("click", () => changePage(button.dataset.kind, button.dataset.page));
});

document.querySelectorAll("[data-page-input]").forEach((input) => {
  input.addEventListener("change", () => jumpToPage(input.dataset.pageInput, input.value));
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      jumpToPage(input.dataset.pageInput, input.value);
    }
  });
});

document.querySelectorAll("form[data-form]").forEach((form) => {
  form.addEventListener("input", (event) => {
    if (isSharedQueryField(event.target.name)) {
      syncSharedQueryFields(form);
      saveCachedFilters();
    }
  });
  form.addEventListener("change", (event) => {
    if (isSharedQueryField(event.target.name)) {
      syncSharedQueryFields(form);
      resetAllQueryState();
    } else {
      resetQueryState(form.dataset.form);
    }
    saveCachedFilters();
  });
});

apiBase.addEventListener("change", checkServer);

checkServer();
loadDecoders();

async function checkServer() {
  try {
    const response = await fetch(`${cleanApiBase()}/health`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    serverState.textContent = `Connected: ${data.db_path}`;
    serverState.className = "server-state ok";
  } catch (error) {
    serverState.textContent = `Disconnected: ${error.message}`;
    serverState.className = "server-state error";
  }
}

async function loadDecoders() {
  try {
    const response = await fetch(`${cleanApiBase()}/decoders`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    document.querySelectorAll("select[name='decoder']").forEach((select) => {
      const currentValue = select.value;
      select.innerHTML = data.decoders.map((decoder) => {
        return `<option value="${escapeHtml(decoder.value)}">${escapeHtml(decoder.label)}</option>`;
      }).join("");
      if ([...select.options].some((option) => option.value === currentValue)) {
        select.value = currentValue;
      }
    });
  } catch {
    // Keep the built-in fallback options when the server cannot list decoders.
  }
}

async function searchRows(kind) {
  const tbody = document.querySelector(rowTargetSelector(kind));
  tbody.innerHTML = `<tr><td colspan="${columnCount(kind)}">Loading...</td></tr>`;

  try {
    const limit = displayLimit(kind);
    const offset = Math.min(state.offsets[kind], maxOffsetForLimit(limit));
    const pageLimit = Math.min(PAGE_SIZE, Math.max(limit - offset, 1));
    state.offsets[kind] = offset;

    const response = await fetch(readUrl(kind, pageLimit, offset));
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    renderRows(kind, data.rows);
    state.totals[kind] = Math.min(data.total || 0, limit);
    updatePager(kind, data.rows.length, state.totals[kind]);
  } catch (error) {
    tbody.innerHTML = `<tr><td colspan="${columnCount(kind)}">Failed: ${escapeHtml(error.message)}</td></tr>`;
  }
}

function changePage(kind, direction) {
  const maxOffset = lastPageOffset(kind);
  let nextOffset = state.offsets[kind];
  if (direction === "first") nextOffset = 0;
  if (direction === "back") nextOffset = Math.max(0, state.offsets[kind] - PAGE_SIZE);
  if (direction === "next") nextOffset = Math.min(maxOffset, state.offsets[kind] + PAGE_SIZE);
  if (direction === "end") nextOffset = maxOffset;
  if (nextOffset === state.offsets[kind]) return;
  state.offsets[kind] = nextOffset;
  searchRows(kind);
}

function jumpToPage(kind, value) {
  const pageCount = totalPages(kind);
  if (!pageCount) return;
  const requestedPage = Number.parseInt(value, 10);
  const page = Math.min(Math.max(requestedPage || 1, 1), pageCount);
  state.offsets[kind] = (page - 1) * PAGE_SIZE;
  searchRows(kind);
}

function downloadCsv(kind) {
  window.location.href = downloadUrl(kind);
}

function readUrl(kind, limitOverride, offsetOverride = 0) {
  const path = datasetPath(kind);
  return `${cleanApiBase()}${path}?${queryParams(kind, limitOverride, offsetOverride)}`;
}

function downloadUrl(kind) {
  const path = datasetDownloadPath(kind);
  return `${cleanApiBase()}${path}?${queryParams(kind)}`;
}

function queryParams(kind, limitOverride, offsetOverride = 0) {
  saveCachedFilters();
  const form = document.querySelector(`[data-form='${kind}']`);
  const data = new FormData(form);
  const params = new URLSearchParams();

  const start = combineDateTime(data.get("startDate"), data.get("startTime"));
  const end = combineDateTime(data.get("endDate"), data.get("endTime"));
  const receivedStart = combineDateTime(data.get("receivedStartDate"), data.get("receivedStartTime"));
  const receivedEnd = combineDateTime(data.get("receivedEndDate"), data.get("receivedEndTime"));
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  if (receivedStart) params.set("received_start", receivedStart);
  if (receivedEnd) params.set("received_end", receivedEnd);
  if (data.get("gse")) params.set("gse", data.get("gse"));

  if (kind === "adcs" && data.get("sampling_type")) {
    params.set("sampling_type", data.get("sampling_type"));
  }

  params.set("order", data.get("order") || "desc");
  params.set("limit", limitOverride || data.get("limit") || "1000");
  params.set("offset", String(offsetOverride));
  params.set("decoder", data.get("decoder") || "latest");
  params.set("raw", data.get("raw") === "on" ? "1" : "0");

  return params.toString();
}

function combineDateTime(date, time) {
  if (!date) return "";
  return `${date}T${time || "00:00"}:00+00:00`;
}

function cleanApiBase() {
  return apiBase.value.replace(/\/+$/, "");
}

function renderRows(kind, rows) {
  const tbody = document.querySelector(rowTargetSelector(kind));
  const displayRows = mergeDuplicateUnits(rows);
  if (!displayRows.length) {
    tbody.innerHTML = `<tr><td colspan="${columnCount(kind)}">No rows found.</td></tr>`;
    return;
  }

  tbody.innerHTML = displayRows.map((row) => {
    if (kind === "main" || kind === "realtime") {
      return rowHtml([
        row.gse,
        row.packet_id,
        row.received_time,
        row.timestamp_obc,
      ]);
    }
    return rowHtml([
      row.gse,
      row.packet_id,
      row.sampling_type,
      row.received_time,
      row.timestamp_adcs,
    ]);
  }).join("");
}

function updatePager(kind, rowCount, total) {
  const label = document.querySelector(`[data-page-label='${kind}']`);
  const input = document.querySelector(`[data-page-input='${kind}']`);
  const first = document.querySelector(`[data-page='first'][data-kind='${kind}']`);
  const back = document.querySelector(`[data-page='back'][data-kind='${kind}']`);
  const next = document.querySelector(`[data-page='next'][data-kind='${kind}']`);
  const end = document.querySelector(`[data-page='end'][data-kind='${kind}']`);
  const page = currentPage(kind);
  const pageTotal = totalPages(kind);
  const hasRows = total > 0;
  const atFirst = state.offsets[kind] === 0;
  const atEnd = !hasRows || state.offsets[kind] >= lastPageOffset(kind);

  if (label) {
    label.textContent = `/ ${pageTotal}`;
  }
  if (input) {
    input.disabled = !hasRows;
    input.max = String(pageTotal || 1);
    input.value = String(page || 1);
    input.title = rowCount ? `${state.offsets[kind] + 1}-${state.offsets[kind] + rowCount} of ${total}` : "No rows";
  }
  if (first) {
    first.disabled = !hasRows || atFirst;
  }
  if (back) {
    back.disabled = !hasRows || atFirst;
  }
  if (next) {
    next.disabled = atEnd;
  }
  if (end) {
    end.disabled = atEnd;
  }
}

function currentPage(kind) {
  return Math.floor(state.offsets[kind] / PAGE_SIZE) + 1;
}

function totalPages(kind) {
  return Math.ceil(state.totals[kind] / PAGE_SIZE);
}

function lastPageOffset(kind) {
  const pages = totalPages(kind);
  return pages ? (pages - 1) * PAGE_SIZE : 0;
}

function displayLimit(kind) {
  const form = document.querySelector(`[data-form='${kind}']`);
  const value = Number.parseInt(form?.elements.limit?.value, 10);
  return Number.isFinite(value) && value > 0 ? value : Number.parseInt(DEFAULT_SHARED_VALUES.limit, 10);
}

function maxOffsetForLimit(limit) {
  return limit > 0 ? Math.floor((limit - 1) / PAGE_SIZE) * PAGE_SIZE : 0;
}

function mergeDuplicateUnits(rows) {
  const byUnit = new Map();
  rows.forEach((row) => {
    const key = row.unit_id || `${row.packet_id}|${row.timestamp_obc || row.timestamp_adcs}|${row.data_hex}`;
    if (!byUnit.has(key)) {
      byUnit.set(key, { ...row, gse: row.gse || "" });
      return;
    }
    const current = byUnit.get(key);
    current.gse = mergeGseLabels(current.gse, row.gse);
  });
  return [...byUnit.values()];
}

function mergeGseLabels(left, right) {
  return [...new Set([left, right].flatMap((value) => String(value || "").split(",").map((item) => item.trim()).filter(Boolean)))]
    .sort()
    .join(", ");
}

function columnCount(kind) {
  return kind === "adcs" ? 5 : 4;
}

function rowTargetSelector(kind) {
  if (kind === "main") return "#mainRows";
  if (kind === "realtime") return "#realtimeRows";
  return "#adcsRows";
}

function datasetPath(kind) {
  if (kind === "main") return "/main-hk";
  if (kind === "realtime") return "/real-time-hk";
  return "/adcs-hk";
}

function datasetDownloadPath(kind) {
  if (kind === "main") return "/downloads/main-hk.csv";
  if (kind === "realtime") return "/downloads/real-time-hk.csv";
  return "/downloads/adcs-hk.csv";
}

function rowHtml(values) {
  return `<tr>${values.map((value) => `<td>${escapeHtml(value ?? "")}</td>`).join("")}</tr>`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function loadCachedFilters() {
  const cache = readFilterCache();
  const sharedValues = sharedQueryValuesFromCache(cache);
  document.querySelectorAll("form[data-form]").forEach((form) => {
    const kind = form.dataset.form;
    const values = { ...DEFAULT_RANGE, ...(cache[kind] || {}), ...sharedValues };
    setFormValue(form, "startDate", values.startDate);
    setFormValue(form, "startTime", values.startTime);
    setFormValue(form, "endDate", values.endDate);
    setFormValue(form, "endTime", values.endTime);
    setFormValue(form, "receivedStartDate", values.receivedStartDate);
    setFormValue(form, "receivedStartTime", values.receivedStartTime);
    setFormValue(form, "receivedEndDate", values.receivedEndDate);
    setFormValue(form, "receivedEndTime", values.receivedEndTime);
    setFormValue(form, "gse", values.gse || "");
    setFormValue(form, "limit", values.limit || "1000");
    setFormValue(form, "order", values.order || "desc");
    setFormValue(form, "decoder", values.decoder || "latest");
    setFormValue(form, "sampling_type", values.sampling_type || "");
    setFormChecked(form, "raw", values.raw === "1");
  });
}

function saveCachedFilters() {
  const firstForm = document.querySelector("form[data-form]");
  const sharedValues = firstForm ? readSharedQueryFields(firstForm) : { ...DEFAULT_SHARED_VALUES };
  const cache = { shared: sharedValues };
  document.querySelectorAll("form[data-form]").forEach((form) => {
    const data = new FormData(form);
    cache[form.dataset.form] = {
      ...sharedValues,
      gse: data.get("gse") || "",
      limit: data.get("limit") || "1000",
      order: data.get("order") || "desc",
      decoder: data.get("decoder") || "latest",
      sampling_type: data.get("sampling_type") || "",
      raw: data.get("raw") === "on" ? "1" : "0",
    };
  });
  localStorage.setItem(FILTER_CACHE_KEY, JSON.stringify(cache));
}

function readFilterCache() {
  try {
    return JSON.parse(localStorage.getItem(FILTER_CACHE_KEY)) || {};
  } catch {
    return {};
  }
}

function isSharedQueryField(name) {
  return SHARED_QUERY_FIELDS.includes(name);
}

function syncSharedQueryFields(sourceForm) {
  const values = readSharedQueryFields(sourceForm);
  document.querySelectorAll("form[data-form]").forEach((form) => {
    if (form === sourceForm) return;
    SHARED_QUERY_FIELDS.forEach((name) => setFormValue(form, name, values[name]));
  });
}

function readSharedQueryFields(form) {
  const data = new FormData(form);
  return Object.fromEntries(
    SHARED_QUERY_FIELDS.map((name) => [name, data.get(name) || DEFAULT_SHARED_VALUES[name]])
  );
}

function sharedQueryValuesFromCache(cache) {
  const values = { ...DEFAULT_SHARED_VALUES };
  [cache.realtime, cache.adcs, cache.main, cache.shared].forEach((source) => {
    Object.assign(values, pickSharedQueryFields(source || {}));
  });
  return values;
}

function pickSharedQueryFields(values) {
  return Object.fromEntries(
    SHARED_QUERY_FIELDS
      .filter((name) => values[name] !== undefined)
      .map((name) => [name, values[name]])
  );
}

function resetAllQueryState() {
  document.querySelectorAll("form[data-form]").forEach((form) => resetQueryState(form.dataset.form));
}

function resetQueryState(kind) {
  state.offsets[kind] = 0;
  state.totals[kind] = 0;
  updatePager(kind, 0, 0);
}

function setFormValue(form, name, value) {
  const field = form.elements[name];
  if (field) field.value = value;
}

function setFormChecked(form, name, checked) {
  const field = form.elements[name];
  if (field) field.checked = checked;
}
