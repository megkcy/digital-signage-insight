import { initializeApp } from "https://www.gstatic.com/firebasejs/12.15.0/firebase-app.js";
import { getFirestore, doc, getDoc, setDoc } from "https://www.gstatic.com/firebasejs/12.15.0/firebase-firestore.js";

const firebaseConfig = {
  apiKey: "AIzaSyBW3QGkqvw1fuLaDEd9t69oQU6-LTMG090",
  authDomain: "digital-signage-insight.firebaseapp.com",
  projectId: "digital-signage-insight",
  storageBucket: "digital-signage-insight.firebasestorage.app",
  messagingSenderId: "537464295756",
  appId: "1:537464295756:web:029092e4fd6a58baee7fe9"
};

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

const REPO = "megkcy/digital-signage-insight";
const WORKFLOW = "weekly_scrape.yml";

let allData = [];
let editingIndex = null;
let charts = {};

// ── GitHub Token (only needed for scrape trigger) ─────────────────────────────
function getToken() { return localStorage.getItem("gh_token") || ""; }

// ── Edit password gate (Firestore rules are fully open — this is just a
// speed bump against accidental edits, not real security) ─────────────────────
const EDIT_PASSWORD = "gocayin";
function checkEditPassword() {
  if (sessionStorage.getItem("edit_unlocked") === "1") return true;
  const pw = prompt("請輸入編輯密碼：");
  if (pw === null) return false;
  if (pw !== EDIT_PASSWORD) { showToast("❌ 密碼錯誤"); return false; }
  sessionStorage.setItem("edit_unlocked", "1");
  return true;
}

// ── Firestore ─────────────────────────────────────────────────────────────────
async function loadData() {
  try {
    const snap = await getDoc(doc(db, "insight", "data"));
    if (snap.exists()) {
      applyData(snap.data());
      return;
    }
  } catch (e) {
    console.warn("Firestore failed, falling back to data.json", e);
  }
  // fallback to local data.json
  try {
    const r = await fetch("data.json?t=" + Date.now());
    applyData(await r.json());
  } catch {
    document.getElementById("tableBody").innerHTML =
      '<tr><td colspan="8" class="loading">⚠ 無法載入數據</td></tr>';
  }
}

async function saveData(updatedCompetitors, _message) {
  // Read existing Firestore doc first so we don't wipe keyword_rankings / gsc / content_strategy
  let existing = {};
  try {
    const snap = await getDoc(doc(db, "insight", "data"));
    if (snap.exists()) existing = snap.data();
  } catch { /* ignore, will overwrite safely */ }
  const json = {
    ...existing,
    last_updated: updatedCompetitors.find(c => c.latest?.date)?.latest?.date || existing.last_updated || null,
    competitors: updatedCompetitors,
  };
  try {
    await setDoc(doc(db, "insight", "data"), json);
    return true;
  } catch (e) {
    showToast("❌ 儲存失敗：" + e.message);
    return false;
  }
}

function applyData(json) {
  document.getElementById("cardTotal").textContent = json.competitors.length;
  document.getElementById("cardLastScrape").textContent = json.last_updated || "未爬取";
  document.getElementById("statusBadge").textContent =
    `${json.competitors.length} 個對手 · 最後更新: ${json.last_updated || "—"}`;
  const fbCount = json.competitors.filter(c => c.latest?.facebook_followers != null).length;
  document.getElementById("cardSocial").textContent = fbCount;
  const liCount = json.competitors.filter(c => c.latest?.linkedin_followers != null).length;
  document.getElementById("cardLinkedin").textContent = liCount;
  allData = json.competitors;
  if (json.content_strategy) csData = json.content_strategy;
  if (json.seo_health) seoHealthData = json.seo_health;
  if (json.keyword_intel) renderKeywordIntel(json.keyword_intel);
  renderFreshness(json);
  filterTable();
  if (json.keyword_rankings) renderKeywordRankings(json.keyword_rankings);
  if (json.gsc) renderGsc(json.gsc);
  if (json.gsc) document.getElementById("gscSection").style.display = "";
  if (!json.gsc && json.seo_health) {
    // no GSC data but health audit exists — still show the section
    document.getElementById("gscSection").style.display = "";
    renderSeoHealth(json.seo_health.sites?.[0]?.site);
  }
}

// ── Data freshness ────────────────────────────────────────────────────────────
function renderFreshness(json) {
  const el = document.getElementById("freshnessRow");
  if (!el) return;

  // latest successful SerpAPI refresh across competitors (social + Google 收錄);
  // fall back to the newest history entry that actually has social data
  let serpDate = "";
  (json.competitors || []).forEach(c => {
    const d = c.latest?.serp_refreshed || "";
    if (d > serpDate) serpDate = d;
  });
  if (!serpDate) {
    (json.competitors || []).forEach(c => {
      (c.history || []).forEach(h => {
        if ((h.facebook_followers != null || h.google_indexed != null) && (h.date || "") > serpDate) {
          serpDate = h.date;
        }
      });
    });
  }

  const items = [
    ["關鍵字排名", json.keyword_rankings?.last_updated],
    ["內容策略", json.content_strategy?.last_updated],
    ["社群/Google收錄", serpDate],
    ["GSC", json.gsc?.last_updated],
    ["SEO健檢", json.seo_health?.last_updated],
    ["關鍵字情報", json.keyword_intel?.generated_at],
  ];

  const now = Date.now();
  el.innerHTML = items.map(([label, date]) => {
    let cls = "fresh-none", text = "無資料";
    if (date) {
      const days = Math.floor((now - new Date(date + "T00:00:00Z").getTime()) / 86400000);
      cls = days <= 14 ? "fresh-ok" : days <= 35 ? "fresh-warn" : "fresh-old";
      text = date;
    }
    return `<span class="fresh-chip ${cls}"><span class="fresh-dot"></span>${label} ${text}</span>`;
  }).join("");
}

// ── Workflow triggers ─────────────────────────────────────────────────────────
async function dispatchWorkflow(workflowFile, btn, idleText, successMsg, cooldownMs) {
  if (!getToken()) { openSettings(); showToast("請先在設定填入 GitHub Token"); return; }
  btn.disabled = true; btn.textContent = "⏳ 執行中…";
  try {
    const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${workflowFile}/dispatches`, {
      method: "POST",
      headers: { Authorization: `token ${getToken()}`, "Content-Type": "application/json" },
      body: JSON.stringify({ ref: "main" })
    });
    if (r.status === 204) {
      showToast(successMsg);
      setTimeout(() => { btn.disabled = false; btn.textContent = idleText; }, cooldownMs);
    } else {
      const body = await r.text().catch(() => "");
      throw new Error(`HTTP ${r.status}: ${body || "(no body)"}`);
    }
  } catch (e) {
    showToast("❌ 觸發失敗：" + e.message);
    btn.disabled = false; btn.textContent = idleText;
  }
}

function triggerScrape() {
  dispatchWorkflow(WORKFLOW, document.querySelector(".btn-scrape"),
    "▶ 立即爬取", "✓ 爬取已啟動！約需 5–15 分鐘，完成後數據自動更新", 15000);
}

function triggerSync() {
  dispatchWorkflow("restore_firestore.yml", document.getElementById("btnSync"),
    "⟳ 同步數據", "✓ 同步已啟動！約 1 分鐘後重新整理頁面即可看到最新數據", 60000);
}
window.triggerSync = triggerSync;

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

function fmtIndexed(n) {
  if (n == null) return '<span class="na">N/A</span>';
  if (n >= 1_000_000) return `<span class="num">${(n/1_000_000).toFixed(1)}M</span>`;
  if (n >= 1_000) return `<span class="num">${(n/1_000).toFixed(0)}K</span>`;
  return `<span class="num">${n.toLocaleString()}</span>`;
}

function safeHostname(url) {
  try { return new URL(url).hostname; } catch { return ""; }
}

// Country can hold multiple comma-separated values (Notion multi-select) —
// the table only has room for one, so show the first and hint the rest via title.
function firstCountry(country) {
  if (!country) return "";
  const parts = country.split(",").map(s => s.trim()).filter(Boolean);
  if (!parts.length) return "";
  return parts.length > 1
    ? `<span title="${country.replace(/"/g, "&quot;")}">${parts[0]} +${parts.length - 1}</span>`
    : parts[0];
}

function renderTable(data) {
  const tbody = document.getElementById("tableBody");
  if (!data.length) { tbody.innerHTML = '<tr><td colspan="9" class="loading">沒有符合的結果</td></tr>'; return; }
  tbody.innerHTML = data.map(d => {
    const l = d.latest || {};
    const idx = allData.indexOf(d);
    const host = safeHostname(d.url);
    return `<tr>
      <td>
        <div class="comp-name">${d.url ? `<a href="${d.url}" target="_blank">${d.name}</a>` : d.name}</div>
        <div class="comp-url">${d.url||""}</div>
      </td>
      <td class="td-country">${firstCountry(d.country) || '<span class="na">—</span>'}</td>
      <td>${fmtTech(l.tech_stack)}</td>
      <td>${l.sitemap_pages!=null?`<span class="num">${l.sitemap_pages.toLocaleString()}</span>`:'<span class="na">N/A</span>'}</td>
      <td>${fmtIndexed(l.google_indexed)}</td>
      <td>${fmt(l.facebook_followers)}</td>
      <td>${fmt(l.linkedin_followers)}</td>
      <td>${l.date||'<span class="na">—</span>'}</td>
      <td style="display:flex;gap:4px;flex-wrap:wrap">
        <button class="btn-detail" onclick="openModal(${idx})">圖表</button>
        <button class="btn-edit" onclick="openEditModal(${idx})">編輯</button>
        ${host ? `<a class="btn-semrush" href="https://zh.semrush.com/analytics/overview/?q=${host}&db=us&searchType=domain" target="_blank">Semrush</a>` : ""}
        ${host ? `<a class="btn-site" href="https://www.google.com/search?q=site:${host}" target="_blank">site:</a>` : ""}
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
    <div class="meta-item"><div class="label">網站頁數</div><div class="value">${l.sitemap_pages!=null?l.sitemap_pages.toLocaleString():"N/A"}</div></div>
    <div class="meta-item"><div class="label">LinkedIn</div><div class="value">${l.linkedin_followers!=null?l.linkedin_followers.toLocaleString():"N/A"}</div></div>
    <div class="meta-item" style="grid-column:1/-1"><div class="label">Tech Stack</div><div class="value" style="font-size:13px">${l.tech_stack||"N/A"}</div></div>
    ${l.meta_title?`<div class="meta-item" style="grid-column:1/-1"><div class="label">Page Title</div><div class="value" style="font-size:12px;font-weight:400">${l.meta_title}</div></div>`:""}
  `;
  renderModalAudit(l.seo_audit, comp.name);
  renderModalTargets(comp, l);
  renderModalKeywords(comp.name);
  document.getElementById("modal").classList.add("open");
  renderCharts(comp.history||[]);
}

function scoreClass(v) { return v >= 90 ? "score-good" : v >= 50 ? "score-mid" : "score-bad"; }
function scoreRing(label, v) {
  if (v == null) return "";
  const cls = scoreClass(v);
  return `<div class="score-ring ${cls}" style="--pct:${v}"><span class="score-num">${v}</span><span class="score-label">${label}</span></div>`;
}

let compareAudit = null;
let compareCompName = "";
let activeCompareSite = null;
let activeSubTab = "seo";

const SUB_METRICS = {
  seo: {
    title: "🔍 傳統 SEO 評分 詳細比較",
    rows: [
      ["performance", "Performance"],
      ["onpage", "On-Page SEO"],
      ["technical", "Technical SEO"],
      ["meta", "Meta Tags"],
      ["mobile", "Mobile 友善"],
      ["speed", "頁面速度"],
    ],
  },
  geo: {
    title: "🤖 AI 搜尋 GEO 評分 詳細比較",
    rows: [
      ["citable", "AI 可引用性"],
      ["ai_open", "AI 爬蟲開放度"],
      ["schema", "Schema 完整性"],
      ["eeat", "E-E-A-T 專業度"],
      ["brand", "品牌權威"],
      ["platform", "平台優化 (llms.txt)"],
    ],
  },
  aeo: {
    title: "💬 AEO 答案引擎評分 詳細比較",
    rows: [
      ["answer", "答案段落最佳化"],
      ["faq", "FAQ 結構化"],
      ["snippet", "Featured Snippet 就緒度"],
      ["howto", "HowTo 結構"],
      ["qhead", "問題式標題"],
      ["paa", "PAA 友善度"],
    ],
  },
};

function _overall(s) {
  const vals = [s.seo, s.aeo, s.geo].filter(v => v != null);
  return vals.length ? Math.round(vals.reduce((a, b) => a + b, 0) / vals.length) : null;
}

function _ownScores(siteName) {
  const site = (seoHealthData?.sites || []).find(s => s.site === siteName);
  if (!site) return null;
  const psi = site.psi || {};
  return {
    seo: site.seo?.score ?? null, aeo: site.aeo?.score ?? null, geo: site.geo?.score ?? null,
    performance: psi.performance ?? null, accessibility: psi.accessibility ?? null, best_practices: psi.best_practices ?? null,
  };
}

function _compScores(audit) {
  const psi = audit?.psi || {};
  return {
    seo: audit?.seo_score ?? null, aeo: audit?.aeo_score ?? null, geo: audit?.geo_score ?? null,
    performance: psi.performance ?? null, accessibility: psi.accessibility ?? null, best_practices: psi.best_practices ?? null,
  };
}

function _vsRow(label, own, comp, bold) {
  const fmt = v => v == null ? '<span class="na">—</span>' : v;
  const ownWin = own != null && comp != null && own > comp;
  const compWin = own != null && comp != null && comp > own;
  return `<tr class="${bold ? "vs-total-row" : ""}">
    <td class="vs-label">${label}</td>
    <td class="vs-val ${ownWin ? "vs-win" : ""}">${fmt(own)}${ownWin ? " ⭐" : ""}</td>
    <td class="vs-val ${compWin ? "vs-win" : ""}">${fmt(comp)}${compWin ? " ⭐" : ""}</td>
  </tr>`;
}

function renderModalAudit(audit, compName) {
  const el = document.getElementById("modalAudit");
  if (!el) return;
  compareAudit = audit;
  compareCompName = compName || "";

  const ownSites = (seoHealthData?.sites || []).map(s => s.site);
  if (!audit && !ownSites.length) {
    el.innerHTML = `<h3 class="modal-kw-title">SEO 比較</h3><div class="modal-kw-empty">尚無體檢數據，下次爬取後顯示</div>`;
    return;
  }
  if (!activeCompareSite || !ownSites.includes(activeCompareSite)) activeCompareSite = ownSites[0] || null;

  const own = activeCompareSite ? _ownScores(activeCompareSite) : null;
  const comp = _compScores(audit);
  const ownOverall = own ? _overall(own) : null;
  const compOverall = audit ? _overall(comp) : null;

  const pills = ownSites.length > 1 ? `
    <div class="vs-site-pills">${ownSites.map(s =>
      `<button class="kw-tab ${s === activeCompareSite ? "active" : ""}" onclick="selectCompareSite('${s.replace(/'/g, "\\'")}')">${s}</button>`
    ).join("")}</div>` : "";

  const rows = [
    _vsRow("綜合分數", ownOverall, compOverall, true),
    _vsRow("🔍 SEO 搜尋引擎優化", own?.seo ?? null, comp.seo),
    _vsRow("💬 AEO 答案引擎優化", own?.aeo ?? null, comp.aeo),
    _vsRow("🤖 GEO AI 搜尋優化", own?.geo ?? null, comp.geo),
    _vsRow("⚡ 效能 (Lighthouse)", own?.performance ?? null, comp.performance),
    _vsRow("♿ 無障礙", own?.accessibility ?? null, comp.accessibility),
    _vsRow("✅ 最佳實踐", own?.best_practices ?? null, comp.best_practices),
  ].join("");

  // Detailed sub-metric comparison (SEO / GEO / AEO tabs)
  const ownSite = activeCompareSite ? (seoHealthData?.sites || []).find(s => s.site === activeCompareSite) : null;
  const ownSubs = ownSite?.subs || null;
  const compSubs = audit?.subs || null;
  let subsHtml = "";
  if (ownSubs || compSubs) {
    const conf = SUB_METRICS[activeSubTab];
    const subTabs = Object.keys(SUB_METRICS).map(k =>
      `<button class="kw-tab sub-tab ${k === activeSubTab ? "active" : ""}" onclick="selectSubTab('${k}')">${{seo: "🔍 SEO", geo: "🤖 GEO", aeo: "💬 AEO"}[k]}</button>`
    ).join("");
    const subRows = conf.rows.map(([key, label]) =>
      _vsRow(label, ownSubs?.[activeSubTab]?.[key] ?? null, compSubs?.[activeSubTab]?.[key] ?? null)
    ).join("");
    subsHtml = `
      <div class="vs-site-pills sub-tab-row">${subTabs}</div>
      <div class="vs-sub-title">${conf.title}</div>
      <div class="table-wrap vs-wrap">
        <table class="vs-table">
          <thead><tr>
            <th>指標</th>
            <th>${activeCompareSite || "自家網站"} <span class="vs-you-badge">你</span></th>
            <th>${compareCompName}</th>
          </tr></thead>
          <tbody>${subRows}</tbody>
        </table>
      </div>`;
  }

  const notes = [];
  if (!own) notes.push("自家網站健檢尚未產生（下次每週爬取後顯示）");
  if (!audit) notes.push(`${compareCompName} 的體檢尚未產生（下次月度爬取後顯示）`);
  if ((own || audit) && !ownSubs && !compSubs) notes.push("細項評分將在下次爬取後顯示");

  const checks = Object.entries(audit?.checks || {}).map(([label, ok]) =>
    `<span class="audit-chip ${ok ? "chip-pass" : "chip-fail"}">${ok ? "✓" : "✗"} ${label}</span>`
  ).join("");
  const schema = (audit?.schema_types || []).map(t => `<span class="pill pill-purple">${t}</span>`).join(" ");

  el.innerHTML = `
    <h3 class="modal-kw-title">SEO 評分比較</h3>
    ${pills}
    <div class="table-wrap vs-wrap">
      <table class="vs-table">
        <thead><tr>
          <th>指標</th>
          <th>${activeCompareSite || "自家網站"} <span class="vs-you-badge">你</span></th>
          <th>${compareCompName}</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
    ${subsHtml}
    ${notes.map(n => `<div class="modal-kw-empty">${n}</div>`).join("")}
    ${checks ? `<div class="audit-chips-title">${compareCompName} 站內檢查</div><div class="audit-chips">${checks}</div>` : ""}
    ${schema ? `<div class="audit-schema"><span class="audit-schema-label">結構化資料：</span>${schema}</div>` : ""}
  `;
}

window.selectCompareSite = (site) => {
  activeCompareSite = site;
  renderModalAudit(compareAudit, compareCompName);
};

window.selectSubTab = (tab) => {
  activeSubTab = tab;
  renderModalAudit(compareAudit, compareCompName);
};

function renderModalTargets(comp, l) {
  const el = document.getElementById("modalTargets");
  if (!el) return;
  const host = safeHostname(comp.url);
  const kws = l.target_keywords || [];
  const ads = l.ads_transparency;

  const kwHtml = kws.length ? `
    <h3 class="modal-kw-title">🎯 推測目標關鍵字 <span class="target-hint">（由網站頁面網址結構分析）</span></h3>
    <div class="target-kw-chips">
      ${kws.map(k => `<span class="target-kw-chip">${k.phrase}<span class="target-kw-count">${k.pages} 頁</span></span>`).join("")}
    </div>` : "";

  const FMT_ZH = { text: "文字", image: "圖片", video: "影片", unknown: "其他" };
  let adsHtml = "";
  if (ads) {
    const detail = ads.total > 0
      ? `${ads.total}+ 則廣告素材${ads.formats ? "（" + Object.entries(ads.formats).map(([f, n]) => `${FMT_ZH[f] || f} ${n}`).join("、") + "）" : ""}${ads.last_shown ? `，最近投放：${ads.last_shown}` : ""}`
      : "目前未偵測到 Google 廣告投放";
    adsHtml = `
      <h3 class="modal-kw-title">📢 Google 廣告投放</h3>
      <div class="ads-summary ${ads.total > 0 ? "ads-active" : ""}">${detail}
        <a class="btn-kw-action" style="margin-left:8px" target="_blank"
           href="https://adstransparency.google.com/?region=anywhere&domain=${host}">查看廣告 ↗</a>
      </div>`;
  } else if (host) {
    adsHtml = `
      <h3 class="modal-kw-title">📢 Google 廣告投放</h3>
      <div class="ads-summary">數據將於下次爬取產生
        <a class="btn-kw-action" style="margin-left:8px" target="_blank"
           href="https://adstransparency.google.com/?region=anywhere&domain=${host}">先手動查看 ↗</a>
      </div>`;
  }

  el.innerHTML = kwHtml + adsHtml;
}

function renderModalKeywords(name) {
  const el = document.getElementById("modalKw");
  if (!el) return;
  const rows = (kwData?.results || [])
    .filter(r => r.competitor === name)
    .sort((a, b) => a.rank - b.rank);
  const csEntries = (csData?.results || []).filter(r => r.competitor === name);
  if (!rows.length && !csEntries.length) {
    el.innerHTML = `
      <h3 class="modal-kw-title">關鍵字排名</h3>
      <div class="modal-kw-empty">未進入追蹤關鍵字（${(kwData?.keywords || []).join("、") || "—"}）前 20 名</div>`;
    return;
  }
  const kwHtml = rows.map(r => `
    <div class="modal-kw-row">
      <span class="rank-badge${r.rank <= 3 ? " top3" : ""}">${r.rank}</span>
      <span class="modal-kw-keyword">${r.keyword}</span>
      <a class="modal-kw-page" href="${r.url}" target="_blank" title="${r.title || r.url}">${r.title || r.url}</a>
    </div>`).join("");
  const csHtml = csEntries.map(e => `
    <div class="modal-cs-block">
      <div class="modal-cs-kw">「${e.keyword}」熱門內容</div>
      ${e.pages.slice(0, 3).map(p => `<a class="modal-kw-page" href="${p.url}" target="_blank">${p.title || p.url}</a>`).join("")}
    </div>`).join("");
  el.innerHTML = `
    <h3 class="modal-kw-title">關鍵字排名</h3>
    ${kwHtml || '<div class="modal-kw-empty">未進入前 20 名</div>'}
    ${csHtml}`;
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
  charts.facebook = new Chart(document.getElementById("chartTrends"), { type:"line", options:opts, data:{ labels, datasets:[{ label:"Facebook", data:history.map(r=>r.facebook_followers), borderColor:"#1877f2", backgroundColor:"rgba(24,119,242,.1)", tension:.4, fill:true, pointRadius:4 }] } });
  charts.pages = new Chart(document.getElementById("chartPages"), { type:"line", options:opts, data:{ labels, datasets:[{ label:"頁數", data:history.map(r=>r.sitemap_pages), borderColor:"#16a34a", backgroundColor:"rgba(22,163,74,.1)", tension:.4, fill:true, pointRadius:4 }] } });
  charts.social = new Chart(document.getElementById("chartSocial"), { type:"line", options:opts, data:{ labels, datasets:[
    { label:"LinkedIn", data:history.map(r=>r.linkedin_followers), borderColor:"#0a66c2", backgroundColor:"rgba(10,102,194,.1)", tension:.4, fill:true, pointRadius:4 },
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
  document.getElementById("fCountry").value = d.country || "";
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
  if (!checkEditPassword()) return;
  const entry = {
    name: document.getElementById("fName").value.trim(),
    url: document.getElementById("fUrl").value.trim(),
    country: document.getElementById("fCountry").value.trim(),
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
  const ok = await saveData(updated, "");
  if (ok) { allData = updated; filterTable(); closeEditModal(); showToast("✓ 已儲存"); }
}
async function deleteCompetitor() {
  if (editingIndex === null) return;
  const name = allData[editingIndex].name;
  if (!confirm(`確定要刪除「${name}」？`)) return;
  if (!checkEditPassword()) return;
  const updated = allData.filter((_, i) => i !== editingIndex);
  const ok = await saveData(updated, "");
  if (ok) { allData = updated; filterTable(); closeEditModal(); showToast("✓ 已刪除"); }
}

// ── Settings modal (GitHub Token for scrape trigger only) ─────────────────────
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
  if (t) { localStorage.setItem("gh_token", t); showToast("✓ Token 已儲存"); closeSettings(); }
  else { localStorage.removeItem("gh_token"); showToast("Token 已清除"); }
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function showToast(msg) {
  const t = document.createElement("div");
  t.className = "toast"; t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

// ── Expose to HTML onclick handlers ──────────────────────────────────────────
window.filterTable = filterTable;
window.openModal = openModal;
window.closeModal = closeModal;
window.openEditModal = openEditModal;
window.closeEditModal = closeEditModal;
window.openAddModal = openAddModal;
window.saveCompetitor = saveCompetitor;
window.deleteCompetitor = deleteCompetitor;
window.triggerScrape = triggerScrape;
window.openSettings = openSettings;
window.closeSettings = closeSettings;
window.saveToken = saveToken;

// ── Keyword Rankings ─────────────────────────────────────────────────────────
let kwData = null;
let activeKw = null;
let csData = null;

function renderKeywordRankings(rankings) {
  if (!rankings || !rankings.results || !rankings.results.length) return;
  kwData = rankings;
  document.getElementById("kwSection").style.display = "";
  document.getElementById("kwUpdated").textContent = `更新：${rankings.last_updated || "—"}`;

  const tabs = document.getElementById("kwTabs");
  tabs.innerHTML = rankings.keywords.map((kw, i) =>
    `<button class="kw-tab${i === 0 ? " active" : ""}" onclick="selectKwTab('${kw}')">${kw}</button>`
  ).join("");

  activeKw = rankings.keywords[0];
  renderKwTable(activeKw);
  renderKwTrend(activeKw);
  renderContentStrategy(activeKw);
}

function selectKwTab(kw) {
  activeKw = kw;
  document.querySelectorAll(".kw-tab").forEach(t =>
    t.classList.toggle("active", t.textContent === kw)
  );
  renderKwTable(kw);
  renderKwTrend(kw);
  renderContentStrategy(kw);
}

// ── Rank trend chart ─────────────────────────────────────────────────────────
let kwTrendChart = null;
const TREND_COLORS = ["#7c3aed", "#0a66c2", "#16a34a", "#d97706", "#dc2626",
                      "#0891b2", "#be185d", "#65a30d", "#7e22ce", "#b45309"];

function renderKwTrend(kw) {
  const wrap = document.getElementById("kwTrend");
  if (!wrap || typeof Chart === "undefined") return;
  const history = kwData?.history || [];
  if (history.length < 2) { wrap.style.display = "none"; return; }

  const dates = history.map(h => h.date);
  // collect every competitor that ever ranked for this keyword
  const names = [];
  history.forEach(h => (h.results || []).forEach(r => {
    if (r.keyword === kw && !names.includes(r.competitor)) names.push(r.competitor);
  }));
  if (!names.length) { wrap.style.display = "none"; return; }

  const ownNames = new Set();
  history.forEach(h => (h.results || []).forEach(r => { if (r.is_own) ownNames.add(r.competitor); }));

  const datasets = names.map((name, i) => {
    const data = history.map(h => {
      const hit = (h.results || []).find(r => r.keyword === kw && r.competitor === name);
      return hit ? hit.rank : null;
    });
    const own = ownNames.has(name);
    const color = own ? "#4f6ef7" : TREND_COLORS[i % TREND_COLORS.length];
    return {
      label: own ? `${name}（自己）` : name,
      data,
      borderColor: color,
      backgroundColor: color,
      borderWidth: own ? 3 : 2,
      tension: .3,
      spanGaps: true,
      pointRadius: 4,
    };
  });

  wrap.style.display = "";
  if (kwTrendChart) { kwTrendChart.destroy(); kwTrendChart = null; }
  kwTrendChart = new Chart(document.getElementById("kwTrendChart"), {
    type: "line",
    data: { labels: dates, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#6b7280", font: { size: 11 } } } },
      scales: {
        x: { ticks: { color: "#6b7280", font: { size: 10 } }, grid: { color: "#f0f2f5" } },
        y: {
          reverse: true,
          min: 1,
          ticks: { color: "#6b7280", font: { size: 10 }, stepSize: 1, precision: 0 },
          grid: { color: "#f0f2f5" },
          title: { display: true, text: "排名", color: "#6b7280", font: { size: 10 } },
        },
      },
    },
  });
}

function renderKwTable(kw) {
  const rows = kwData.results
    .filter(r => r.keyword === kw)
    .sort((a, b) => a.rank - b.rank);

  // Ranking gap
  const ownRows = rows.filter(r => r.is_own);
  const compRows = rows.filter(r => !r.is_own);
  const ownRank = ownRows.length ? ownRows[0].rank : null;
  const topCompRank = compRows.length ? compRows[0].rank : null;
  let gapHtml = "";
  if (rows.length) {
    const ownLabel = ownRank != null
      ? `<span class="gap-own">自己最高：第 ${ownRank} 名</span>`
      : `<span class="gap-none">自己未進前 20</span>`;
    const compLabel = topCompRank != null
      ? `<span class="gap-comp">競爭對手最高：第 ${topCompRank} 名</span>`
      : "";
    let diffLabel = "";
    if (ownRank != null && topCompRank != null) {
      const diff = ownRank - topCompRank;
      const cls = diff > 0 ? "gap-behind" : diff < 0 ? "gap-ahead" : "gap-even";
      diffLabel = `<span class="gap-diff ${cls}">差距：${diff > 0 ? "+" : ""}${diff}</span>`;
    }
    const parts = [ownLabel, compLabel, diffLabel].filter(Boolean);
    gapHtml = `<div class="kw-gap">${parts.join('<span class="gap-sep">｜</span>')}</div>`;
  }
  document.getElementById("kwGap").innerHTML = gapHtml;

  const tbody = document.getElementById("kwTableBody");
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="5" class="loading">此關鍵字無競爭對手出現在前 20 名</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(r => {
    let domain = "";
    try { domain = new URL(r.url).hostname; } catch { domain = r.url; }
    const encUrl = encodeURIComponent(r.url);
    const encKw = encodeURIComponent(kw);
    return `
      <tr class="${r.is_own ? "own-site-row" : ""}">
        <td><span class="rank-badge${r.rank <= 3 ? " top3" : ""}">${r.rank}</span></td>
        <td>
          <span class="comp-name">${r.competitor}</span>
          ${r.is_own ? '<span class="own-badge">自己</span>' : ""}
        </td>
        <td><span class="kw-title">${r.title || "—"}</span></td>
        <td><a class="kw-url" href="${r.url}" target="_blank" title="${r.url}">${r.url}</a></td>
        <td class="kw-actions">
          <a href="https://ahrefs.com/backlink-checker/?target=${encUrl}" target="_blank" class="btn-kw-action btn-ahrefs">Ahrefs</a>
          <a href="https://moz.com/link-explorer/analysis?target=${encUrl}" target="_blank" class="btn-kw-action btn-moz">Moz</a>
          <a href="https://www.google.com/search?q=site:${domain}" target="_blank" class="btn-kw-action">site:</a>
          <a href="https://www.google.com/search?q=site:${domain}+${encKw}" target="_blank" class="btn-kw-action">內容策略</a>
        </td>
      </tr>
    `;
  }).join("");
}

function renderContentStrategy(kw) {
  const section = document.getElementById("csSection");
  if (!section) return;
  if (!csData || !csData.results || !csData.results.length) { section.innerHTML = ""; return; }
  const entries = csData.results.filter(r => r.keyword === kw);
  if (!entries.length) { section.innerHTML = ""; return; }
  section.innerHTML = `
    <h3 class="cs-title">競爭對手內容策略：「${kw}」</h3>
    <div class="cs-grid">
      ${entries.map(e => `
        <div class="cs-card">
          <div class="cs-card-header">
            <span class="cs-comp-name">${e.competitor}</span>
            <span class="cs-domain">${e.domain}</span>
          </div>
          <div class="cs-pages">
            ${e.pages.map((p, i) => `
              <div class="cs-page">
                <span class="cs-page-num">${i + 1}</span>
                <div class="cs-page-info">
                  <a class="cs-page-title" href="${p.url}" target="_blank">${p.title || p.url}</a>
                  ${p.snippet ? `<div class="cs-snippet">${p.snippet}</div>` : ""}
                </div>
              </div>
            `).join("")}
          </div>
        </div>
      `).join("")}
    </div>
  `;
}

window.selectKwTab = selectKwTab;

// ── Page switching ────────────────────────────────────────────────────────────
const PAGE_LABELS = { competitors: "競爭對手", gsc: "Google", keywordIntel: "關鍵字情報" };
function showPage(page) {
  document.getElementById("pageCompetitors").style.display = page === "competitors" ? "" : "none";
  document.getElementById("pageGsc").style.display = page === "gsc" ? "" : "none";
  document.getElementById("pageKeywordIntel").style.display = page === "keywordIntel" ? "" : "none";
  document.querySelectorAll(".page-tab").forEach(t =>
    t.classList.toggle("active", t.textContent.includes(PAGE_LABELS[page]))
  );
}
window.showPage = showPage;

// ── GSC ───────────────────────────────────────────────────────────────────────
let gscData = null;
let activeGscSite = null;
let seoHealthData = null;
let activePsiStrategy = "mobile";

function selectPsiStrategy(strategy) {
  activePsiStrategy = strategy;
  renderSeoHealth(activeGscSite);
}
window.selectPsiStrategy = selectPsiStrategy;

function renderSeoHealth(site) {
  const el = document.getElementById("seoHealth");
  if (!el) return;
  const entry = (seoHealthData?.sites || []).find(s => s.site === site);
  if (!entry) { el.innerHTML = ""; return; }

  const hasDesktop = !!entry.psi_desktop;
  const strategy = hasDesktop ? activePsiStrategy : "mobile";
  const psi = (strategy === "desktop" ? entry.psi_desktop : entry.psi) || {};
  const psiToggle = hasDesktop ? `
    <div class="kw-tabs">
      <button class="kw-tab ${strategy === "mobile" ? "active" : ""}" onclick="selectPsiStrategy('mobile')">📱 Mobile</button>
      <button class="kw-tab ${strategy === "desktop" ? "active" : ""}" onclick="selectPsiStrategy('desktop')">💻 Desktop</button>
    </div>` : "";
  const rings = [
    scoreRing("SEO", entry.seo?.score),
    scoreRing("AEO", entry.aeo?.score),
    scoreRing("GEO", entry.geo?.score),
    scoreRing("效能", psi.performance),
    scoreRing("無障礙", psi.accessibility),
    scoreRing("最佳實踐", psi.best_practices),
  ].filter(Boolean).join("");

  const DESC = {
    seo: ["SEO 搜尋引擎優化", "傳統 Google 搜尋排名的技術基礎"],
    aeo: ["AEO 答案引擎優化", "精選摘要與問答框（People Also Ask）曝光"],
    geo: ["GEO 生成式引擎優化", "讓 ChatGPT / Claude / Perplexity 等 AI 搜尋引用你的內容"],
  };
  const cols = ["seo", "aeo", "geo"].map(k => {
    const sec = entry[k];
    if (!sec) return "";
    const fails = sec.items.filter(i => !i.pass);
    const passes = sec.items.filter(i => i.pass);
    return `
      <div class="health-card">
        <div class="health-card-head">
          <span class="health-title">${DESC[k][0]}</span>
          <span class="health-score ${scoreClass(sec.score)}">${sec.score}</span>
        </div>
        <div class="health-sub">${DESC[k][1]}</div>
        ${fails.map(i => `
          <div class="health-item item-fail">
            <div class="health-item-label">✗ ${i.label}</div>
            <div class="health-advice">${i.advice || ""}</div>
          </div>`).join("")}
        ${passes.map(i => `<div class="health-item item-pass">✓ ${i.label}</div>`).join("")}
      </div>`;
  }).join("");

  const warn = entry.unreliable ? `
    <div class="health-warn">⚠ 此網站對爬蟲回傳的內容不完整（可能為 JS 渲染），站內檢查項目僅供參考——Lighthouse 分數（效能/無障礙等）仍為 Google 實測、可信。</div>` : "";

  el.innerHTML = `
    ${psiToggle}
    <div class="health-rings">${rings}</div>
    ${warn}
    <div class="health-grid">${cols}</div>
  `;
}

function renderGsc(gsc) {
  if (!gsc || !gsc.results || !gsc.results.length) return;
  gscData = gsc;
  document.getElementById("gscUpdated").textContent = `更新：${gsc.last_updated || "—"}`;

  const sites = gsc.results.map(r => r.site);
  const tabs = document.getElementById("gscTabs");
  tabs.innerHTML = sites.map((s, i) =>
    `<button class="kw-tab${i === 0 ? " active" : ""}" onclick="selectGscTab('${s}')">${s}</button>`
  ).join("");

  activeGscSite = sites[0];
  renderGscTables(activeGscSite);
}

function selectGscTab(site) {
  activeGscSite = site;
  document.querySelectorAll("#gscTabs .kw-tab").forEach(t =>
    t.classList.toggle("active", t.textContent === site)
  );
  renderGscTables(site);
}

const COUNTRY_NAMES = {
  afg:"阿富汗 Afghanistan", alb:"阿爾巴尼亞 Albania", dza:"阿爾及利亞 Algeria",
  and:"安道爾 Andorra", ago:"安哥拉 Angola", arg:"阿根廷 Argentina",
  arm:"亞美尼亞 Armenia", aus:"澳大利亞 Australia", aut:"奧地利 Austria",
  aze:"亞塞拜然 Azerbaijan", bhs:"巴哈馬 Bahamas", bhr:"巴林 Bahrain",
  bgd:"孟加拉 Bangladesh", blr:"白俄羅斯 Belarus", bel:"比利時 Belgium",
  biz:"伯利茲 Belize", ben:"貝南 Benin", btn:"不丹 Bhutan",
  bol:"玻利維亞 Bolivia", bih:"波士尼亞赫塞哥維納 Bosnia and Herzegovina",
  bwa:"波札那 Botswana", bra:"巴西 Brazil", brn:"汶萊 Brunei",
  bgr:"保加利亞 Bulgaria", bfa:"布吉納法索 Burkina Faso", bdi:"蒲隆地 Burundi",
  cpv:"維德角 Cape Verde", khm:"柬埔寨 Cambodia", cmr:"喀麥隆 Cameroon",
  can:"加拿大 Canada", caf:"中非共和國 Central African Republic",
  tcd:"查德 Chad", chl:"智利 Chile", chn:"中國 China",
  col:"哥倫比亞 Colombia", cog:"剛果共和國 Congo", cod:"剛果民主共和國 DR Congo",
  cri:"哥斯大黎加 Costa Rica", hrv:"克羅埃西亞 Croatia", cub:"古巴 Cuba",
  cyp:"賽普勒斯 Cyprus", cze:"捷克 Czech Republic", dnk:"丹麥 Denmark",
  dom:"多明尼加 Dominican Republic", ecu:"厄瓜多 Ecuador", egy:"埃及 Egypt",
  slv:"薩爾瓦多 El Salvador", est:"愛沙尼亞 Estonia", eth:"衣索比亞 Ethiopia",
  fin:"芬蘭 Finland", fra:"法國 France", geo:"喬治亞 Georgia",
  deu:"德國 Germany", gha:"迦納 Ghana", grc:"希臘 Greece",
  gtm:"瓜地馬拉 Guatemala", hnd:"宏都拉斯 Honduras", hkg:"香港 Hong Kong",
  hun:"匈牙利 Hungary", isl:"冰島 Iceland", ind:"印度 India",
  idn:"印尼 Indonesia", irn:"伊朗 Iran", irq:"伊拉克 Iraq",
  irl:"愛爾蘭 Ireland", isr:"以色列 Israel", ita:"義大利 Italy",
  jam:"牙買加 Jamaica", jpn:"日本 Japan", jor:"約旦 Jordan",
  kaz:"哈薩克 Kazakhstan", ken:"肯亞 Kenya", kwt:"科威特 Kuwait",
  kgz:"吉爾吉斯 Kyrgyzstan", lao:"寮國 Laos", lva:"拉脫維亞 Latvia",
  lbn:"黎巴嫩 Lebanon", lby:"利比亞 Libya", ltu:"立陶宛 Lithuania",
  lux:"盧森堡 Luxembourg", mys:"馬來西亞 Malaysia", mdv:"馬爾地夫 Maldives",
  mlt:"馬爾他 Malta", mex:"墨西哥 Mexico", mda:"摩爾多瓦 Moldova",
  mng:"蒙古 Mongolia", mar:"摩洛哥 Morocco", moz:"莫三比克 Mozambique",
  mmr:"緬甸 Myanmar", nam:"納米比亞 Namibia", npl:"尼泊爾 Nepal",
  nld:"荷蘭 Netherlands", nzl:"紐西蘭 New Zealand", nic:"尼加拉瓜 Nicaragua",
  nga:"奈及利亞 Nigeria", nor:"挪威 Norway", omn:"阿曼 Oman",
  pak:"巴基斯坦 Pakistan", pan:"巴拿馬 Panama", pry:"巴拉圭 Paraguay",
  per:"秘魯 Peru", phl:"菲律賓 Philippines", pol:"波蘭 Poland",
  prt:"葡萄牙 Portugal", qat:"卡達 Qatar", rou:"羅馬尼亞 Romania",
  rus:"俄羅斯 Russia", sau:"沙烏地阿拉伯 Saudi Arabia", sen:"塞內加爾 Senegal",
  srb:"塞爾維亞 Serbia", sgp:"新加坡 Singapore", svk:"斯洛伐克 Slovakia",
  svn:"斯洛維尼亞 Slovenia", som:"索馬利亞 Somalia", zaf:"南非 South Africa",
  kor:"南韓 South Korea", esp:"西班牙 Spain", lka:"斯里蘭卡 Sri Lanka",
  sdn:"蘇丹 Sudan", swe:"瑞典 Sweden", che:"瑞士 Switzerland",
  syr:"敘利亞 Syria", twn:"台灣 Taiwan", tjk:"塔吉克 Tajikistan",
  tza:"坦尚尼亞 Tanzania", tha:"泰國 Thailand", tun:"突尼西亞 Tunisia",
  tur:"土耳其 Turkey", tkm:"土庫曼 Turkmenistan", uga:"烏干達 Uganda",
  ukr:"烏克蘭 Ukraine", are:"阿聯酋 United Arab Emirates",
  gbr:"英國 United Kingdom", usa:"美國 United States",
  ury:"烏拉圭 Uruguay", uzb:"烏茲別克 Uzbekistan", ven:"委內瑞拉 Venezuela",
  vnm:"越南 Vietnam", yem:"葉門 Yemen", zmb:"尚比亞 Zambia",
  zwe:"辛巴威 Zimbabwe",
};

function formatCountry(code) {
  if (!code) return code;
  const key = code.toLowerCase();
  return COUNTRY_NAMES[key] || code;
}

function renderGscTables(site) {
  renderSeoHealth(site);
  const entry = gscData.results.find(r => r.site === site);
  if (!entry) return;

  // Queries
  const qBody = document.getElementById("gscQueryBody");
  qBody.innerHTML = entry.queries?.length
    ? entry.queries.map(r => `
        <tr>
          <td><span class="comp-name">${r.query}</span></td>
          <td><span class="num">${r.clicks.toLocaleString()}</span></td>
          <td><span class="num">${r.impressions.toLocaleString()}</span></td>
          <td><span class="pill pill-blue">${r.ctr}%</span></td>
          <td><span class="rank-badge${r.position <= 3 ? " top3" : ""}">${r.position}</span></td>
        </tr>`).join("")
    : kiEmptyRow();

  // Countries
  const cBody = document.getElementById("gscCountryBody");
  cBody.innerHTML = entry.countries?.length
    ? entry.countries.map(r => `
        <tr>
          <td><span class="comp-name">${formatCountry(r.country)}</span></td>
          <td><span class="num">${r.clicks.toLocaleString()}</span></td>
          <td><span class="num">${r.impressions.toLocaleString()}</span></td>
          <td><span class="pill pill-blue">${r.ctr}%</span></td>
          <td><span class="rank-badge${r.position <= 3 ? " top3" : ""}">${r.position}</span></td>
        </tr>`).join("")
    : kiEmptyRow();
}

window.selectGscTab = selectGscTab;

// ── Keyword Intelligence ──────────────────────────────────────────────────────
let kiData = null;

function kiEmptyRow() {
  return '<tr><td colspan="5" class="loading">無資料</td></tr>';
}

function kiRow(r, freqCol) {
  const bidLow = r.bid_low != null ? r.bid_low.toFixed(0) : "0";
  const bidHigh = r.bid_high != null ? r.bid_high.toFixed(0) : "0";
  const freqCell = `<span class="num">${r.seen}/${kiData.n_exports}</span>`;
  return freqCol === "first"
    ? `<tr>
        <td><span class="comp-name">${r.keyword}</span></td>
        <td><span class="num">${r.volume.toLocaleString()}</span></td>
        <td>${freqCell}</td>
        <td><span class="pill pill-purple">${r.competition}</span></td>
        <td><span class="na">NT$${bidLow}–${bidHigh}</span></td>
      </tr>`
    : `<tr>
        <td><span class="comp-name">${r.keyword}</span></td>
        <td>${freqCell}</td>
        <td><span class="num">${r.volume.toLocaleString()}</span></td>
        <td><span class="pill pill-purple">${r.competition}</span></td>
        <td><span class="na">NT$${bidLow}–${bidHigh}</span></td>
      </tr>`;
}

function renderKeywordIntel(data) {
  kiData = data;
  document.getElementById("kiTotal").textContent = data.total_unique?.toLocaleString() || "—";
  document.getElementById("kiGap").textContent = data.gap?.length || 0;
  document.getElementById("kiSources").textContent = `${data.n_exports} 個對手網站 · ${data.generated_at || ""}`;

  const findingEl = document.getElementById("kiFinding");
  const subEl = document.getElementById("kiFindingSub");
  if (data.gap?.length) {
    findingEl.style.display = "";
    subEl.textContent = `機會缺口表：在 2 個以上對手網站同時出現、且月搜尋量 ≥150、自家完全沒有曝光的字，依搜尋量排序。必爭字表：不論搜尋量高低，在 ${data.n_exports} 個對手網站中最多共同鎖定的字，依出現次數排序。`;
  }

  document.getElementById("kiGapBody").innerHTML =
    (data.gap || []).map(r => kiRow(r, "first")).join("") || kiEmptyRow();
  document.getElementById("kiCommonBody").innerHTML =
    (data.top_common || []).map(r => kiRow(r, "second")).join("") || kiEmptyRow();
  document.getElementById("kiOverallBody").innerHTML =
    (data.overall_top || []).map(r => kiRow(r, "first")).join("") || kiEmptyRow();
}

function filterKiTable(which) {
  if (!kiData) return;
  const map = {
    gap: ["kiGapSearch", "kiGapBody", kiData.gap, "first"],
    common: ["kiCommonSearch", "kiCommonBody", kiData.top_common, "second"],
    overall: ["kiOverallSearch", "kiOverallBody", kiData.overall_top, "first"],
  };
  const [searchId, bodyId, rows, freqCol] = map[which];
  const q = document.getElementById(searchId).value.trim().toLowerCase();
  const filtered = (rows || []).filter(r => r.keyword.toLowerCase().includes(q));
  document.getElementById(bodyId).innerHTML = filtered.map(r => kiRow(r, freqCol)).join("") || kiEmptyRow();
}
window.filterKiTable = filterKiTable;

// ── Init ──────────────────────────────────────────────────────────────────────
loadData();
