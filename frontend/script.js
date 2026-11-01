/**
 * script.js – APIWatch Frontend Logic
 *
 * Handles all frontend interactivity:
 * - Navigation between sections
 * - Sending API requests
 * - Managing collections
 * - Displaying history
 * - Monitoring endpoints
 * - Report generation
 */

const API_BASE = "http://localhost:8000";

// ─── Navigation ────────────────────────────────────────────────────────────

document.querySelectorAll(".nav-link").forEach(link => {
  link.addEventListener("click", e => {
    e.preventDefault();
    const section = link.dataset.section;
    navigateTo(section);
  });
});

function navigateTo(section) {
  // Update nav links
  document.querySelectorAll(".nav-link").forEach(l => l.classList.remove("active"));
  const navLink = document.getElementById(`nav-${section}`);
  if (navLink) navLink.classList.add("active");

  // Show section
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
  const el = document.getElementById(`section-${section}`);
  if (el) el.classList.add("active");

  // Load section data
  if (section === "dashboard")   loadDashboard();
  if (section === "collections") loadCollections();
  if (section === "monitoring")  loadMonitoring();
  if (section === "history")     loadHistory();
  if (section === "reports")     loadReportStats();
  if (section === "tester")      populateSaveCollectionDropdown();
}

// ─── Tab switching ─────────────────────────────────────────────────────────

document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const tabId = btn.dataset.tab;
    const parent = btn.closest(".card, .section");

    // Deactivate sibling tab buttons
    btn.closest(".tab-bar").querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");

    // Deactivate sibling tab contents inside the same panel
    if (parent) {
      parent.querySelectorAll(".tab-content").forEach(t => t.classList.remove("active"));
      const target = parent.querySelector(`#${tabId}`);
      if (target) target.classList.add("active");
    }
  });
});

// ─── Dashboard ─────────────────────────────────────────────────────────────

async function loadDashboard() {
  try {
    const data = await apiGet("/api/reports/dashboard");
    document.getElementById("stat-total").textContent   = data.total_requests ?? 0;
    document.getElementById("stat-success").textContent = data.successful_requests ?? 0;
    document.getElementById("stat-failed").textContent  = data.failed_requests ?? 0;
    document.getElementById("stat-avg-time").textContent =
      data.average_response_time_ms != null ? `${data.average_response_time_ms}ms` : "—";

    const container = document.getElementById("recent-activity");
    if (!data.recent_history || data.recent_history.length === 0) {
      container.innerHTML = `<div class="empty-state">No requests yet. Go to API Tester to get started!</div>`;
      return;
    }
    container.innerHTML = data.recent_history.map(r => `
      <div class="data-table-row" style="display:flex;gap:1rem;align-items:center;padding:.6rem .75rem;border-bottom:1px solid var(--border-subtle);">
        <span class="method-badge method-${r.method}">${r.method}</span>
        <span style="flex:1;font-family:var(--font-mono);font-size:.8rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${r.url}</span>
        <span class="badge ${statusBadgeClass(r.status_code)}">${r.status_code ?? "ERR"}</span>
        <span style="color:var(--text-secondary);font-size:.78rem;">${r.response_time_ms ? r.response_time_ms + "ms" : "—"}</span>
        <span style="color:var(--text-muted);font-size:.75rem;">${formatDate(r.timestamp)}</span>
      </div>
    `).join("");
  } catch (err) {
    console.error("Dashboard load failed:", err);
  }
}

// ─── API Tester ─────────────────────────────────────────────────────────────

function collectKVPairs(editorId) {
  const rows = document.querySelectorAll(`#${editorId} .kv-row:not(.kv-header-row)`);
  const result = {};
  rows.forEach(row => {
    const inputs = row.querySelectorAll(".kv-input");
    const key   = inputs[0]?.value.trim();
    const value = inputs[1]?.value.trim();
    if (key) result[key] = value;
  });
  return result;
}

function collectAssertions() {
  const rows = document.querySelectorAll("#assertions-list .assertion-row");
  return Array.from(rows).map(row => {
    const selects = row.querySelectorAll(".assertion-select");
    const inputs  = row.querySelectorAll(".kv-input");
    return {
      type:     selects[0]?.value,
      key:      inputs[0]?.value.trim() || null,
      expected: inputs[1]?.value.trim(),
    };
  }).filter(a => a.type && a.expected);
}

async function sendRequest() {
  const method      = document.getElementById("method-select").value;
  const url         = document.getElementById("url-input").value.trim();
  const body        = document.getElementById("body-input").value;
  const headers     = collectKVPairs("headers-editor");
  const queryParams = collectKVPairs("params-editor");
  const assertions  = collectAssertions();

  if (!url) { showToast("Please enter a URL", "error"); return; }

  const btn = document.getElementById("send-btn");
  btn.disabled = true;
  btn.textContent = "Sending…";
  document.getElementById("response-loading").classList.remove("hidden");
  document.getElementById("response-body").textContent    = "";
  document.getElementById("response-headers").textContent = "";
  document.getElementById("response-meta").innerHTML      = "";
  document.getElementById("assertion-results").classList.add("hidden");

  try {
    const result = await apiPost("/api/requests/send", {
      method, url, headers, body, query_params: queryParams,
      assertions: assertions.length > 0 ? assertions : null,
    });

    // Show status / time
    const statusClass = statusBadgeClass(result.status_code);
    document.getElementById("response-meta").innerHTML = `
      <span class="badge ${statusClass}">${result.status_code ?? "ERR"}</span>
      <span class="time-badge">${result.response_time_ms ? result.response_time_ms + " ms" : ""}</span>
    `;

    // Show body (pretty-print JSON if possible)
    document.getElementById("response-body").textContent = prettyJSON(result.response_body);

    // Show headers
    document.getElementById("response-headers").textContent =
      JSON.stringify(result.response_headers, null, 2);

    // Show error if any
    if (result.error_message) {
      document.getElementById("response-body").textContent = `⚠ Error: ${result.error_message}`;
    }

    // Show assertions
    if (result.assertion_results && result.assertion_results.length > 0) {
      const assertionEl = document.getElementById("assertion-results");
      assertionEl.classList.remove("hidden");
      assertionEl.innerHTML = result.assertion_results.map(a => `
        <div class="assertion-result-row ${a.passed ? 'pass' : 'fail'}">
          <span>${a.passed ? "✅" : "❌"}</span>
          <span style="font-weight:600;min-width:100px;">${a.type}</span>
          <span style="color:var(--text-secondary);flex:1;">${a.message}</span>
          <span style="font-family:var(--font-mono);font-size:.75rem;">Expected: ${a.expected}</span>
        </div>
      `).join("");
    }

  } catch (err) {
    document.getElementById("response-body").textContent = `⚠ Request failed: ${err.message}`;
  } finally {
    btn.disabled = false;
    btn.textContent = "Send";
    document.getElementById("response-loading").classList.add("hidden");
  }
}

function addKVRow(editorId) {
  const editor = document.getElementById(editorId);
  const row = document.createElement("div");
  row.className = "kv-row";
  row.innerHTML = `
    <input type="text" class="kv-input" placeholder="Key" />
    <input type="text" class="kv-input" placeholder="Value" />
    <button class="kv-remove" onclick="this.parentElement.remove()">×</button>
  `;
  editor.appendChild(row);
}

function addAssertion() {
  const list = document.getElementById("assertions-list");
  const row = document.createElement("div");
  row.className = "assertion-row";
  row.innerHTML = `
    <select class="assertion-select">
      <option value="status_code">Status Code</option>
      <option value="body_contains">Body Contains</option>
      <option value="json_key">JSON Key Exists</option>
      <option value="json_value">JSON Key=Value</option>
      <option value="response_time">Max Response Time (ms)</option>
    </select>
    <input type="text" class="kv-input" placeholder="Key (for json_value)" />
    <input type="text" class="kv-input" placeholder="Expected value" />
    <button class="kv-remove" onclick="this.parentElement.remove()">×</button>
  `;
  list.appendChild(row);
}

async function saveCurrentRequest() {
  const name         = document.getElementById("save-name").value.trim();
  const collectionId = document.getElementById("save-collection").value;

  if (!name)         { showToast("Please enter a request name", "error"); return; }
  if (!collectionId) { showToast("Please select a collection", "error"); return; }

  const method      = document.getElementById("method-select").value;
  const url         = document.getElementById("url-input").value.trim();
  const headers     = JSON.stringify(collectKVPairs("headers-editor"));
  const body        = document.getElementById("body-input").value;
  const queryParams = JSON.stringify(collectKVPairs("params-editor"));

  try {
    await apiPost("/api/collections/requests", {
      name, method, url,
      headers, body, query_params: queryParams,
      collection_id: parseInt(collectionId),
    });
    showToast(`Request "${name}" saved!`, "success");
    document.getElementById("save-name").value = "";
  } catch (err) {
    showToast("Failed to save: " + err.message, "error");
  }
}

async function populateSaveCollectionDropdown() {
  try {
    const collections = await apiGet("/api/collections/");
    const sel = document.getElementById("save-collection");
    sel.innerHTML = `<option value="">Select collection...</option>`;
    collections.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = c.name;
      sel.appendChild(opt);
    });
  } catch (_) {}
}

// ─── Collections ────────────────────────────────────────────────────────────

let editingCollectionId = null;

async function loadCollections() {
  try {
    const collections = await apiGet("/api/collections/");
    const container = document.getElementById("collections-list");

    if (collections.length === 0) {
      container.innerHTML = `<div class="empty-state">No collections yet. Create one to save requests.</div>`;
      return;
    }

    container.innerHTML = collections.map(c => `
      <div class="collection-card">
        <div class="collection-card-header">
          <div>
            <h3>📁 ${escHtml(c.name)}</h3>
          </div>
          <div style="display:flex;gap:.4rem;">
            <button class="btn btn-sm btn-ghost" onclick="editCollection(${c.id}, '${escHtml(c.name)}', '${escHtml(c.description)}')">✏</button>
            <button class="btn btn-sm btn-danger" onclick="deleteCollection(${c.id})">🗑</button>
          </div>
        </div>
        ${c.description ? `<div class="collection-desc">${escHtml(c.description)}</div>` : ""}
        <div class="saved-requests-list">
          ${c.saved_requests.length === 0
            ? `<div style="padding:.5rem .75rem;color:var(--text-muted);font-size:.8rem;">No requests saved yet.</div>`
            : c.saved_requests.map(r => `
              <div class="saved-req-item">
                <span class="method-badge method-${r.method}">${r.method}</span>
                <span class="saved-req-name">${escHtml(r.name)}</span>
                <button class="btn btn-sm btn-success" onclick="executeRequest(${r.id})">▶</button>
                <button class="btn btn-sm btn-danger"  onclick="deleteSavedRequest(${r.id}, ${c.id})">🗑</button>
              </div>
            `).join("")
          }
        </div>
        <button class="collection-add-btn" onclick="openAddRequestToCollection(${c.id})">+ Add Request</button>
      </div>
    `).join("");
  } catch (err) {
    showToast("Failed to load collections", "error");
  }
}

function showNewCollectionModal() {
  editingCollectionId = null;
  document.getElementById("collection-modal-title").textContent = "New Collection";
  document.getElementById("collection-name").value = "";
  document.getElementById("collection-desc").value = "";
  document.getElementById("collection-modal").classList.remove("hidden");
}

function editCollection(id, name, desc) {
  editingCollectionId = id;
  document.getElementById("collection-modal-title").textContent = "Edit Collection";
  document.getElementById("collection-name").value = name;
  document.getElementById("collection-desc").value = desc;
  document.getElementById("collection-modal").classList.remove("hidden");
}

async function saveCollection() {
  const name = document.getElementById("collection-name").value.trim();
  const desc = document.getElementById("collection-desc").value.trim();
  if (!name) { showToast("Name is required", "error"); return; }

  try {
    if (editingCollectionId) {
      await apiPut(`/api/collections/${editingCollectionId}`, { name, description: desc });
      showToast("Collection updated!", "success");
    } else {
      await apiPost("/api/collections/", { name, description: desc });
      showToast("Collection created!", "success");
    }
    closeModal("collection-modal");
    loadCollections();
  } catch (err) {
    showToast("Failed: " + err.message, "error");
  }
}

async function deleteCollection(id) {
  if (!confirm("Delete this collection and all its saved requests?")) return;
  try {
    await apiDelete(`/api/collections/${id}`);
    showToast("Collection deleted", "success");
    loadCollections();
  } catch (err) {
    showToast("Failed: " + err.message, "error");
  }
}

function openAddRequestToCollection(collectionId) {
  document.getElementById("sr-name").value = "";
  document.getElementById("sr-method").value = "GET";
  document.getElementById("sr-url").value = "";
  document.getElementById("sr-headers").value = "{}";
  document.getElementById("sr-body").value = "";
  document.getElementById("sr-collection-id").value = collectionId;
  document.getElementById("save-request-modal").classList.remove("hidden");
}

async function saveSavedRequest() {
  const name         = document.getElementById("sr-name").value.trim();
  const method       = document.getElementById("sr-method").value.trim().toUpperCase() || "GET";
  const url          = document.getElementById("sr-url").value.trim();
  const headers      = document.getElementById("sr-headers").value.trim() || "{}";
  const body         = document.getElementById("sr-body").value;
  const collectionId = parseInt(document.getElementById("sr-collection-id").value);

  if (!name || !url) { showToast("Name and URL are required", "error"); return; }

  try {
    await apiPost("/api/collections/requests", {
      name, method, url, headers, body,
      query_params: "{}",
      collection_id: collectionId,
    });
    showToast("Request saved!", "success");
    closeModal("save-request-modal");
    loadCollections();
  } catch (err) {
    showToast("Failed: " + err.message, "error");
  }
}

async function deleteSavedRequest(requestId, collectionId) {
  if (!confirm("Delete this saved request?")) return;
  try {
    await apiDelete(`/api/collections/requests/${requestId}`);
    showToast("Request deleted", "success");
    loadCollections();
  } catch (err) {
    showToast("Failed: " + err.message, "error");
  }
}

async function executeRequest(requestId) {
  showToast("Executing request…", "success");
  try {
    const result = await apiPost(`/api/collections/requests/${requestId}/execute`, {});
    // Navigate to tester and show result
    navigateTo("tester");
    document.getElementById("response-body").textContent = prettyJSON(result.response_body);
    document.getElementById("response-headers").textContent = JSON.stringify(result.response_headers, null, 2);
    const statusClass = statusBadgeClass(result.status_code);
    document.getElementById("response-meta").innerHTML = `
      <span class="badge ${statusClass}">${result.status_code ?? "ERR"}</span>
      <span class="time-badge">${result.response_time_ms ? result.response_time_ms + " ms" : ""}</span>
    `;
  } catch (err) {
    showToast("Execution failed: " + err.message, "error");
  }
}

// ─── Monitoring ─────────────────────────────────────────────────────────────

async function loadMonitoring() {
  try {
    const endpoints = await apiGet("/api/monitoring/endpoints");
    const container = document.getElementById("monitoring-list");

    if (endpoints.length === 0) {
      container.innerHTML = `<div class="empty-state">No endpoints registered. Add one to start monitoring.</div>`;
      return;
    }

    container.innerHTML = endpoints.map(ep => {
      const lastCheck  = ep.last_check;
      const isUp       = lastCheck ? lastCheck.is_up : null;
      const cardClass  = isUp === null ? "unknown" : (isUp ? "up" : "down");
      const uptimePct  = ep.uptime_percentage ?? null;
      const fillClass  = uptimePct === null ? "" : (uptimePct >= 90 ? "" : uptimePct >= 70 ? "med" : "low");

      return `
        <div class="endpoint-card ${cardClass}">
          <div class="endpoint-header">
            <div>
              <div class="endpoint-name">
                <span class="status-dot dot-${cardClass}"></span>${escHtml(ep.name)}
              </div>
              <div class="endpoint-url">${escHtml(ep.url)}</div>
            </div>
            <span class="method-badge method-${ep.method}">${ep.method}</span>
          </div>

          <div class="uptime-bar-container">
            <div class="uptime-bar-label">
              <span>Uptime</span>
              <span>${uptimePct !== null ? uptimePct + "%" : "No checks yet"}</span>
            </div>
            <div class="uptime-bar">
              <div class="uptime-bar-fill ${fillClass}" style="width:${uptimePct ?? 0}%"></div>
            </div>
          </div>

          <div class="endpoint-stats">
            <span>Checks: ${ep.total_checks}</span>
            ${lastCheck ? `<span>Last: ${lastCheck.status_code ?? "ERR"}</span>` : ""}
            ${lastCheck?.response_time_ms ? `<span>${lastCheck.response_time_ms}ms</span>` : ""}
            ${lastCheck ? `<span>${formatDate(lastCheck.checked_at)}</span>` : ""}
          </div>

          <div class="endpoint-actions">
            <button class="btn btn-sm btn-primary" onclick="checkSingleEndpoint(${ep.id})">▶ Check Now</button>
            <button class="btn btn-sm btn-danger"  onclick="deleteEndpoint(${ep.id})">🗑 Remove</button>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    showToast("Failed to load monitoring data", "error");
  }
}

function showEndpointModal() {
  document.getElementById("ep-name").value   = "";
  document.getElementById("ep-url").value    = "";
  document.getElementById("ep-method").value = "GET";
  document.getElementById("ep-status").value = "200";
  document.getElementById("endpoint-modal").classList.remove("hidden");
}

async function saveEndpoint() {
  const name           = document.getElementById("ep-name").value.trim();
  const url            = document.getElementById("ep-url").value.trim();
  const method         = document.getElementById("ep-method").value;
  const expectedStatus = parseInt(document.getElementById("ep-status").value) || 200;

  if (!name || !url) { showToast("Name and URL are required", "error"); return; }

  try {
    await apiPost("/api/monitoring/endpoints", { name, url, method, expected_status: expectedStatus });
    showToast("Endpoint registered!", "success");
    closeModal("endpoint-modal");
    loadMonitoring();
  } catch (err) {
    showToast("Failed: " + err.message, "error");
  }
}

async function deleteEndpoint(id) {
  if (!confirm("Remove this endpoint from monitoring?")) return;
  try {
    await apiDelete(`/api/monitoring/endpoints/${id}`);
    showToast("Endpoint removed", "success");
    loadMonitoring();
  } catch (err) {
    showToast("Failed: " + err.message, "error");
  }
}

async function checkSingleEndpoint(id) {
  showToast("Checking endpoint…", "success");
  try {
    await apiPost(`/api/monitoring/endpoints/${id}/check`, {});
    showToast("Check complete!", "success");
    loadMonitoring();
  } catch (err) {
    showToast("Check failed: " + err.message, "error");
  }
}

async function checkAllEndpoints() {
  showToast("Checking all endpoints…", "success");
  try {
    const results = await apiPost("/api/monitoring/check-all", {});
    showToast(`Checked ${results.length} endpoint(s)`, "success");
    loadMonitoring();
  } catch (err) {
    showToast("Check failed: " + err.message, "error");
  }
}

// ─── History ────────────────────────────────────────────────────────────────

async function loadHistory() {
  const search = document.getElementById("history-search").value.trim();
  const method = document.getElementById("history-method-filter").value;

  let url = "/api/history/?limit=100";
  if (method) url += `&method=${method}`;
  if (search) url += `&search=${encodeURIComponent(search)}`;

  try {
    const history = await apiGet(url);
    const tbody   = document.getElementById("history-tbody");

    if (history.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty-state">No history found.</td></tr>`;
      return;
    }

    tbody.innerHTML = history.map(r => `
      <tr>
        <td><span class="method-badge method-${r.method}">${r.method}</span></td>
        <td style="font-family:var(--font-mono);font-size:.78rem;max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
            title="${escHtml(r.url)}">${escHtml(r.url)}</td>
        <td><span class="badge ${statusBadgeClass(r.status_code)}">${r.status_code ?? "ERR"}</span></td>
        <td style="font-family:var(--font-mono);">${r.response_time_ms ? r.response_time_ms + "" : "—"}</td>
        <td>${r.test_result ? `<span class="badge ${r.test_result === 'PASS' ? 'badge-success' : 'badge-error'}">${r.test_result}</span>` : "—"}</td>
        <td style="color:var(--text-secondary);font-size:.78rem;">${formatDate(r.timestamp)}</td>
        <td style="display:flex;gap:.4rem;">
          <button class="btn btn-sm btn-ghost" onclick="viewHistoryDetail(${r.id})">👁</button>
          <button class="btn btn-sm btn-danger" onclick="deleteHistory(${r.id})">🗑</button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    showToast("Failed to load history", "error");
  }
}

async function viewHistoryDetail(id) {
  try {
    const r = await apiGet(`/api/history/${id}`);
    const content = document.getElementById("history-detail-content");
    content.innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1rem;">
        <div><strong>Method:</strong> <span class="method-badge method-${r.method}">${r.method}</span></div>
        <div><strong>Status:</strong> <span class="badge ${statusBadgeClass(r.status_code)}">${r.status_code ?? "ERR"}</span></div>
        <div><strong>Response Time:</strong> ${r.response_time_ms ? r.response_time_ms + "ms" : "—"}</div>
        <div><strong>Timestamp:</strong> ${formatDate(r.timestamp)}</div>
      </div>
      <div style="margin-bottom:.75rem;">
        <strong>URL:</strong>
        <div style="font-family:var(--font-mono);font-size:.8rem;word-break:break-all;color:var(--accent);margin-top:.25rem;">${escHtml(r.url)}</div>
      </div>
      ${r.error_message ? `<div class="badge badge-error" style="margin-bottom:.75rem;">Error: ${escHtml(r.error_message)}</div>` : ""}
      <details style="margin-bottom:.75rem;">
        <summary style="cursor:pointer;color:var(--text-secondary);font-size:.85rem;">Response Body</summary>
        <pre style="background:var(--bg-base);border:1px solid var(--border);border-radius:4px;padding:.75rem;font-family:var(--font-mono);font-size:.75rem;overflow:auto;max-height:300px;margin-top:.5rem;">${escHtml(prettyJSON(r.response_body))}</pre>
      </details>
      <details>
        <summary style="cursor:pointer;color:var(--text-secondary);font-size:.85rem;">Response Headers</summary>
        <pre style="background:var(--bg-base);border:1px solid var(--border);border-radius:4px;padding:.75rem;font-family:var(--font-mono);font-size:.75rem;overflow:auto;max-height:200px;margin-top:.5rem;">${escHtml(r.response_headers)}</pre>
      </details>
    `;
    document.getElementById("history-detail-modal").classList.remove("hidden");
  } catch (err) {
    showToast("Failed to load detail", "error");
  }
}

async function deleteHistory(id) {
  try {
    await apiDelete(`/api/history/${id}`);
    showToast("Record deleted", "success");
    loadHistory();
  } catch (err) {
    showToast("Failed to delete", "error");
  }
}

async function clearHistory() {
  if (!confirm("Delete ALL request history? This cannot be undone.")) return;
  try {
    await apiDelete("/api/history/");
    showToast("History cleared", "success");
    loadHistory();
  } catch (err) {
    showToast("Failed to clear history", "error");
  }
}

// ─── Reports ────────────────────────────────────────────────────────────────

async function loadReportStats() {
  try {
    const data = await apiGet("/api/reports/summary");
    document.getElementById("rpt-total").textContent   = data.total_requests ?? 0;
    document.getElementById("rpt-success").textContent = data.successful_requests ?? 0;
    document.getElementById("rpt-failed").textContent  = data.failed_requests ?? 0;
    document.getElementById("rpt-avg").textContent     =
      data.average_response_time_ms != null ? `${data.average_response_time_ms}ms` : "—";
  } catch (err) {
    console.error("Failed to load report stats", err);
  }
}

// ─── Modal Utilities ─────────────────────────────────────────────────────────

function closeModal(id) {
  document.getElementById(id).classList.add("hidden");
}

// Close modal on overlay click
document.querySelectorAll(".modal-overlay").forEach(overlay => {
  overlay.addEventListener("click", e => {
    if (e.target === overlay) overlay.classList.add("hidden");
  });
});

// ─── Toast Notifications ─────────────────────────────────────────────────────

function showToast(message, type = "success") {
  const container = document.getElementById("toast-container") || createToastContainer();
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

function createToastContainer() {
  const el = document.createElement("div");
  el.id = "toast-container";
  el.className = "toast-container";
  document.body.appendChild(el);
  return el;
}

// ─── HTTP Helpers ─────────────────────────────────────────────────────────────

async function apiGet(path) {
  const res = await fetch(API_BASE + path);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetch(API_BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

async function apiPut(path, body) {
  const res = await fetch(API_BASE + path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function apiDelete(path) {
  const res = await fetch(API_BASE + path, { method: "DELETE" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ─── Formatting Helpers ───────────────────────────────────────────────────────

function prettyJSON(text) {
  if (!text) return "";
  try { return JSON.stringify(JSON.parse(text), null, 2); }
  catch { return text; }
}

function formatDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString();
}

function statusBadgeClass(code) {
  if (!code) return "badge-error";
  if (code >= 200 && code < 300) return "badge-success";
  if (code >= 300 && code < 400) return "badge-info";
  if (code >= 400 && code < 500) return "badge-warn";
  return "badge-error";
}

function escHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ─── Init ─────────────────────────────────────────────────────────────────────

loadDashboard();
