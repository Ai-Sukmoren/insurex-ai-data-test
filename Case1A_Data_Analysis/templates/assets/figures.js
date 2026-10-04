/* Figures - every chart of the analysis, built from the DATA payload. Shared by the dashboard, the slides and the guide. */
"use strict";

class Figures {
  static SEGMENT_COLORS = {"Lower Mass": "var(--seg-1)", "Mass": "var(--seg-2)", "Upper Mass": "var(--seg-3)"};
  static OUTCOME_COLORS = {"Rejected": "var(--rejected)", "PA": "var(--pa)", "Life": "var(--life)"};

  static avg(s) { return (s.kpi.pa + s.kpi.life) / s.kpi.n; }

  /** Render a figure by name: used by pages that declare <div data-fig="name" data-slice="All">. */
  static render(name, host, data, sliceName = "All") {
    const s = data.slices[sliceName], m = data.model;
    const [kind, arg] = name.split(":");
    const fn = {
      volume: () => Figures.volume(host, s), rate: () => Figures.rate(host, s),
      heatmap: () => new HeatmapChart(host, s.heatmap),
      bubble: () => new BubbleChart(host, s.opportunity, Figures.SEGMENT_COLORS, Figures.avg(s)),
      lift: () => new DivergingBarChart(host, s.lift),
      agedist: () => Figures.ageDistribution(host, s.age_dist),
      range: () => new DotRangeChart(host, s.ranges[+arg], Figures.OUTCOME_COLORS),
      profile: () => new StackedBarChart(host, s.profile[arg], Figures.avg(s)),
      gains: () => Figures.gains(host, m), deciles: () => Figures.deciles(host, m),
      importance: () => Figures.importance(host, m, +arg || 10), tiers: () => Figures.tiers(host, m),
    }[kind];
    if (!fn) throw new Error("Unknown figure " + name);
    fn();
  }

  static volume(host, s) {
    const rows = s.month;
    return new ColumnChart(host, rows.map(r => ({
      label: r.cat, value: r.n,
      tip: [`${r.cat} campaign`, [{label: "Customers contacted", value: Fmt.n(r.n), color: "var(--volume)"}]],
      row: [r.cat, Fmt.n(r.n)],
    })), {color: "var(--volume)", max: Math.ceil(Math.max(...rows.map(r => r.n)) * 1.1 / 5000) * 5000,
          format: (v, label) => label ? Fmt.n(v) : Fmt.compact(v), headers: ["Month", "Customers"]});
  }

  static rate(host, s) {
    const rows = s.month;
    const total = rows.map(r => (r.pa + r.life) / r.n), pa = rows.map(r => r.pa / r.n), life = rows.map(r => r.life / r.n);
    const chart = new LineChart(host, rows.map(r => r.cat), [
      {name: "Total", values: total, color: "var(--ink)"},
      {name: "PA", values: pa, color: "var(--pa)"},
      {name: "Life", values: life, color: "var(--life)"},
    ], {yMax: niceMax(Math.max(...total) * 1.15), yFormat: (v, tip) => tip ? Fmt.pct(v) : Fmt.tick(v),
        tipTitle: (mo, i) => `${mo} · ${Fmt.n(rows[i].n)} contacted`,
        table: {headers: ["Month", "Total", "PA", "Life"], rows: rows.map((r, i) => [r.cat, Fmt.pct(total[i]), Fmt.pct(pa[i]), Fmt.pct(life[i])])}});
    const hi = total.indexOf(Math.max(...total));
    chart.annotate(hi, total[hi], `${rows[hi].cat} ${Fmt.pct(total[hi], 1)}`, "var(--ink)");
    return chart;
  }

  static ageDistribution(host, dist) {
    const names = Object.keys(dist.series);
    const max = Math.max(...names.flatMap(n => dist.series[n]));
    return new LineChart(host, dist.x.map(String),
      names.map(n => ({name: n, values: dist.series[n], color: Figures.OUTCOME_COLORS[n]})),
      {yMax: Math.ceil(max * 1.15), yFormat: (v, tip) => (tip ? v.toFixed(1) : Math.round(v)) + "%", xEvery: 5,
       tipTitle: a => `Age ${a}–${+a + 1}`,
       table: {headers: ["Age", ...names], rows: dist.x.map((a, i) => [`${a}–${a + 1}`, ...names.map(n => dist.series[n][i].toFixed(1) + "%")])}});
  }

  static gains(host, m) {
    const chart = new LineChart(host, m.gains.map(g => String(g.pct_contacted)), [
      {name: "Model", values: m.gains.map(g => g.pct_buyers / 100), color: "var(--model)", area: true},
      {name: "Random targeting", values: m.gains.map(g => g.pct_contacted / 100), color: "var(--muted)", width: 1.5},
    ], {yMax: 1, yTicks: [0, 0.25, 0.5, 0.75, 1], yFormat: v => Math.round(v * 100) + "%", xEvery: 10, height: 260,
        tipTitle: p => `Contact top ${p}% of customers`,
        table: {headers: ["% contacted", "% buyers (model)", "% buyers (random)"],
                rows: m.gains.filter(g => g.pct_contacted % 10 === 0).map(g => [g.pct_contacted + "%", g.pct_buyers.toFixed(1) + "%", g.pct_contacted + "%"])}});
    chart.annotate(20, m.top20_capture / 100, `Top 20% → ${Math.round(m.top20_capture)}% of buyers`, "var(--model)");
    return chart;
  }

  static deciles(host, m) {
    return new ColumnChart(host, m.deciles.map(d => ({
      label: "D" + d.decile, value: d.lift,
      tip: [`Decile ${d.decile} (${(d.decile - 1) * 10}–${d.decile * 10}% highest scores)`, [
        {label: "Lift", value: d.lift.toFixed(2) + "×", color: "var(--model)"},
        {label: "Acceptance", value: Fmt.pct(d.rate)}, {label: "Share of buyers", value: Fmt.pct(d.capture, 1)}]],
      row: ["D" + d.decile, d.lift.toFixed(2) + "×", Fmt.pct(d.rate), Fmt.pct(d.capture, 1)],
    })), {color: "var(--model)", max: Math.ceil(m.deciles[0].lift), ref: 1, refLabel: "average = 1×",
          format: v => v.toFixed(1) + "×", headers: ["Decile", "Lift", "Acceptance", "Share of buyers"]});
  }

  static importance(host, m, top = 10) {
    return new HBarChart(host, m.importance.slice(0, top).map(r => ({label: r.feature, value: r.importance})),
      {color: "var(--model)", format: v => v.toFixed(3), valueName: "AUC drop when shuffled"});
  }

  static tierRows(m) {
    return [
      {name: "A · Call first", from: 1, to: 2, action: "Agent call, best offer"},
      {name: "B · Standard", from: 3, to: 5, action: "Standard campaign"},
      {name: "C · Low priority", from: 6, to: 10, action: "Digital only or skip"},
    ].map(x => {
      const ds = m.deciles.filter(d => d.decile >= x.from && d.decile <= x.to);
      const rate = ds.reduce((a, d) => a + d.rate, 0) / ds.length;
      return {...x, rate, lift: rate / m.base_rate, capture: ds.reduce((a, d) => a + d.capture, 0)};
    });
  }

  static tiers(host, m) {
    host.replaceChildren();
    const t = htmlEl("table", null, host);
    let tr = htmlEl("tr", null, t);
    ["Tier", "Customers", "Acceptance", "Lift", "Share of buyers", "Treatment"].forEach((h, i) => htmlEl("th", h, tr, i && i < 5 ? "num" : ""));
    Figures.tierRows(m).forEach(x => {
      tr = htmlEl("tr", null, t);
      htmlEl("td", null, tr).appendChild(htmlEl("b", x.name));
      htmlEl("td", `Top ${(x.from - 1) * 10}–${x.to * 10}%`, tr, "num");
      htmlEl("td", Fmt.pct(x.rate), tr, "num");
      htmlEl("td", x.lift.toFixed(1) + "×", tr, "num");
      htmlEl("td", Fmt.pct(x.capture, 0), tr, "num");
      htmlEl("td", x.action, tr);
    });
  }
}

/** Fill every <div data-fig> and <span data-num> on a page. */
function renderFigurePage(data) {
  document.querySelectorAll("[data-fig]").forEach(el => Figures.render(el.dataset.fig, el, data, el.dataset.slice || "All"));
}
