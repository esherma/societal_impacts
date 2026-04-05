/* AI Exposure Atlas — Interactive County Choropleth
 * D3 v7 + topojson-client v3
 */

(async function () {
  // ── 1. Load data ──────────────────────────────────────────────────
  const [topoData, atlas, rankings] = await Promise.all([
    d3.json("https://cdn.jsdelivr.net/npm/us-atlas@3/counties-10m.json"),
    d3.json("data/atlas.json"),
    d3.json("data/rankings.json"),
  ]);

  const { occ_names, occ_exp, summary_5yr, summary_1yr,
          counties_5yr, counties_1yr } = atlas;

  // ── 2. State ──────────────────────────────────────────────────────
  let activeDataset = "5yr";
  let selectedFips   = null;
  let panelSort      = { col: "contrib", dir: "desc" };

  function currentData()    { return activeDataset === "5yr" ? counties_5yr : counties_1yr; }
  function currentSummary() { return activeDataset === "5yr" ? summary_5yr  : summary_1yr;  }

  // ── 3. Formatting ─────────────────────────────────────────────────
  // Index displayed ×100, rounded to 1 decimal (so 0.1093 → "10.9")
  function fmtIndex(v)   { return (v * 100).toFixed(1); }
  function fmtPct(v)     { return (v * 100).toFixed(1) + "%"; }
  function fmtN(n) {
    return n >= 1e6 ? (n / 1e6).toFixed(1) + "M"
         : n >= 1e3 ? (n / 1e3).toFixed(0) + "K"
         : String(n);
  }

  function pctileLabel(v, s) {
    if (v >= s.p95) return "Top 5%";
    if (v >= s.p90) return "Top 10%";
    if (v >= s.p75) return "Top 25%";
    if (v <= s.p05) return "Bottom 5%";
    if (v <= s.p10) return "Bottom 10%";
    if (v <= s.p25) return "Bottom 25%";
    return "Middle 50%";
  }

  function shortOccName(name) {
    return name
      .replace(" occupations", "")
      .replace(" and related", "")
      .replace(", entertainment, sports, media", "")
      .replace("Health diagnosing and treating practitioners", "Health diagnosing")
      .replace("Building and grounds cleaning and maintenance", "Building & grounds")
      .replace("Installation, maintenance, and repair", "Installation & repair");
  }

  // ── 4. Color scale ────────────────────────────────────────────────
  function makeColorScale(summary) {
    return d3.scaleSequential(d3.interpolateBlues)
      .domain([summary.p05, summary.p95])
      .clamp(true);
  }
  let colorScale = makeColorScale(currentSummary());

  // ── 5. Map setup ──────────────────────────────────────────────────
  const container = document.getElementById("map-container");
  function dims() { return { w: container.clientWidth, h: container.clientHeight }; }

  const svg      = d3.select("#map");
  const mapGroup = svg.append("g");

  const counties    = topojson.feature(topoData, topoData.objects.counties);
  const stateBorders = topojson.mesh(topoData, topoData.objects.states, (a, b) => a !== b);

  let projection, path;
  function setupProjection() {
    const { w, h } = dims();
    svg.attr("viewBox", `0 0 ${w} ${h}`);
    projection = d3.geoAlbersUsa().fitSize([w, h], counties);
    path = d3.geoPath().projection(projection);
  }
  setupProjection();

  // ── 6. Draw map ───────────────────────────────────────────────────
  const countyPaths = mapGroup
    .selectAll(".county")
    .data(counties.features)
    .join("path")
    .attr("class", "county")
    .attr("d", path)
    .on("mousemove", onMouseMove)
    .on("mouseleave", onMouseLeave)
    .on("click", onCountyClick);

  mapGroup.append("path").datum(stateBorders).attr("class", "state-border").attr("d", path);

  function updateFill() {
    countyPaths
      .attr("fill", (d) => {
        const rec = currentData()[String(d.id).padStart(5, "0")];
        return rec ? colorScale(rec.e) : "#d0d8e4";
      })
      .attr("opacity", (d) => {
        if (activeDataset === "5yr") return 1;
        return counties_1yr[String(d.id).padStart(5, "0")] ? 1 : 0.35;
      });
  }
  updateFill();

  // ── 7. Zoom ───────────────────────────────────────────────────────
  const zoom = d3.zoom()
    .scaleExtent([1, 20])
    .on("zoom", (event) => {
      mapGroup.attr("transform", event.transform);
      const k = event.transform.k;
      countyPaths.attr("stroke-width", 0.3 / k);
      mapGroup.select(".state-border").attr("stroke-width", 0.8 / k);
    });

  svg.call(zoom);

  d3.select("#zoom-in").on("click",    () => svg.transition().duration(350).call(zoom.scaleBy, 2));
  d3.select("#zoom-out").on("click",   () => svg.transition().duration(350).call(zoom.scaleBy, 0.5));
  d3.select("#zoom-reset").on("click", () => { closePanel(); svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity); });

  function zoomToCounty(fips) {
    const feature = counties.features.find(f => String(f.id).padStart(5, "0") === fips);
    if (!feature) return;
    const { w, h } = dims();
    const [[x0, y0], [x1, y1]] = path.bounds(feature);
    const pad = 60;
    const scale = Math.min(16, 0.85 / Math.max((x1 - x0 + pad) / w, (y1 - y0 + pad) / h));
    const tx = w / 2 - scale * (x0 + x1) / 2;
    const ty = h / 2 - scale * (y0 + y1) / 2;
    svg.transition().duration(750)
      .call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale));
  }

  // ── 8. Tooltip ────────────────────────────────────────────────────
  const tooltip = document.getElementById("tooltip");

  function onMouseMove(event, d) {
    const fips = String(d.id).padStart(5, "0");
    const rec  = currentData()[fips];
    if (!rec) { tooltip.classList.add("hidden"); return; }

    const topOccs = occ_names
      .map((name, i) => ({ name, share: rec.sh[i] }))
      .sort((a, b) => b.share - a.share)
      .slice(0, 4);

    const occRows = topOccs.map(o =>
      `<div class="tt-occ-row">
        <span>${shortOccName(o.name)}</span>
        <span class="tt-occ-pct">${fmtPct(o.share)}</span>
      </div>`
    ).join("");

    tooltip.innerHTML = `
      <div class="tt-county">${rec.n}</div>
      <div class="tt-state">${rec.s}</div>
      <div class="tt-score-line">
        <span class="tt-index">${fmtIndex(rec.e)}</span>
        <span class="tt-pctile">AI Exposure Index &middot; ${pctileLabel(rec.e, currentSummary())}</span>
      </div>
      <div class="tt-workforce">Civilian workforce: ${fmtN(rec.w)}</div>
      <div class="tt-occ-label">Largest occupation groups</div>
      ${occRows}
      <div class="tt-click-hint">Click for full breakdown</div>
    `;
    tooltip.classList.remove("hidden");

    const m = 14, tw = 300, th = 220;
    let x = event.clientX + m;
    let y = event.clientY - th / 2;
    if (x + tw > window.innerWidth) x = event.clientX - tw - m;
    y = Math.max(m, Math.min(y, window.innerHeight - th - m));
    tooltip.style.left = x + "px";
    tooltip.style.top  = y + "px";
  }

  function onMouseLeave() { tooltip.classList.add("hidden"); }

  // ── 9. Detail panel ───────────────────────────────────────────────
  function getRows(rec) {
    return occ_names.map((name, i) => ({
      name:    shortOccName(name),
      share:   rec.sh[i],
      catExp:  occ_exp[i],
      contrib: rec.sh[i] * occ_exp[i],
    }));
  }

  function sortRows(rows) {
    return [...rows].sort((a, b) => {
      const av = panelSort.col === "name"   ? a.name
               : panelSort.col === "share"  ? a.share
               : a.contrib;
      const bv = panelSort.col === "name"   ? b.name
               : panelSort.col === "share"  ? b.share
               : b.contrib;
      if (typeof av === "string") {
        return panelSort.dir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      return panelSort.dir === "asc" ? av - bv : bv - av;
    });
  }

  function renderOccupations(rec) {
    const rows       = sortRows(getRows(rec));
    const maxContrib = Math.max(...rows.map(r => r.contrib));
    const list       = document.getElementById("detail-occ-list");
    list.innerHTML   = "";

    for (const row of rows) {
      const barPct = maxContrib > 0 ? (row.contrib / maxContrib) * 100 : 0;
      const el     = document.createElement("div");
      el.className = "occ-row";
      el.innerHTML = `
        <div class="occ-name">${row.name}</div>
        <div class="occ-share">${fmtPct(row.share)}</div>
        <div class="occ-contrib-cell">
          <span class="occ-contrib-val">${(row.contrib * 100).toFixed(1)}</span>
          <div class="occ-bar-bg"><div class="occ-bar" style="width:${barPct}%"></div></div>
        </div>
      `;
      list.appendChild(el);
    }

    // Sync sort icons on column headers
    document.querySelectorAll(".sort-col").forEach(col => {
      const icon = col.querySelector(".sort-icon");
      if (col.dataset.col === panelSort.col) {
        icon.textContent = panelSort.dir === "asc" ? " ↑" : " ↓";
        col.classList.add("sort-active");
      } else {
        icon.textContent = " ↕";
        col.classList.remove("sort-active");
      }
    });
  }

  function openPanel(fips) {
    const rec = currentData()[fips];
    if (!rec) return;

    selectedFips = fips;

    document.getElementById("detail-county").textContent = rec.n;
    document.getElementById("detail-state").textContent  = rec.s;
    document.getElementById("detail-score").textContent  = fmtIndex(rec.e);
    document.getElementById("detail-score-context").textContent =
      pctileLabel(rec.e, currentSummary()) + " of US counties · index scale 0–100";
    document.getElementById("detail-workforce").textContent =
      `Civilian workforce: ${rec.w.toLocaleString()}`;

    renderOccupations(rec);
    document.getElementById("detail-panel").classList.remove("hidden");
  }

  function closePanel() {
    document.getElementById("detail-panel").classList.add("hidden");
    selectedFips = null;
    countyPaths.attr("stroke", null).attr("stroke-width", null);
  }

  function onCountyClick(event, d) {
    event.stopPropagation();
    const fips = String(d.id).padStart(5, "0");
    countyPaths
      .attr("stroke", (dd) => String(dd.id).padStart(5, "0") === fips ? "#1e293b" : null)
      .attr("stroke-width", (dd) => {
        const k = d3.zoomTransform(svg.node()).k;
        return String(dd.id).padStart(5, "0") === fips ? 2 / k : 0.3 / k;
      });
    openPanel(fips);
    tooltip.classList.add("hidden");
  }

  svg.on("click", () => closePanel());
  document.getElementById("close-panel").addEventListener("click", closePanel);

  // Sortable column headers
  document.querySelectorAll(".sort-col").forEach(col => {
    col.addEventListener("click", () => {
      const newCol = col.dataset.col;
      if (panelSort.col === newCol) {
        panelSort.dir = panelSort.dir === "desc" ? "asc" : "desc";
      } else {
        panelSort.col = newCol;
        panelSort.dir = newCol === "name" ? "asc" : "desc";
      }
      if (selectedFips) renderOccupations(currentData()[selectedFips]);
    });
  });

  // ── 10. Dataset toggle ────────────────────────────────────────────
  document.querySelectorAll(".toggle-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      activeDataset = btn.dataset.dataset;
      document.querySelectorAll(".toggle-btn").forEach((b) =>
        b.classList.toggle("active", b === btn)
      );
      colorScale = makeColorScale(currentSummary());
      updateFill();
      updateLegend();
      updateStats();
      updateRankings();
      if (selectedFips) openPanel(selectedFips);
    });
  });

  // ── 11. Legend ────────────────────────────────────────────────────
  const legendSvg = d3.select("#legend-svg").attr("width", 220).attr("height", 10);
  const defs      = legendSvg.append("defs");
  const grad      = defs.append("linearGradient").attr("id", "legend-grad");
  d3.range(0, 1.01, 0.1).forEach(t => {
    grad.append("stop")
      .attr("offset", `${t * 100}%`)
      .attr("stop-color", d3.interpolateBlues(t * 0.85 + 0.1));
  });
  legendSvg.append("rect").attr("width", 220).attr("height", 10).attr("rx", 3)
    .attr("fill", "url(#legend-grad)");

  function updateLegend() {
    const s = currentSummary();
    document.getElementById("legend-lo").textContent = fmtIndex(s.p05);
    document.getElementById("legend-hi").textContent = fmtIndex(s.p95);
  }
  updateLegend();

  // ── 12. Stats ─────────────────────────────────────────────────────
  function updateStats() {
    const s = currentSummary();
    document.getElementById("stat-n").textContent     = s.n.toLocaleString();
    document.getElementById("stat-mean").textContent  = fmtIndex(s.mean);
    document.getElementById("stat-range").textContent =
      `${fmtIndex(s.min)}–${fmtIndex(s.max)}`;
  }
  updateStats();

  // ── 13. Rankings ──────────────────────────────────────────────────
  function updateRankings() {
    renderRankList("top-list",    rankings[activeDataset].top.slice(0, 8));
    renderRankList("bottom-list", rankings[activeDataset].bottom.slice(-8).reverse());
  }

  function renderRankList(id, items) {
    const ul = document.getElementById(id);
    ul.innerHTML = "";
    items.forEach((item) => {
      const li = document.createElement("li");
      li.innerHTML = `
        <span class="rk-num">${item.rank}</span>
        <span class="rk-name">${item.county}</span>
        <span class="rk-state">${abbrevState(item.state)}</span>
        <span class="rk-score">${fmtIndex(item.exposure)}</span>
      `;
      li.style.cursor = "pointer";
      li.addEventListener("click", () => {
        zoomToCounty(item.fips);
        openPanel(item.fips);
        onCountyClick({ stopPropagation: () => {} }, { id: parseInt(item.fips, 10) });
      });
      ul.appendChild(li);
    });
  }
  updateRankings();

  // ── 14. Search ────────────────────────────────────────────────────
  // Build index from 5yr data (always complete)
  const searchIndex = Object.entries(counties_5yr).map(([fips, d]) => ({
    fips,
    label: `${d.n}, ${d.s}`,
    lower: `${d.n.toLowerCase()}, ${d.s.toLowerCase()}`,
  }));

  const searchInput   = document.getElementById("search-input");
  const searchResults = document.getElementById("search-results");

  searchInput.addEventListener("input", () => {
    const q = searchInput.value.toLowerCase().trim();
    searchResults.innerHTML = "";
    if (q.length < 2) { searchResults.classList.add("hidden"); return; }

    const matches = searchIndex
      .filter(c => c.lower.includes(q))
      .slice(0, 8);

    if (!matches.length) { searchResults.classList.add("hidden"); return; }

    matches.forEach(match => {
      const div = document.createElement("div");
      div.className = "search-result";
      div.textContent = match.label;
      div.addEventListener("mousedown", (e) => {
        e.preventDefault(); // keep focus on input long enough to register click
        searchInput.value = match.label;
        searchResults.classList.add("hidden");
        zoomToCounty(match.fips);
        openPanel(match.fips);
      });
      searchResults.appendChild(div);
    });
    searchResults.classList.remove("hidden");
  });

  searchInput.addEventListener("blur", () => {
    setTimeout(() => searchResults.classList.add("hidden"), 150);
  });

  searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { searchResults.classList.add("hidden"); searchInput.blur(); }
  });

  // ── 15. Resize ────────────────────────────────────────────────────
  window.addEventListener("resize", () => {
    setupProjection();
    countyPaths.attr("d", path);
    mapGroup.select(".state-border").attr("d", path);
    svg.call(zoom.transform, d3.zoomIdentity);
  });

  // ── Helpers ───────────────────────────────────────────────────────
  const STATE_ABBREVS = {
    "Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA",
    "Colorado":"CO","Connecticut":"CT","Delaware":"DE","District of Columbia":"DC",
    "Florida":"FL","Georgia":"GA","Hawaii":"HI","Idaho":"ID","Illinois":"IL",
    "Indiana":"IN","Iowa":"IA","Kansas":"KS","Kentucky":"KY","Louisiana":"LA",
    "Maine":"ME","Maryland":"MD","Massachusetts":"MA","Michigan":"MI","Minnesota":"MN",
    "Mississippi":"MS","Missouri":"MO","Montana":"MT","Nebraska":"NE","Nevada":"NV",
    "New Hampshire":"NH","New Jersey":"NJ","New Mexico":"NM","New York":"NY",
    "North Carolina":"NC","North Dakota":"ND","Ohio":"OH","Oklahoma":"OK","Oregon":"OR",
    "Pennsylvania":"PA","Puerto Rico":"PR","Rhode Island":"RI","South Carolina":"SC",
    "South Dakota":"SD","Tennessee":"TN","Texas":"TX","Utah":"UT","Vermont":"VT",
    "Virginia":"VA","Washington":"WA","West Virginia":"WV","Wisconsin":"WI","Wyoming":"WY",
  };
  function abbrevState(n) { return STATE_ABBREVS[n] || n.slice(0, 2).toUpperCase(); }
})();
