const API = "http://localhost:8000";

let allData = [];
let charts = {};

// ── Format helpers ────────────────────────────────────────────────────────────
function fmt(n) {
  if (n == null) return '<span class="na">N/A</span>';
  if (n >= 1_000_000) return `<span class="num num-big">${(n / 1_000_000).toFixed(1)}M</span>`;
  if (n >= 1_000) return `<span class="num num-big">${(n / 1_000).toFixed(1)}K</span>`;
  return `<span class="num num-big">${n.toLocaleString()}</span>`;
}

function fmtPR(v) {
  if (v == null) return '<span class="na">N/A</span>';
  return `<span class="pill pill-blue">${parseFloat(v).toFixed(2)}</span>`;
}

function fmtDate(d) {
  if (!d) return '<span class="na">—</span>';
  return d;
}

function fmtTech(t) {
  if (!t || t === "Unknown") return '<span class="na">—</span>';
  return t.split(", ").map(s => `<span class="pill pill-purple">${s}</span>`).join(" ");
}

// ── Load data ─────────────────────────────────────────────────────────────────
async function loadStatus() {
  try {
    const r = await fetch(`${API}/api/status`);
    const d = await r.json();
    document.getElementById("cardTotal").textContent = d.competitors;
    document.getElementById("cardLastScrape").textContent = d.last_scrape || "未爬取";
    document.getElementById("cardSeo").textContent = d.seo_snapshots;
    document.getElementById("cardSocial").textContent = d.social_snapshots;
    document.getElementById("statusBadge").textContent =
      `${d.competitors} 個對手 · 最後更新: ${d.last_scrape || "—"}`;
  } catch {
    document.getElementById("statusBadge").textContent = "無法連接後端";
  }
}

async function loadSnapshots() {
  try {
    const r = await fetch(`${API}/api/snapshots`);
    allData = await r.json();
    filterTable();
  } catch {
    document.getElementById("tableBody").innerHTML =
      '<tr><td colspan="10" class="loading">⚠ 無法連接後端，請確認 server 已啟動</td></tr>';
  }
}

// ── Table ─────────────────────────────────────────────────────────────────────
function filterTable() {
  const q = document.getElementById("search").value.toLowerCase();
  const sortBy = document.getElementById("sortBy").value;
  const dir = document.getElementById("sortDir").value;

  let data = allData.filter(d => d.name.toLowerCase().includes(q) || (d.url || "").includes(q));

  data.sort((a, b) => {
    let av = a[sortBy] ?? -Infinity;
    let bv = b[sortBy] ?? -Infinity;
    if (typeof av === "string") return dir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
    return dir === "asc" ? av - bv : bv - av;
  });

  renderTable(data);
}

function renderTable(data) {
  const tbody = document.getElementById("tableBody");
  if (!data.length) {
    tbody.innerHTML = '<tr><td colspan="10" class="loading">沒有符合的結果</td></tr>';
    return;
  }

  tbody.innerHTML = data.map(d => `
    <tr>
      <td>
        <div class="comp-name">${d.name}</div>
        <div class="comp-url">${d.url || ""}</div>
      </td>
      <td>${fmtPR(d.open_pagerank)}</td>
      <td>${fmtTech(d.tech_stack)}</td>
      <td>${d.sitemap_pages != null ? `<span class="num">${d.sitemap_pages.toLocaleString()}</span>` : '<span class="na">N/A</span>'}</td>
      <td>${fmt(d.facebook_followers)}</td>
      <td>${fmt(d.instagram_followers)}</td>
      <td>${fmt(d.x_followers)}</td>
      <td>${fmt(d.linkedin_followers)}</td>
      <td>${fmtDate(d.seo_date || d.social_date)}</td>
      <td><button class="btn-detail" onclick="openModal(${d.id})">詳細</button></td>
    </tr>
  `).join("");
}

// ── Modal ─────────────────────────────────────────────────────────────────────
async function openModal(id) {
  const comp = allData.find(d => d.id === id);
  if (!comp) return;

  document.getElementById("modalTitle").textContent = comp.name;
  const urlEl = document.getElementById("modalUrl");
  urlEl.textContent = comp.url || "";
  urlEl.href = comp.url || "#";

  document.getElementById("modalMeta").innerHTML = `
    <div class="meta-item"><div class="label">PageRank</div><div class="value">${comp.open_pagerank != null ? parseFloat(comp.open_pagerank).toFixed(2) : "N/A"}</div></div>
    <div class="meta-item"><div class="label">網站頁數</div><div class="value">${comp.sitemap_pages != null ? comp.sitemap_pages.toLocaleString() : "N/A"}</div></div>
    <div class="meta-item"><div class="label">Facebook</div><div class="value">${comp.facebook_followers != null ? comp.facebook_followers.toLocaleString() : "N/A"}</div></div>
    <div class="meta-item"><div class="label">Instagram</div><div class="value">${comp.instagram_followers != null ? comp.instagram_followers.toLocaleString() : "N/A"}</div></div>
    <div class="meta-item"><div class="label">X (Twitter)</div><div class="value">${comp.x_followers != null ? comp.x_followers.toLocaleString() : "N/A"}</div></div>
    <div class="meta-item"><div class="label">LinkedIn</div><div class="value">${comp.linkedin_followers != null ? comp.linkedin_followers.toLocaleString() : "N/A"}</div></div>
    <div class="meta-item" style="grid-column:1/-1"><div class="label">Tech Stack</div><div class="value" style="font-size:13px">${comp.tech_stack || "N/A"}</div></div>
    ${comp.meta_title ? `<div class="meta-item" style="grid-column:1/-1"><div class="label">Page Title</div><div class="value" style="font-size:13px">${comp.meta_title}</div></div>` : ""}
  `;

  document.getElementById("modal").classList.add("open");

  // Load history charts
  try {
    const r = await fetch(`${API}/api/history/${id}`);
    const h = await r.json();
    renderCharts(h);
  } catch {
    ["chartPagerank", "chartSocial", "chartPages"].forEach(id => {
      const canvas = document.getElementById(id);
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    });
  }
}

function closeModal(e) {
  if (e && e.target !== document.getElementById("modal")) return;
  document.getElementById("modal").classList.remove("open");
  Object.values(charts).forEach(c => c.destroy());
  charts = {};
}

function renderCharts(h) {
  Object.values(charts).forEach(c => c.destroy());
  charts = {};

  const seoLabels = h.seo.map(r => r.snapshot_date);
  const socialLabels = h.social.map(r => r.snapshot_date);

  const chartDefaults = {
    type: "line",
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: "#7b82a0", font: { size: 11 } } } },
      scales: {
        x: { ticks: { color: "#7b82a0", font: { size: 10 } }, grid: { color: "#2e3250" } },
        y: { ticks: { color: "#7b82a0", font: { size: 10 } }, grid: { color: "#2e3250" } },
      },
    },
  };

  charts.pagerank = new Chart(document.getElementById("chartPagerank"), {
    ...chartDefaults,
    data: {
      labels: seoLabels,
      datasets: [{
        label: "PageRank",
        data: h.seo.map(r => r.open_pagerank),
        borderColor: "#4f6ef7",
        backgroundColor: "rgba(79,110,247,.1)",
        tension: .4, fill: true, pointRadius: 4,
      }],
    },
  });

  charts.pages = new Chart(document.getElementById("chartPages"), {
    ...chartDefaults,
    data: {
      labels: seoLabels,
      datasets: [{
        label: "頁數",
        data: h.seo.map(r => r.sitemap_pages),
        borderColor: "#22c55e",
        backgroundColor: "rgba(34,197,94,.1)",
        tension: .4, fill: true, pointRadius: 4,
      }],
    },
  });

  charts.social = new Chart(document.getElementById("chartSocial"), {
    ...chartDefaults,
    data: {
      labels: socialLabels,
      datasets: [
        {
          label: "Facebook",
          data: h.social.map(r => r.facebook_followers),
          borderColor: "#3b82f6", tension: .4, pointRadius: 4,
        },
        {
          label: "Instagram",
          data: h.social.map(r => r.instagram_followers),
          borderColor: "#ec4899", tension: .4, pointRadius: 4,
        },
        {
          label: "X",
          data: h.social.map(r => r.x_followers),
          borderColor: "#a3a3a3", tension: .4, pointRadius: 4,
        },
      ],
    },
  });
}

// ── Scrape trigger ────────────────────────────────────────────────────────────
async function triggerScrape() {
  const btn = document.getElementById("btnScrape");
  btn.disabled = true;
  btn.textContent = "⏳ 爬取中…";
  showToast("爬取已開始，這可能需要幾分鐘");

  try {
    await fetch(`${API}/api/scrape`, { method: "POST" });
    setTimeout(async () => {
      await Promise.all([loadStatus(), loadSnapshots()]);
      btn.disabled = false;
      btn.textContent = "▶ 立即爬取";
      showToast("✓ 爬取完成");
    }, 5000);
  } catch {
    btn.disabled = false;
    btn.textContent = "▶ 立即爬取";
    showToast("⚠ 爬取失敗，請確認後端已啟動");
  }
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function showToast(msg) {
  const t = document.createElement("div");
  t.className = "toast";
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

// ── Init ──────────────────────────────────────────────────────────────────────
loadStatus();
loadSnapshots();
