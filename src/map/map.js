/* AI Exposure Atlas — Interactive County Choropleth
 * D3 v7 + topojson-client v3
 *
 * Layers: AI exposure · Robot exposure · AI × Robot (bivariate) · Within-county spread
 */

(async function () {
  // ── 1. Load data ──────────────────────────────────────────────────
  const [topoData, atlas, rankings] = await Promise.all([
    d3.json("https://cdn.jsdelivr.net/npm/us-atlas@3/counties-10m.json"),
    d3.json("data/atlas.json"),
    d3.json("data/rankings.json"),
  ]);

  const { occ_names, occ_exp, occ_robot, summary_5yr, summary_1yr,
          summary_robot_5yr, summary_robot_1yr, counties_5yr, counties_1yr } = atlas;
  const hasRobot = Array.isArray(occ_robot);

  // ── 2. State ──────────────────────────────────────────────────────
  let activeDataset = "5yr";
  let activeLayer   = "ai";
  let selectedFips  = null;
  let panelSort     = { col: "contrib", dir: "desc" };

  function currentData()    { return activeDataset === "5yr" ? counties_5yr : counties_1yr; }
  function currentSummary() { return activeDataset === "5yr" ? summary_5yr  : summary_1yr;  }
  function robotSummary()   { return activeDataset === "5yr" ? summary_robot_5yr : summary_robot_1yr; }

  // ── 3. Formatting ─────────────────────────────────────────────────
  // AI index displayed ×100 (0.1093 → "10.9"); robot index on its native 0–3 scale.
  function fmtIndex(v)   { return (v * 100).toFixed(1); }
  function fmtRobot(v)   { return v.toFixed(2); }
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

  // ── 4. Layers ─────────────────────────────────────────────────────
  // Bivariate palette (Stevens 3×3): columns = AI third (low→high), rows = robot third.
  const BIV = [
    ["#e8e8e8", "#ace4e4", "#5ac8c8"],   // robot low
    ["#dfb0d6", "#a5add3", "#5698b9"],   // robot mid
    ["#be64ac", "#8c62aa", "#3b4994"],   // robot high
  ];
  const BIV_NAME = (a, r) =>
    a === 2 && r === 2 ? "High on both"
    : a === 2 && r === 0 ? "AI-exposed only"
    : a === 0 && r === 2 ? "Robot-exposed only"
    : a === 0 && r === 0 ? "Low on both"
    : `AI ${["low", "mid", "high"][a]} · robot ${["low", "mid", "high"][r]}`;

  let bivCuts = null;   // { ai: [t1, t2], robot: [t1, t2] } — national terciles of the current dataset
  function computeBivCuts() {
    const recs = Object.values(currentData());
    const q = (arr) => { arr.sort(d3.ascending); return [d3.quantileSorted(arr, 1 / 3), d3.quantileSorted(arr, 2 / 3)]; };
    bivCuts = { ai: q(recs.map(r => r.e)), robot: q(recs.map(r => r.r)) };
  }
  function tercile(v, cuts) { return v <= cuts[0] ? 0 : v <= cuts[1] ? 1 : 2; }
  function bivClass(rec) { return [tercile(rec.e, bivCuts.ai), tercile(rec.r, bivCuts.robot)]; }

  // Spread is only meaningful with enough tracts: in counties with ≤5 tracts, ACS sampling
  // noise exceeds the measured variation two-thirds of the time.
  const MIN_SPREAD_TRACTS = 10;
  const hasSpread = (r) => r.ws && r.ws[2] >= MIN_SPREAD_TRACTS;
  function spreadSummary() {
    const v = Object.values(currentData()).filter(hasSpread).map(r => r.ws[0]).sort(d3.ascending);
    return { p05: d3.quantileSorted(v, 0.05), p95: d3.quantileSorted(v, 0.95), mean: d3.mean(v),
             min: v[0], max: v[v.length - 1], n: v.length };
  }

  const LAYERS = {
    ai: {
      value: r => r.e,
      ramp: d3.interpolateBlues,
      domain: () => [currentSummary().p05, currentSummary().p95],
      fmt: fmtIndex,
      title: "AI Exposure Index",
      sub: "Scale ×100 · p5–p95 range",
      top: "Most Exposed", bottom: "Least Exposed",
    },
    robot: {
      value: r => r.r,
      ramp: d3.interpolateRdPu,
      domain: () => [robotSummary().p05, robotSummary().p95],
      fmt: fmtRobot,
      title: "Robot Exposure Index",
      sub: "Scale 0–3 · p5–p95 range",
      top: "Most Robot-Exposed", bottom: "Least Robot-Exposed",
    },
    biv: {
      title: "AI × Robot Exposure",
      sub: "National thirds of counties",
      top: "Exposed to Both", bottom: "Exposed to Neither",
    },
    spread: {
      value: r => (hasSpread(r) ? r.ws[0] : null),
      ramp: d3.interpolateGreens,
      domain: () => { const s = spreadSummary(); return [s.p05, s.p95]; },
      fmt: fmtIndex,
      title: "Within-County Spread of AI Exposure",
      sub: "SD across tracts, noise-adjusted · ×100 · gray = under 10 tracts",
      top: "Most Internally Divided", bottom: "Most Uniform (50+ tracts)",
    },
  };

  let colorScale;
  function makeColorScale() {
    const L = LAYERS[activeLayer];
    if (activeLayer === "biv") { computeBivCuts(); return null; }
    return d3.scaleSequential(L.ramp).domain(L.domain()).clamp(true);
  }
  function fillFor(rec) {
    if (!rec) return "#d0d8e4";
    if (activeLayer === "biv") { const [a, r] = bivClass(rec); return BIV[r][a]; }
    const v = LAYERS[activeLayer].value(rec);
    return v == null ? "#d0d8e4" : colorScale(v);
  }
  colorScale = makeColorScale();

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
      .attr("fill", (d) => fillFor(currentData()[String(d.id).padStart(5, "0")]))
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

  function scoreLine(rec) {
    if (activeLayer === "robot") {
      return `<span class="tt-index tt-robot">${fmtRobot(rec.r)}</span>
        <span class="tt-pctile">Robot Exposure Index &middot; ${pctileLabel(rec.r, robotSummary())}</span>`;
    }
    if (activeLayer === "biv") {
      const [a, r] = bivClass(rec);
      return `<span class="tt-swatch" style="background:${BIV[r][a]}"></span>
        <span class="tt-pctile tt-strong">${BIV_NAME(a, r)}</span>`;
    }
    if (activeLayer === "spread") {
      if (!hasSpread(rec)) {
        return `<span class="tt-pctile">Only ${rec.ws ? rec.ws[2] : 0} tract(s): too few to separate real spread from survey noise</span>`;
      }
      return rec.ws[0] === 0
        ? `<span class="tt-index tt-spread">~0</span>
           <span class="tt-pctile">Tract differences within survey noise (${rec.ws[2]} tracts)</span>`
        : `<span class="tt-index tt-spread">${fmtIndex(rec.ws[0])}</span>
           <span class="tt-pctile">SD of AI exposure across ${rec.ws[2]} tracts</span>`;
    }
    return `<span class="tt-index">${fmtIndex(rec.e)}</span>
      <span class="tt-pctile">AI Exposure Index &middot; ${pctileLabel(rec.e, currentSummary())}</span>`;
  }

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

    const both = hasRobot && (activeLayer === "biv" || activeLayer === "spread")
      ? `<div class="tt-both">AI ${fmtIndex(rec.e)} &middot; Robot ${fmtRobot(rec.r)}</div>` : "";

    tooltip.innerHTML = `
      <div class="tt-county">${rec.n}</div>
      <div class="tt-state">${rec.s}</div>
      <div class="tt-score-line">${scoreLine(rec)}</div>
      ${both}
      <div class="tt-workforce">Civilian workforce: ${fmtN(rec.w)}</div>
      <div class="tt-occ-label">Largest occupation groups</div>
      ${occRows}
      <div class="tt-click-hint">Click for full breakdown</div>
    `;
    tooltip.classList.remove("hidden");

    const m = 14, tw = 300, th = 240;
    let x = event.clientX + m;
    let y = event.clientY - th / 2;
    if (x + tw > window.innerWidth) x = event.clientX - tw - m;
    y = Math.max(m, Math.min(y, window.innerHeight - th - m));
    tooltip.style.left = x + "px";
    tooltip.style.top  = y + "px";
  }

  function onMouseLeave() { tooltip.classList.add("hidden"); }

  // ── 9. Detail panel ───────────────────────────────────────────────
  // The contribution column follows the layer: robot scores on the robot layer, AI otherwise.
  function isRobotView() { return activeLayer === "robot" && hasRobot; }
  function contribScores() { return isRobotView() ? occ_robot : occ_exp; }

  function getRows(rec) {
    const s = contribScores();
    return occ_names.map((name, i) => ({
      name:    shortOccName(name),
      share:   rec.sh[i],
      contrib: rec.sh[i] * s[i],
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
    const isRobot    = isRobotView();
    const rows       = sortRows(getRows(rec));
    const maxContrib = Math.max(...rows.map(r => r.contrib));
    const list       = document.getElementById("detail-occ-list");
    list.innerHTML   = "";
    document.getElementById("contrib-label").textContent = isRobot ? "Robot contrib." : "AI contribution";
    document.getElementById("footer-metric").textContent = isRobot ? "robot" : "AI";

    for (const row of rows) {
      const barPct = maxContrib > 0 ? (row.contrib / maxContrib) * 100 : 0;
      const el     = document.createElement("div");
      el.className = "occ-row";
      el.innerHTML = `
        <div class="occ-name">${row.name}</div>
        <div class="occ-share">${fmtPct(row.share)}</div>
        <div class="occ-contrib-cell">
          <span class="occ-contrib-val">${isRobot ? row.contrib.toFixed(2) : (row.contrib * 100).toFixed(1)}</span>
          <div class="occ-bar-bg"><div class="occ-bar${isRobot ? " robot" : ""}" style="width:${barPct}%"></div></div>
        </div>
      `;
      list.appendChild(el);
    }

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
    const isRobot = isRobotView();

    document.getElementById("detail-county").textContent = rec.n;
    document.getElementById("detail-state").textContent  = rec.s;
    const scoreEl = document.getElementById("detail-score");
    scoreEl.textContent = isRobot ? fmtRobot(rec.r) : fmtIndex(rec.e);
    scoreEl.classList.toggle("robot", isRobot);
    document.getElementById("detail-score-context").textContent = isRobot
      ? pctileLabel(rec.r, robotSummary()) + " of US counties · robot index, scale 0–3"
      : pctileLabel(rec.e, currentSummary()) + " of US counties · AI index, scale 0–100";
    document.getElementById("detail-workforce").textContent =
      `Civilian workforce: ${rec.w.toLocaleString()}`;

    const other = [];
    if (hasRobot) {
      other.push(isRobot ? `AI index ${fmtIndex(rec.e)} (${pctileLabel(rec.e, currentSummary()).toLowerCase()})`
                         : `Robot index ${fmtRobot(rec.r)} (${pctileLabel(rec.r, robotSummary()).toLowerCase()})`);
    }
    if (hasSpread(rec) && rec.ws[0] > 0) {
      other.push(`AI exposure varies by ±${fmtIndex(rec.ws[0])} (1 SD) across its ${rec.ws[2]} census tracts`);
    }
    document.getElementById("detail-other").innerHTML = other.map(t => `<div>${t}</div>`).join("");

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

  // ── 10. Toggles ───────────────────────────────────────────────────
  function refresh() {
    colorScale = makeColorScale();
    updateFill();
    updateLegend();
    updateStats();
    updateRankings();
    if (selectedFips) openPanel(selectedFips);
  }

  document.querySelectorAll(".toggle-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      activeDataset = btn.dataset.dataset;
      document.querySelectorAll(".toggle-btn").forEach((b) => b.classList.toggle("active", b === btn));
      refresh();
    });
  });

  document.querySelectorAll(".layer-btn").forEach((btn) => {
    if (!hasRobot && (btn.dataset.layer === "robot" || btn.dataset.layer === "biv")) btn.disabled = true;
    btn.addEventListener("click", () => {
      activeLayer = btn.dataset.layer;
      document.querySelectorAll(".layer-btn").forEach((b) => b.classList.toggle("active", b === btn));
      refresh();
    });
  });

  // ── 11. Legend ────────────────────────────────────────────────────
  const legendSvg = d3.select("#legend-svg").attr("width", 220).attr("height", 10);
  const grad      = legendSvg.append("defs").append("linearGradient").attr("id", "legend-grad");
  legendSvg.append("rect").attr("width", 220).attr("height", 10).attr("rx", 3)
    .attr("fill", "url(#legend-grad)");

  // Bivariate legend: 3×3 grid, AI across, robot up, with corner labels
  const bivEl = document.getElementById("legend-biv");
  bivEl.innerHTML = `
    <div class="biv-wrap">
      <div class="biv-axis-y">Robot →</div>
      <div class="biv-grid">${[2, 1, 0].map(r => [0, 1, 2].map(a =>
        `<span style="background:${BIV[r][a]}" title="${BIV_NAME(a, r)}"></span>`).join("")).join("")}</div>
      <div class="biv-notes">
        <div><b>Top-right</b> high on both</div>
        <div><b>Top-left</b> robot-exposed only</div>
        <div><b>Bottom-right</b> AI-exposed only</div>
      </div>
    </div>
    <div class="biv-axis-x">AI →</div>`;

  function updateLegend() {
    const L = LAYERS[activeLayer];
    document.getElementById("legend-title").textContent = L.title;
    document.getElementById("legend-sub").textContent = L.sub;
    const isBiv = activeLayer === "biv";
    document.getElementById("legend-ramp").classList.toggle("hidden", isBiv);
    bivEl.classList.toggle("hidden", !isBiv);
    if (isBiv) return;
    grad.selectAll("stop").data(d3.range(0, 1.01, 0.1)).join("stop")
      .attr("offset", t => `${t * 100}%`)
      .attr("stop-color", t => L.ramp(t * 0.85 + 0.1));
    const [lo, hi] = colorScale.domain();
    document.getElementById("legend-lo").textContent = L.fmt(lo);
    document.getElementById("legend-hi").textContent = L.fmt(hi);
  }
  updateLegend();

  // ── 12. Stats ─────────────────────────────────────────────────────
  function pearson(xs, ys) {
    const mx = d3.mean(xs), my = d3.mean(ys);
    const sxy = d3.sum(xs, (v, i) => (v - mx) * (ys[i] - my));
    return sxy / Math.sqrt(d3.sum(xs, v => (v - mx) ** 2) * d3.sum(ys, v => (v - my) ** 2));
  }

  function updateStats() {
    const set = (id, v) => { document.getElementById(id).textContent = v; };
    const s = currentSummary();
    set("stat-n", s.n.toLocaleString());
    if (activeLayer === "robot") {
      const rs = robotSummary();
      set("stat-mean", fmtRobot(rs.mean));            set("stat-mean-label", "mean robot index");
      set("stat-range", `${fmtRobot(rs.min)}–${fmtRobot(rs.max)}`); set("stat-range-label", "robot range");
    } else if (activeLayer === "biv") {
      const recs = Object.values(currentData());
      const n = recs.filter(r => { const [a, b] = bivClass(r); return a === 2 && b === 2; }).length;
      set("stat-mean", n.toLocaleString());             set("stat-mean-label", "high on both");
      set("stat-range", pearson(recs.map(r => r.e), recs.map(r => r.r)).toFixed(2));
      set("stat-range-label", "AI–robot correlation");
    } else if (activeLayer === "spread") {
      const ss = spreadSummary();
      set("stat-n", ss.n.toLocaleString());
      set("stat-mean", fmtIndex(ss.mean));             set("stat-mean-label", "mean tract SD");
      set("stat-range", `${fmtIndex(ss.min)}–${fmtIndex(ss.max)}`); set("stat-range-label", "tract SD range");
    } else {
      set("stat-mean", fmtIndex(s.mean));              set("stat-mean-label", "mean index");
      set("stat-range", `${fmtIndex(s.min)}–${fmtIndex(s.max)}`);   set("stat-range-label", "index range");
    }
  }
  updateStats();

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

  // ── 13. Rankings ──────────────────────────────────────────────────
  // The AI layer uses the precomputed rankings.json; other layers rank in the browser.
  // Small counties are noisy, so computed rankings require ≥ MIN_RANK_WORKERS workers
  // (spread rankings require ≥ 20 tracts instead).
  const MIN_RANK_WORKERS = 25000;

  function computedRanking() {
    const entries = Object.entries(currentData()).map(([fips, r]) => ({ fips, r }));
    const item = (e, label) => ({ fips: e.fips, county: e.r.n, state: e.r.s, label });
    if (activeLayer === "robot") {
      const big = entries.filter(e => e.r.w >= MIN_RANK_WORKERS).sort((a, b) => b.r.r - a.r.r);
      return { top: big.slice(0, 8).map(e => item(e, fmtRobot(e.r.r))),
               bottom: big.slice(-8).reverse().map(e => item(e, fmtRobot(e.r.r))) };
    }
    if (activeLayer === "biv") {
      // Rank by the weaker of the two national percentiles: both must be high to rank high
      const pa = d3.scaleQuantile().domain(entries.map(e => e.r.e)).range(d3.range(100));
      const pr = d3.scaleQuantile().domain(entries.map(e => e.r.r)).range(d3.range(100));
      const big = entries.filter(e => e.r.w >= MIN_RANK_WORKERS)
        .map(e => ({ ...e, a: pa(e.r.e), b: pr(e.r.r) }))
        .map(e => ({ ...e, lo: Math.min(e.a, e.b), hi: Math.max(e.a, e.b) }));
      const lbl = e => `${e.a} / ${e.b}`;
      return { top: [...big].sort((x, y) => y.lo - x.lo).slice(0, 8).map(e => item(e, lbl(e))),
               bottom: [...big].sort((x, y) => x.hi - y.hi).slice(0, 8).map(e => item(e, lbl(e))) };
    }
    // "Most uniform" needs many tracts, or it just lists counties too small to measure
    const byDesc = (min) => entries.filter(e => e.r.ws && e.r.ws[2] >= min).sort((a, b) => b.r.ws[0] - a.r.ws[0]);
    return { top: byDesc(20).slice(0, 8).map(e => item(e, fmtIndex(e.r.ws[0]))),
             bottom: byDesc(50).slice(-8).reverse().map(e => item(e, fmtIndex(e.r.ws[0]))) };
  }

  function updateRankings() {
    const L = LAYERS[activeLayer];
    document.getElementById("top-heading").textContent = L.top;
    document.getElementById("bottom-heading").textContent = L.bottom;
    if (activeLayer === "ai") {
      const fmt = it => ({ ...it, label: fmtIndex(it.exposure), num: it.rank });
      renderRankList("top-list",    rankings[activeDataset].top.slice(0, 8).map(fmt));
      renderRankList("bottom-list", rankings[activeDataset].bottom.slice(-8).reverse().map(fmt));
      return;
    }
    const { top, bottom } = computedRanking();
    renderRankList("top-list",    top.map((it, i) => ({ ...it, num: i + 1 })));
    renderRankList("bottom-list", bottom.map((it, i) => ({ ...it, num: i + 1 })));
  }

  function renderRankList(id, items) {
    const ul = document.getElementById(id);
    ul.innerHTML = "";
    items.forEach((item) => {
      const li = document.createElement("li");
      li.innerHTML = `
        <span class="rk-num">${item.num}</span>
        <span class="rk-name">${item.county}</span>
        <span class="rk-state">${abbrevState(item.state)}</span>
        <span class="rk-score">${item.label}</span>
      `;
      li.style.cursor = "pointer";
      if (activeLayer === "biv") li.title = "National percentile: AI / robot (counties with 25K+ workers)";
      li.addEventListener("click", () => {
        zoomToCounty(item.fips);
        onCountyClick({ stopPropagation: () => {} }, { id: parseInt(item.fips, 10) });
      });
      ul.appendChild(li);
    });
  }
  updateRankings();

  // ── 14. Search ────────────────────────────────────────────────────
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

    const matches = searchIndex.filter(c => c.lower.includes(q)).slice(0, 8);
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

})();
