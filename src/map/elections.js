/* AI Exposure × 2026 Midterms — King County prototype
 * D3 v7. Data: data/elections/king_2026.json (built by src/pipeline/08_election_overlay.py)
 */
(async function () {
  const data = await d3.json("data/elections/king_2026.json");
  const { meta, models, bins } = data;

  let layer = "e";
  let unit = "precincts";
  let binView = "raw";

  // ── Formatting ───────────────────────────────────────────────────
  const pct  = (v, d = 1) => v == null ? "—" : (v * 100).toFixed(d) + "%";
  const pp   = (v, d = 1) => v == null ? "—" : (v >= 0 ? "+" : "−") + Math.abs(v * 100).toFixed(d) + " pp";
  const idx  = (v) => v == null ? "—" : (v * 100).toFixed(1);
  const num  = (v) => v == null ? "—" : Math.round(v).toLocaleString();
  const money = (v) => v == null ? "—" : "$" + Math.round(v / 1000) + "K";

  // ── Header / stats ───────────────────────────────────────────────
  const snapLabel = (s) => s.replace("_", "-");
  document.getElementById("snapshot-note").textContent =
    `Snapshot: 2026 ${snapLabel(meta.snapshot_2026)} vs 2024 ${snapLabel(meta.snapshot_2024)}.`;
  document.getElementById("stat-swing").textContent = pp(meta.county_swing);
  document.getElementById("stat-d26").textContent   = pct(meta.county_d2p26_house);
  document.getElementById("stat-d24").textContent   = pct(meta.county_d2p24_pres);
  document.getElementById("stat-bal").textContent   = num(meta.ballots_2026);
  document.getElementById("sd-note").textContent    = (meta.exposure_sd * 100).toFixed(1);
  document.getElementById("corr-note").textContent  = "r = " + meta.corr_exposure_ba.toFixed(2);

  // ── Layers ───────────────────────────────────────────────────────
  // Each layer: accessor, color scale builder, legend text.
  function quantiles(features, key) {
    const v = features.map(f => f.properties[key]).filter(x => x != null).sort(d3.ascending);
    return [d3.quantileSorted(v, 0.05), d3.quantileSorted(v, 0.95)];
  }
  const LAYERS = {
    e: {
      title: "AI Exposure Index (tract-based)",
      scale: (fs) => d3.scaleSequential(d3.interpolateBlues).domain(quantiles(fs, "e")).clamp(true),
      ends: (s) => [idx(s.domain()[0]), "", idx(s.domain()[1])],
      sub: "Scale ×100 · p5–p95 range",
      ramp: (t) => d3.interpolateBlues(t),
    },
    d2p26: {
      title: "2026 US House — Democratic two-party share",
      scale: () => d3.scaleDiverging(d3.interpolateRdBu).domain([0.2, 0.5, 0.8]).clamp(true),
      ends: () => ["≤20% D", "50%", "≥80% D"],
      sub: "Election-night count · unofficial",
      ramp: (t) => d3.interpolateRdBu(t),
    },
    sw: {
      title: "Swing: 2026 House D share − 2024 President D share",
      scale: () => d3.scaleDiverging(d3.interpolateRdBu).domain([-0.12, 0, 0.12]).clamp(true),
      ends: () => ["−12 pp R", "0", "+12 pp D"],
      sub: "Election night vs election night",
      ramp: (t) => d3.interpolateRdBu(t),
    },
    ba: {
      title: "Adults 25+ with a bachelor's degree or more",
      scale: (fs) => d3.scaleSequential(d3.interpolatePurples).domain(quantiles(fs, "ba")).clamp(true),
      ends: (s) => [pct(s.domain()[0], 0), "", pct(s.domain()[1], 0)],
      sub: "ACS 2020–24 · p5–p95 range · the main confounder",
      ramp: (t) => d3.interpolatePurples(t),
    },
  };

  // ── Map ──────────────────────────────────────────────────────────
  const container = document.getElementById("map-container");
  const svg = d3.select("#map");
  const g = svg.append("g");
  let projection, path, colorScale;

  function setupProjection() {
    const w = container.clientWidth, h = container.clientHeight;
    svg.attr("viewBox", `0 0 ${w} ${h}`);
    projection = d3.geoMercator().fitExtent([[16, 16], [w - 16, h - 16]], data.tracts);
    path = d3.geoPath(projection);
  }
  setupProjection();

  function features() { return data[unit].features; }

  function draw() {
    const fs = features();
    const L = LAYERS[layer];
    colorScale = L.scale(fs);
    g.selectAll(".unit")
      .data(fs, d => unit + d.properties.id)
      .join("path")
      .attr("class", "unit")
      .attr("d", path)
      .attr("fill", d => {
        const v = d.properties[layer];
        return v == null ? "#d0d8e4" : colorScale(v);
      })
      .on("mousemove", onMove)
      .on("mouseleave", () => tooltip.classList.add("hidden"));
    rescaleStrokes(d3.zoomTransform(svg.node()).k);
    drawLegend();
  }

  const zoom = d3.zoom().scaleExtent([1, 40]).on("zoom", (ev) => {
    g.attr("transform", ev.transform);
    rescaleStrokes(ev.transform.k);
  });
  function rescaleStrokes(k) { g.selectAll(".unit").attr("stroke-width", (unit === "tracts" ? 0.4 : 0.15) / k); }
  svg.call(zoom);
  d3.select("#zoom-in").on("click", () => svg.transition().duration(300).call(zoom.scaleBy, 2));
  d3.select("#zoom-out").on("click", () => svg.transition().duration(300).call(zoom.scaleBy, 0.5));
  d3.select("#zoom-reset").on("click", () => svg.transition().duration(400).call(zoom.transform, d3.zoomIdentity));

  // ── Tooltip ──────────────────────────────────────────────────────
  const tooltip = document.getElementById("tooltip");
  function row(k, v) { return `<div class="tt-row"><span>${k}</span><span>${v}</span></div>`; }
  function onMove(ev, d) {
    const p = d.properties;
    const isP = unit === "precincts";
    tooltip.innerHTML = `
      <div class="tt-county">${isP ? "Precinct " + p.id : "Tract " + p.id.slice(5)}</div>
      <div class="tt-state">${isP && p.cd ? "Congressional District " + p.cd : "King County, WA"}</div>
      ${row("AI exposure index", idx(p.e))}
      ${row("BA+ share", pct(p.ba, 0))}
      ${row("Median HH income", money(p.inc))}
      <div style="height:6px"></div>
      ${row("2026 House D share", pct(p.d2p26))}
      ${row("2024 President D share", pct(p.d2p24))}
      ${row("Swing", pp(p.sw))}
      ${isP ? row("2026 ballots counted", num(p.b26)) : row("Turnout ratio 26/24", p.tr == null ? "—" : p.tr.toFixed(2))}
      ${isP ? "" : row("Workers (ACS)", num(p.w))}
      ${isP ? '<div class="tt-click-hint">Exposure is interpolated from overlapping tracts</div>' : ""}
    `;
    tooltip.classList.remove("hidden");
    const m = 14, tw = 260, th = 230;
    let x = ev.clientX + m, y = ev.clientY - th / 2;
    if (x + tw > window.innerWidth) x = ev.clientX - tw - m;
    y = Math.max(m, Math.min(y, window.innerHeight - th - m));
    tooltip.style.left = x + "px"; tooltip.style.top = y + "px";
  }

  // ── Legend ───────────────────────────────────────────────────────
  const legendSvg = d3.select("#legend-svg").attr("width", 220).attr("height", 10);
  const grad = legendSvg.append("defs").append("linearGradient").attr("id", "el-grad");
  legendSvg.append("rect").attr("width", 220).attr("height", 10).attr("rx", 3).attr("fill", "url(#el-grad)");
  function drawLegend() {
    const L = LAYERS[layer];
    grad.selectAll("stop").data(d3.range(0, 1.001, 0.1)).join("stop")
      .attr("offset", t => t * 100 + "%")
      .attr("stop-color", t => L.ramp(t));
    const [lo, mid, hi] = L.ends(colorScale);
    document.getElementById("legend-title").textContent = L.title;
    document.getElementById("legend-lo").textContent  = lo;
    document.getElementById("legend-mid").textContent = mid;
    document.getElementById("legend-hi").textContent  = hi;
    document.getElementById("legend-sub").textContent = L.sub;
  }

  // ── Toggles ──────────────────────────────────────────────────────
  function wireSeg(id, attr, set) {
    document.querySelectorAll(`#${id} .seg-btn`).forEach(btn => btn.addEventListener("click", () => {
      document.querySelectorAll(`#${id} .seg-btn`).forEach(b => b.classList.toggle("active", b === btn));
      set(btn.dataset[attr]);
    }));
  }
  wireSeg("layer-toggle", "layer", v => { layer = v; draw(); });
  wireSeg("unit-toggle",  "unit",  v => { unit = v; g.selectAll(".unit").remove(); draw(); });
  wireSeg("bin-toggle",   "bins",  v => { binView = v; drawBins(); });

  // ── Headline + model table ───────────────────────────────────────
  const full = models.swing.full.coef.exposure_sd;
  const lo95 = full[0] - 1.96 * full[1], hi95 = full[0] + 1.96 * full[1];
  document.getElementById("headline").innerHTML = `
    <div class="big">${pp(full[0], 2)}</div>
    <div class="sub">swing toward Democrats per +1 SD of AI exposure, with full controls
      (95% CI ${pp(lo95, 1)} to ${pp(hi95, 1)}; n = ${models.swing.full.n} tracts).
      Raw, without controls: ${pp(models.swing.bivariate.coef.exposure_sd[0], 2)}. Read it as a
      measure of confounding, not as an effect.</div>`;

  const SPECS = [
    ["bivariate", "No controls"],
    ["education_only", "+ BA+ share"],
    ["full", "+ income, 2024 vote, CD FE"],
  ];
  const tbody = document.querySelector("#model-table tbody");
  SPECS.forEach(([k, label]) => {
    const s = models.swing[k].coef.exposure_sd, t = models.turnout_ratio[k].coef.exposure_sd;
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${label}</td>
      <td>${(s[0] * 100 >= 0 ? "+" : "−") + Math.abs(s[0] * 100).toFixed(2)} <span class="se">(${(s[1] * 100).toFixed(2)})</span></td>
      <td>${(t[0] >= 0 ? "+" : "−") + Math.abs(t[0]).toFixed(3)} <span class="se">(${t[1].toFixed(3)})</span></td>`;
    tbody.appendChild(tr);
  });

  // ── Binned scatter ───────────────────────────────────────────────
  const bsvg = d3.select("#binscatter");
  const btip = document.getElementById("bin-tooltip");
  function drawBins() {
    const pts = bins[binView];
    const W = bsvg.node().clientWidth || 360, H = 220;
    const m = { t: 10, r: 10, b: 32, l: 48 };
    bsvg.attr("viewBox", `0 0 ${W} ${H}`).selectAll("*").remove();

    const x = d3.scaleLinear().domain(d3.extent(pts, d => d.x)).nice().range([m.l, W - m.r]);
    const yext = d3.extent(pts, d => d.y);
    const y = d3.scaleLinear().domain([Math.min(0, yext[0]), Math.max(0, yext[1])]).nice().range([H - m.b, m.t]);

    bsvg.append("g").attr("class", "grid").attr("transform", `translate(${m.l},0)`)
      .call(d3.axisLeft(y).ticks(5).tickSize(-(W - m.l - m.r)).tickFormat(""))
      .call(s => s.select(".domain").remove());
    bsvg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`)
      .call(d3.axisBottom(x).ticks(5).tickFormat(v => (v * 100).toFixed(0)));
    bsvg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`)
      .call(d3.axisLeft(y).ticks(5).tickFormat(v => (v * 100).toFixed(y.domain()[1] - y.domain()[0] < 0.06 ? 1 : 0)));
    bsvg.append("line").attr("class", "zero").attr("x1", m.l).attr("x2", W - m.r).attr("y1", y(0)).attr("y2", y(0));
    bsvg.append("text").attr("class", "axis-label").attr("x", W - m.r).attr("y", H - 4).attr("text-anchor", "end")
      .text(binView === "raw" ? "AI exposure index (×100)" : "AI exposure, residualized (×100)");
    bsvg.append("text").attr("class", "axis-label").attr("transform", `translate(10,${(H - m.b + m.t) / 2}) rotate(-90)`)
      .attr("text-anchor", "middle").text("swing toward D, pp");

    // Weighted least-squares line through the bin means
    const wsum = d3.sum(pts, d => d.n), mx = d3.sum(pts, d => d.x * d.n) / wsum, my = d3.sum(pts, d => d.y * d.n) / wsum;
    const b = d3.sum(pts, d => d.n * (d.x - mx) * (d.y - my)) / d3.sum(pts, d => d.n * (d.x - mx) ** 2);
    const [x0, x1] = x.domain();
    bsvg.append("path").attr("class", "fit")
      .attr("d", d3.line()([[x(x0), y(my + b * (x0 - mx))], [x(x1), y(my + b * (x1 - mx))]]));

    bsvg.selectAll(".pt").data(pts).join("circle").attr("class", "pt")
      .attr("cx", d => x(d.x)).attr("cy", d => y(d.y)).attr("r", 4.5);
    bsvg.selectAll(".hit").data(pts).join("circle").attr("class", "hit")
      .attr("cx", d => x(d.x)).attr("cy", d => y(d.y)).attr("r", 11)
      .on("mousemove", (ev, d) => {
        btip.innerHTML = `${row("Exposure (bin mean)", idx(d.x))}${row("Swing (bin mean)", pp(d.y, 2))}${row("Tracts", d.n)}`;
        btip.classList.remove("hidden");
        btip.style.left = (ev.clientX - 270) + "px"; btip.style.top = (ev.clientY - 20) + "px";
      })
      .on("mouseleave", () => btip.classList.add("hidden"));

    const rawB = models.swing.bivariate.coef.exposure_sd[0], fullB = models.swing.full.coef.exposure_sd[0];
    const dir = (v) => v >= 0 ? "more" : "less";
    document.getElementById("bin-note").textContent = binView === "raw"
      ? `Higher-exposure tracts swung ${dir(rawB)} toward Democrats, but exposure tracks education (r = ${meta.corr_exposure_ba.toFixed(2)}), and education drives swing on its own.`
      : `With education, income, 2024 vote and CD partialled out of both axes (Frisch–Waugh), higher-exposure tracts swung ${dir(fullB)} toward Democrats` +
        (Math.sign(rawB) !== Math.sign(fullB) ? ", the reverse of the raw slope." : ".");
  }
  drawBins();
  draw();

  window.addEventListener("resize", () => {
    setupProjection();
    g.selectAll(".unit").attr("d", path);
    svg.call(zoom.transform, d3.zoomIdentity);
    drawBins();
  });
})();
