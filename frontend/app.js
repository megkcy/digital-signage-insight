let allData = [];
let charts = {};

// ── Format helpers ────────────────────────────────────────────────────────────
function fmt(n) {
  if (n == null) return '<span class="na">N/A</span>';
  if (n >= 1_000_000) return `<span class="num">${(n / 1_000_000).toFixed(1)}M</span>`;
  if (n >= 1_000) return `<span class="num">${(n / 1_000).toFixed(1)}K</span>`;
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

// ── Load data ─────────────────────────────────────────────────────────────────
async function loadData() {
  try {
    const r = await fetch("data.json?t=" + Date.now());
    const json = await r.json();

    document.getElementById("cardTotal").textContent = json.competitors.length;
    document.getElementById("cardLastScrape").textContent = json.last_updated || "—";
    document.getElementById("statusBadge").textContent =
      `${json.competitors.length} 個對手 · 最後更新: ${json.last_updated || "—"}`;

    const seoCount = json.competitors.filter(c => c.latest?.open_pagerank != null).length;
    const socialCount = json.competitors.filter(c => c.latest?.facebook_followers != null).length;
    document.getElementById("cardSeo").textContent = seoCount;
    document.getElementById("cardSocial").textContent = socialCount;

    allData = json.competitors;
    filterTable();
  } catch {
    document.getElementById("tableBody").innerHTML =
      '<tr><td colspan="10" class="loading">⚠ 尚無數據，請等待 GitHub Actions 第一次執行（每週一）</td></tr>';
    document.getElementById("statusBadge").textContent = "尚無數據";
  }
}

// ── Table ─────────────────────────────────────────────────────────────────────
function filterTable() {
  const q = document.getElementById("search").value.toLowerCase();
  const sortBy = document.getElementById("sortBy").value;
  const dir = document.getElementById("sortDir").value;

  let data = allData.filter(d =>
    d.name.toLowerCase().includes(q) || (d.url || "").includes(q)
  );

  data.sort((a, b) => {
    const av = a.latest?.[sortBy] ?? (sortBy === "name" ? a.name : -Infinity);
    const bv = b.latest?.[sortBy] ?? (sortBy === "name" ? b.name : -Infinity);
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

  tbody.innerHTML = data.map((d, idx) => {
    const l = d.latest || {};
    return `
    <tr>
      <td>
        <div class="comp-name"><a href="${d.url}" target="_blank">${d.name}</a></div>
        <div class="comp-url">${d.url || ""}</div>
      </td>
      <td>${fmtPR(l.open_pagerank)}</td>
      <td>${fmtTech(l.tech_stack)}</td>
      <td>${l.sitemap_pages != null ? `<span class="num">${l.sitemap_pages.toLocaleString()}</span>` : '<span class="na">N/A</span>'}</td>
      <td>${fmt(l.facebook_followers)}</td>
      <td>${fmt(l.instagram_followers)}</td>
      <td>${fmt(l.x_followers)}</td>
      <td>${fmt(l.linkedin_followers)}</td>
      <td>${l.date || '<span class="na">—</span>'}</td>
      <td><button class="btn-detail" onclick="openModal(${idx})">詳細</button></td>
    </tr>`;
  }).join("");
}

// ── Modal ─────────────────────────────────────────────────────────────────────
function openModal(idx) {
  const comp = allData[idx];
  if (!comp) return;
  const l = comp.latest || {};

  document.getElementById("modalTitle").textContent = comp.name;
  const urlEl = document.getElementById("modalUrl");
  urlEl.textContent = comp.url || "";
  urlEl.href = comp.url || "#";

  document.getElementById("modalMeta").innerHTML = `
    <div class="meta-item"><div class="label">PageRank</div><div class="value">${l.open_pagerank != null ? parseFloat(l.open_pagerank).toFixed(2) : "N/A"}</div></div>
    <div class="meta-item"><div class="label">網站頁數</div><div class="value">${l.sitemap_pages != null ? l.sitemap_pages.toLocaleString() : "N/A"}</div></div>
    <div class="meta-item"><div class="label">Facebook</div><div class="value">${l.facebook_followers != null ? l.facebook_followers.toLocaleString() : "N/A"}</div></div>
    <div class="meta-item"><div class="label">Instagram</div><div class="value">${l.instagram_followers != null ? l.instagram_followers.toLocaleString() : "N/A"}</div></div>
    <div class="meta-item"><div class="label">X (Twitter)</div><div class="value">${l.x_followers != null ? l.x_followers.toLocaleString() : "N/A"}</div></div>
    <div class="meta-item"><div class="label">LinkedIn</div><div class="value">${l.linkedin_followers != null ? l.linkedin_followers.toLocaleString() : "N/A"}</div></div>
    <div class="meta-item" style="grid-column:1/-1"><div class="label">Tech Stack</div><div class="value" style="font-size:13px">${l.tech_stack || "N/A"}</div></div>
    ${l.meta_title ? `<div class="meta-item" style="grid-column:1/-1"><div class="label">Page Title</div><div class="value" style="font-size:12px;font-weight:400">${l.meta_title}</div></div>` : ""}
  `;

  document.getElementById("modal").classList.add("open");
  renderCharts(comp.history || []);
}

function closeModal(e) {
  if (e && e.target !== document.getElementById("modal")) return;
  document.getElementById("modal").classList.remove("open");
  Object.values(charts).forEach(c => c.destroy());
  charts = {};
}

function renderCharts(history) {
  Object.values(charts).forEach(c => c.destroy());
  charts = {};

  const labels = history.map(r => r.date);
  const base = {
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
    ...base,
    data: {
      labels,
      datasets: [{ label: "PageRank", data: history.map(r => r.open_pagerank), borderColor: "#4f6ef7", backgroundColor: "rgba(79,110,247,.1)", tension: .4, fill: true, pointRadius: 4 }],
    },
  });

  charts.pages = new Chart(document.getElementById("chartPages"), {
    ...base,
    data: {
      labels,
      datasets: [{ label: "頁數", data: history.map(r => r.sitemap_pages), borderColor: "#22c55e", backgroundColor: "rgba(34,197,94,.1)", tension: .4, fill: true, pointRadius: 4 }],
    },
  });

  charts.social = new Chart(document.getElementById("chartSocial"), {
    ...base,
    data: {
      labels,
      datasets: [
        { label: "Facebook", data: history.map(r => r.facebook_followers), borderColor: "#3b82f6", tension: .4, pointRadius: 4 },
        { label: "Instagram", data: history.map(r => r.instagram_followers), borderColor: "#ec4899", tension: .4, pointRadius: 4 },
        { label: "X", data: history.map(r => r.x_followers), borderColor: "#a3a3a3", tension: .4, pointRadius: 4 },
      ],
    },
  });
}

// ── Init ──────────────────────────────────────────────────────────────────────
loadData();
