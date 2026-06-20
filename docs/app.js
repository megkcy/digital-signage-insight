const REPO = "megkcy/digital-signage-insight";
const DATA_PATH = "docs/data.json";
const WORKFLOW = "weekly_scrape.yml";

let allData = [];
let fileSha = null;
let editingIndex = null;
let charts = {};

// ── GitHub API ────────────────────────────────────────────────────────────────
function getToken() { return localStorage.getItem("gh_token") || ""; }

async function loadData() {
  try {
    const r = await fetch(`https://api.github.com/repos/${REPO}/contents/${DATA_PATH}`, {
      headers: getToken() ? { Authorization: `token ${getToken()}` } : {}
    });
    const file = await r.json();
    fileSha = file.sha;
    const json = JSON.parse(atob(file.content.replace(/\n/g, "")));
    applyData(json);
  } catch {
    try {
      const r = await fetch("data.json?t=" + Date.now());
      applyData(await r.json());
    } catch {
      document.getElementById("tableBody").innerHTML =
        '<tr><td colspan="10" class="loading">⚠ 無法載入數據</td></tr>';
    }
  }
}

function applyData(json) {
  document.getElementById("cardTotal").textContent = json.competitors.length;
  document.getElementById("cardLastScrape").textContent = json.last_updated || "未爬取";
  document.getElementById("statusBadge").textContent =
    `${json.competitors.length} 個對手 · 最後更新: ${json.last_updated || "—"}`;
  const seoCount = json.competitors.filter(c => c.latest?.open_pagerank != null).length;
  const socialCount = json.competitors.filter(c => c.latest?.facebook_followers != null).length;
  document.getElementById("cardSeo").textContent = seoCount;
  document.getElementById("cardSocial").textContent = socialCount;
  allData = json.competitors;
  filterTable();
}

async function saveData(updatedCompetitors, message) {
  if (!getToken()) { openSettings(); showToast("請先設定 GitHub Token"); return false; }
  const json = {
    last_updated: updatedCompetitors.find(c => c.latest?.date)?.latest?.date || null,
    competitors: updatedCompetitors
  };
  const content = btoa(unescape(encodeURIComponent(JSON.stringify(json, null, 2))));
  const r = await fetch(`https://api.github.com/repos/${REPO}/contents/${DATA_PATH}`, {
    method: "PUT",
    headers: { Authorization: `token ${getToken()}`, "Content-Type": "application/json" },
    body: JSON.stringify({ message, content, sha: fileSha })
  });
  if (!r.ok) { showToast("❌ 儲存失敗，請確認 Token 有 repo 權限"); return false; }
  const res = await r.json();
  fileSha = res.content.sha;
  return true;
}

// ── Scrape trigger ────────────────────────────────────────────────────────────
async function triggerScrape() {
  if (!getToken()) { openSettings(); showToast("請先設定 GitHub Token"); return; }
  const btn = document.querySelector(".btn-scrape");
  btn.disabled = true; btn.textContent = "⏳ 執行中…";
  const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`, {
    method: "POST",
    headers: { Authorization: `token ${getToken()}`, "Content-Type": "application/json" },
    body: JSON.stringify({ ref: "main" })
  });
  if (r.status === 204) {
    showToast("✓ 爬取已啟動！約需 5-15 分鐘，完成後數據自動更新");
    setTimeout(() => { btn.disabled = false; btn.textContent = "▶ 立即爬取"; }, 10000);
  } else {
    showToast("❌ 觸發失敗，請確認 Token 有 workflow 權限");
    btn.disabled = false; btn.textContent = "▶ 立即爬取";
  }
}

// ── Table ─────────────────────────────────────────────────────────────────────
function fmt(n) {
  if (n == null) return '<span class="na">N/A</span>';
  if (n >= 1_000_000) return `<span class="num">${(n/1_000_000).toFixed(1)}M</span>`;
  if (n >= 1_000) return `<span class="num">${(n/1_000).toFixed(1)}K</span>`;
  return `<span class="num">${n.toLocaleString()}</span>`;
}
function fmtPR(v) {
  if (v == null) return '<span class="na">N/A</span>';
  return `<span class="pill pill-blue">${parseFloat(v).toFixed(2)}</span>`;
}
function fmtTech(t) {
  if (!t) return '<span class="na">—</span>';
  return t.split(", ").map(s => `<span class="pill pill-purple">${s}</span>`).join(" ");
}

function filterTable() {
  const q = document.getElementById("search").value.toLowerCase();
  const sortBy = document.getElementById("sortBy").value;
  const dir = document.getElementById("sortDir").value;
  let data = allData.filter(d => d.name.toLowerCase().includes(q) || (d.url||"").includes(q));
  data.sort((a, b) => {
    const av = sortBy === "name" ? a.name : (a.latest?.[sortBy] ?? -Infinity);
    const bv = sortBy === "name" ? b.name : (b.latest?.[sortBy] ?? -Infinity);
    if (typeof av === "string") return dir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
    return dir === "asc" ? av - bv : bv - av;
  });
  renderTable(data);
}

function renderTable(data) {
  const tbody = document.getElementById("tableBody");
  if (!data.length) { tbody.innerHTML = '<tr><td colspan="10" class="loading">沒有符合的結果</td></tr>'; return; }
  tbody.innerHTML = data.map(d => {
    const l = d.latest || {};
    const idx = allData.indexOf(d);
    return `<tr>
      <td>
        <div class="comp-name"><a href="${d.url}" target="_blank">${d.name}</a></div>
        <div class="comp-url">${d.url||""}</div>
      </td>
      <td>${fmtPR(l.open_pagerank)}</td>
      <td>${fmtTech(l.tech_stack)}</td>
      <td>${l.sitemap_pages!=null?`<span class="num">${l.sitemap_pages.toLocaleString()}</span>`:'<span class="na">N/A</span>'}</td>
      <td>${fmt(l.facebook_followers)}</td>
      <td>${fmt(l.instagram_followers)}</td>
      <td>${fmt(l.x_followers)}</td>
      <td>${fmt(l.linkedin_followers)}</td>
      <td>${l.date||'<span class="na">—</span>'}</td>
      <td style="display:flex;gap:4px">
        <button class="btn-detail" onclick="openModal(${idx})">圖表</button>
        <button class="btn-edit" onclick="openEditModal(${idx})">編輯</button>
      </td>
    </tr>`;
  }).join("");
}

// ── Detail / chart modal ──────────────────────────────────────────────────────
function openModal(idx) {
  const comp = allData[idx]; if (!comp) return;
  const l = comp.latest || {};
  document.getElementById("modalTitle").textContent = comp.name;
  const urlEl = document.getElementById("modalUrl");
  urlEl.textContent = comp.url||""; urlEl.href = comp.url||"#";
  document.getElementById("modalMeta").innerHTML = `
    <div class="meta-item"><div class="label">PageRank</div><div class="value">${l.open_pagerank!=null?parseFloat(l.open_pagerank).toFixed(2):"N/A"}</div></div>
    <div class="meta-item"><div class="label">網站頁數</div><div class="value">${l.sitemap_pages!=null?l.sitemap_pages.toLocaleString():"N/A"}</div></div>
    <div class="meta-item"><div class="label">Facebook</div><div class="value">${l.facebook_followers!=null?l.facebook_followers.toLocaleString():"N/A"}</div></div>
    <div class="meta-item"><div class="label">Instagram</div><div class="value">${l.instagram_followers!=null?l.instagram_followers.toLocaleString():"N/A"}</div></div>
    <div class="meta-item"><div class="label">X (Twitter)</div><div class="value">${l.x_followers!=null?l.x_followers.toLocaleString():"N/A"}</div></div>
    <div class="meta-item"><div class="label">LinkedIn</div><div class="value">${l.linkedin_followers!=null?l.linkedin_followers.toLocaleString():"N/A"}</div></div>
    <div class="meta-item" style="grid-column:1/-1"><div class="label">Tech Stack</div><div class="value" style="font-size:13px">${l.tech_stack||"N/A"}</div></div>
    ${l.meta_title?`<div class="meta-item" style="grid-column:1/-1"><div class="label">Page Title</div><div class="value" style="font-size:12px;font-weight:400">${l.meta_title}</div></div>`:""}
  `;
  document.getElementById("modal").classList.add("open");
  renderCharts(comp.history||[]);
}
function closeModal(e) {
  if (e && e.target !== document.getElementById("modal")) return;
  document.getElementById("modal").classList.remove("open");
  Object.values(charts).forEach(c => c.destroy()); charts = {};
}
function renderCharts(history) {
  Object.values(charts).forEach(c => c.destroy()); charts = {};
  const labels = history.map(r => r.date);
  const opts = { responsive:true, plugins:{ legend:{ labels:{ color:"#6b7280", font:{size:11} } } }, scales:{ x:{ticks:{color:"#6b7280",font:{size:10}},grid:{color:"#f0f2f5"}}, y:{ticks:{color:"#6b7280",font:{size:10}},grid:{color:"#f0f2f5"}} } };
  charts.pagerank = new Chart(document.getElementById("chartPagerank"), { type:"line", options:opts, data:{ labels, datasets:[{ label:"PageRank", data:history.map(r=>r.open_pagerank), borderColor:"#4f6ef7", backgroundColor:"rgba(79,110,247,.1)", tension:.4, fill:true, pointRadius:4 }] } });
  charts.pages = new Chart(document.getElementById("chartPages"), { type:"line", options:opts, data:{ labels, datasets:[{ label:"頁數", data:history.map(r=>r.sitemap_pages), borderColor:"#16a34a", backgroundColor:"rgba(22,163,74,.1)", tension:.4, fill:true, pointRadius:4 }] } });
  charts.social = new Chart(document.getElementById("chartSocial"), { type:"line", options:opts, data:{ labels, datasets:[
    { label:"Facebook", data:history.map(r=>r.facebook_followers), borderColor:"#3b82f6", tension:.4, pointRadius:4 },
    { label:"Instagram", data:history.map(r=>r.instagram_followers), borderColor:"#ec4899", tension:.4, pointRadius:4 },
    { label:"X", data:history.map(r=>r.x_followers), borderColor:"#6b7280", tension:.4, pointRadius:4 },
  ] } });
}

// ── Add / Edit modal ──────────────────────────────────────────────────────────
function openAddModal() {
  editingIndex = null;
  document.getElementById("editModalTitle").textContent = "新增競爭對手";
  document.getElementById("editForm").reset();
  document.getElementById("btnDelete").style.display = "none";
  document.getElementById("editModal").classList.add("open");
}
function openEditModal(idx) {
  editingIndex = idx;
  const d = allData[idx];
  document.getElementById("editModalTitle").textContent = "編輯：" + d.name;
  document.getElementById("fName").value = d.name || "";
  document.getElementById("fUrl").value = d.url || "";
  document.getElementById("fFacebook").value = d.handles?.facebook || "";
  document.getElementById("fInstagram").value = d.handles?.instagram || "";
  document.getElementById("fX").value = d.handles?.x || "";
  document.getElementById("fLinkedin").value = d.handles?.linkedin || "";
  document.getElementById("btnDelete").style.display = "inline-block";
  document.getElementById("editModal").classList.add("open");
}
function closeEditModal(e) {
  if (e && e.target !== document.getElementById("editModal")) return;
  document.getElementById("editModal").classList.remove("open");
}
async function saveCompetitor(e) {
  e.preventDefault();
  const entry = {
    name: document.getElementById("fName").value.trim(),
    url: document.getElementById("fUrl").value.trim(),
    handles: {
      facebook: document.getElementById("fFacebook").value.trim(),
      instagram: document.getElementById("fInstagram").value.trim(),
      x: document.getElementById("fX").value.trim(),
      linkedin: document.getElementById("fLinkedin").value.trim(),
    },
    latest: editingIndex !== null ? (allData[editingIndex].latest || {}) : {},
    history: editingIndex !== null ? (allData[editingIndex].history || []) : [],
  };
  const updated = [...allData];
  if (editingIndex !== null) updated[editingIndex] = entry;
  else updated.push(entry);
  updated.sort((a, b) => a.name.localeCompare(b.name));
  showToast("儲存中…");
  const ok = await saveData(updated, editingIndex !== null ? `update: ${entry.name}` : `add: ${entry.name}`);
  if (ok) { allData = updated; filterTable(); closeEditModal(); showToast("✓ 已儲存"); }
}
async function deleteCompetitor() {
  if (editingIndex === null) return;
  const name = allData[editingIndex].name;
  if (!confirm(`確定要刪除「${name}」？`)) return;
  const updated = allData.filter((_, i) => i !== editingIndex);
  const ok = await saveData(updated, `remove: ${name}`);
  if (ok) { allData = updated; filterTable(); closeEditModal(); showToast("✓ 已刪除"); }
}

// ── Settings modal ────────────────────────────────────────────────────────────
function openSettings() {
  document.getElementById("ghToken").value = getToken();
  document.getElementById("settingsModal").classList.add("open");
}
function closeSettings(e) {
  if (e && e.target !== document.getElementById("settingsModal")) return;
  document.getElementById("settingsModal").classList.remove("open");
}
function saveToken() {
  const t = document.getElementById("ghToken").value.trim();
  if (t) { localStorage.setItem("gh_token", t); showToast("✓ Token 已儲存"); closeSettings(); loadData(); }
  else { localStorage.removeItem("gh_token"); showToast("Token 已清除"); }
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function showToast(msg) {
  const t = document.createElement("div");
  t.className = "toast"; t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

// ── Init ──────────────────────────────────────────────────────────────────────
loadData();
if (!getToken()) setTimeout(() => showToast("💡 點右上角 ⚙ 設定 GitHub Token 以啟用編輯和爬取功能"), 2000);
