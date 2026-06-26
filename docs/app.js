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
      '<tr><td colspan="7" class="loading">⚠ 無法載入數據</td></tr>';
  }
}

async function saveData(updatedCompetitors, _message) {
  const json = {
    last_updated: updatedCompetitors.find(c => c.latest?.date)?.latest?.date || null,
    competitors: updatedCompetitors
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
  filterTable();
  if (json.keyword_rankings) renderKeywordRankings(json.keyword_rankings);
  if (json.gsc) renderGsc(json.gsc);
  if (json.gsc) document.getElementById("gscSection").style.display = "";
}

// ── Scrape trigger ────────────────────────────────────────────────────────────
async function triggerScrape() {
  if (!getToken()) { openSettings(); showToast("請先在設定填入 GitHub Token"); return; }
  const btn = document.querySelector(".btn-scrape");
  btn.disabled = true; btn.textContent = "⏳ 執行中…";
  try {
    const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`, {
      method: "POST",
      headers: { Authorization: `token ${getToken()}`, "Content-Type": "application/json" },
      body: JSON.stringify({ ref: "main" })
    });
    if (r.status === 204) {
      showToast("✓ 爬取已啟動！約需 5–15 分鐘，完成後數據自動更新");
      setTimeout(() => { btn.disabled = false; btn.textContent = "▶ 立即爬取"; }, 15000);
    } else {
      const body = await r.text().catch(() => "");
      throw new Error(`HTTP ${r.status}: ${body || "(no body)"}`);
    }
  } catch (e) {
    showToast("❌ 觸發失敗：" + e.message);
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
  if (!data.length) { tbody.innerHTML = '<tr><td colspan="7" class="loading">沒有符合的結果</td></tr>'; return; }
  tbody.innerHTML = data.map(d => {
    const l = d.latest || {};
    const idx = allData.indexOf(d);
    return `<tr>
      <td>
        <div class="comp-name"><a href="${d.url}" target="_blank">${d.name}</a></div>
        <div class="comp-url">${d.url||""}</div>
      </td>
      <td>${fmtTech(l.tech_stack)}</td>
      <td>${l.sitemap_pages!=null?`<span class="num">${l.sitemap_pages.toLocaleString()}</span>`:'<span class="na">N/A</span>'}</td>
      <td>${fmt(l.facebook_followers)}</td>
      <td>${fmt(l.linkedin_followers)}</td>
      <td>${l.date||'<span class="na">—</span>'}</td>
      <td style="display:flex;gap:4px;flex-wrap:wrap">
        <button class="btn-detail" onclick="openModal(${idx})">圖表</button>
        <button class="btn-edit" onclick="openEditModal(${idx})">編輯</button>
        <a class="btn-semrush" href="https://zh.semrush.com/analytics/overview/?q=${new URL(d.url).hostname}&db=us&searchType=domain" target="_blank">Semrush</a>
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
  const ok = await saveData(updated, "");
  if (ok) { allData = updated; filterTable(); closeEditModal(); showToast("✓ 已儲存"); }
}
async function deleteCompetitor() {
  if (editingIndex === null) return;
  const name = allData[editingIndex].name;
  if (!confirm(`確定要刪除「${name}」？`)) return;
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
}

function selectKwTab(kw) {
  activeKw = kw;
  document.querySelectorAll(".kw-tab").forEach(t =>
    t.classList.toggle("active", t.textContent === kw)
  );
  renderKwTable(kw);
}

function renderKwTable(kw) {
  const rows = kwData.results
    .filter(r => r.keyword === kw)
    .sort((a, b) => a.rank - b.rank);

  const tbody = document.getElementById("kwTableBody");
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="loading">此關鍵字無競爭對手出現在前 20 名</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(r => `
    <tr class="${r.is_own ? "own-site-row" : ""}">
      <td><span class="rank-badge${r.rank <= 3 ? " top3" : ""}">${r.rank}</span></td>
      <td>
        <span class="comp-name">${r.competitor}</span>
        ${r.is_own ? '<span class="own-badge">自己</span>' : ""}
      </td>
      <td><span class="kw-title">${r.title || "—"}</span></td>
      <td><a class="kw-url" href="${r.url}" target="_blank" title="${r.url}">${r.url}</a></td>
    </tr>
  `).join("");
}

window.selectKwTab = selectKwTab;

// ── Page switching ────────────────────────────────────────────────────────────
function showPage(page) {
  document.getElementById("pageCompetitors").style.display = page === "competitors" ? "" : "none";
  document.getElementById("pageGsc").style.display = page === "gsc" ? "" : "none";
  document.querySelectorAll(".page-tab").forEach(t =>
    t.classList.toggle("active", t.textContent.includes(page === "gsc" ? "Google" : "競爭對手"))
  );
}
window.showPage = showPage;

// ── GSC ───────────────────────────────────────────────────────────────────────
let gscData = null;
let activeGscSite = null;

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
  const entry = gscData.results.find(r => r.site === site);
  if (!entry) return;

  const fmtRow = (cols, isNA) => isNA
    ? `<tr><td colspan="${cols}" class="loading">無資料</td></tr>`
    : "";

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
    : fmtRow(5, true);

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
    : fmtRow(5, true);
}

window.selectGscTab = selectGscTab;

// ── Init ──────────────────────────────────────────────────────────────────────
loadData();
