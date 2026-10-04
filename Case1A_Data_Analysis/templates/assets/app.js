/* Dashboard controller - renders every section from the DATA payload and wires the segment filter. */
"use strict";

class Dashboard {
  constructor(data) {
    this.data = data;
    this.$ = id => document.getElementById(id);
  }

  init() {
    this.renderStatic();
    this.bindFilter();
    this.renderSlice("All");
  }

  bindFilter() {
    const buttons = document.querySelectorAll(".filters button");
    buttons.forEach(b => b.addEventListener("click", () => {
      buttons.forEach(x => x.setAttribute("aria-pressed", x === b));
      this.renderSlice(b.dataset.slice);
    }));
  }

  /* ------------------------------------------------------------ filtered sections */
  renderSlice(name) {
    const s = this.data.slices[name];
    const avg = (s.kpi.pa + s.kpi.life) / s.kpi.n;
    const scope = name === "All" ? "all customers" : name;
    document.querySelectorAll("[data-scope]").forEach(e => e.textContent = scope);
    this.renderTiles(s);
    const fig = (figure, id) => Figures.render(figure, this.$(id), this.data, name);
    fig("volume", "c-volume");
    fig("rate", "c-rate");
    fig("heatmap", "c-heatmap");
    fig("bubble", "c-bubble");
    fig("lift", "c-lift");
    fig("agedist", "c-agedist");
    s.ranges.forEach((_, i) => fig("range:" + i, "c-range-" + i));
    this.renderProfiles(s, avg, name);
  }

  renderTiles(s) {
    const host = this.$("tiles"), k = s.kpi, acc = k.pa + k.life;
    host.replaceChildren();
    const tile = (label, value, sub, cls = "", color = null) => {
      const t = htmlEl("div", null, host, "tile " + cls);
      const l = htmlEl("div", null, t, "label");
      if (color) htmlEl("i", null, l, "key").style.background = color;
      l.appendChild(document.createTextNode(label));
      htmlEl("div", value, t, "value");
      htmlEl("div", sub, t, "sub");
      return t;
    };
    const hero = tile("Acceptance rate", Fmt.pct(acc / k.n), `${Fmt.n(acc)} of ${Fmt.n(k.n)} customers bought · trend Jan→Dec`, "hero");
    new Sparkline(htmlEl("div", null, hero, "spark"), s.month.map(r => (r.pa + r.life) / r.n), "var(--ink)");
    tile("Customers contacted", Fmt.n(k.n), "offers across 12 campaign months");
    tile("PA insurance", Fmt.pct(k.pa / k.n), `${Fmt.n(k.pa)} policies sold`, "", "var(--pa)");
    tile("Life insurance", Fmt.pct(k.life / k.n), `${Fmt.n(k.life)} policies sold`, "", "var(--life)");
    tile("Product mix", `${Math.round(k.pa / acc * 100)} / ${Math.round(k.life / acc * 100)}`, "PA / Life share of sales");
  }

  renderProfiles(s, avg, name) {
    const host = this.$("profile-charts");
    host.replaceChildren();
    Object.entries(s.profile).forEach(([k, rows]) => {
      if (name !== "All" && k === "segment") return;
      const c = htmlEl("div", null, host, "card");
      htmlEl("h3", this.data.titles[k], c);
      htmlEl("div", `Acceptance rate · ${name === "All" ? "all customers" : name}`, c, "cap");
      Figures.render("profile:" + k, htmlEl("div", null, c), this.data, name);
    });
  }

  /* ------------------------------------------------------------ unfiltered sections */
  renderStatic() {
    this.renderModel();
    this.renderProfileTable();
    this.renderDataset();
  }

  renderModel() {
    const m = this.data.model;
    const top10 = m.deciles[0];
    this.$("model-finding").textContent =
      `Contacting only the top 20% of customers ranked by the model would reach ${Math.round(m.top20_capture)}% of buyers. ` +
      `The top 10% buy at ${Fmt.pct(top10.rate, 1)}, ${top10.lift.toFixed(1)}× the average (ROC-AUC ${m.roc_auc.toFixed(2)}).`;

    const host = this.$("model-tiles");
    [["ROC-AUC", m.roc_auc.toFixed(3), "0.5 = random · 1.0 = perfect"],
     ["Top 20% captures", Math.round(m.top20_capture) + "%", "of all buyers in the test set"],
     ["Top-decile lift", top10.lift.toFixed(1) + "×", `${Fmt.pct(top10.rate, 1)} vs ${Fmt.pct(m.base_rate, 1)} average`],
     ["PR-AUC", m.pr_auc.toFixed(3), `${(m.pr_auc / m.base_rate).toFixed(1)}× the ${Fmt.pct(m.base_rate, 1)} baseline`]]
      .forEach(([l, v, s]) => {
        const t = htmlEl("div", null, host, "tile");
        htmlEl("div", l, t, "label"); htmlEl("div", v, t, "value"); htmlEl("div", s, t, "sub");
      });

    Figures.gains(this.$("c-gains"), m);
    Figures.deciles(this.$("c-deciles"), m);
    Figures.importance(this.$("c-importance"), m, 10);
    Figures.tiers(this.$("tiers"), m);
  }

  renderProfileTable() {
    const p = this.data.profiles, cols = Object.keys(p), t = this.$("profiles");
    let tr = htmlEl("tr", null, t);
    htmlEl("th", "Measure", tr);
    cols.forEach(c => htmlEl("th", c, tr, "num"));
    Object.keys(p[cols[0]]).forEach(m => {
      tr = htmlEl("tr", null, t);
      htmlEl("td", m, tr);
      cols.forEach(c => htmlEl("td", p[c][m], tr, "num"));
    });
  }

  renderDataset() {
    const q = this.data.quality, raw = this.data.raw_kpi, ds = this.$("ds-tiles");
    [["Rows", Fmt.n(q.n_rows), `${Fmt.n(raw.analysed)} analysed after cleaning`], ["Columns", String(q.n_cols), "25 features + label"],
     ["Campaign months", "12", "Jan–Dec, no year given"], ["Target (label)", "3 classes", "0 Reject · 1 PA · 2 Life"]]
      .forEach(([l, v, s]) => {
        const d = htmlEl("div", null, ds, "tile");
        htmlEl("div", l, d, "label"); htmlEl("div", v, d, "value"); htmlEl("div", s, d, "sub");
      });

    const st = this.$("summary");
    let tr = htmlEl("tr", null, st);
    ["Field", "Type", "Definition", "Missing", "Profile"].forEach((c, i) => htmlEl("th", c, tr, i === 3 ? "num" : ""));
    q.fields.forEach(f => {
      tr = htmlEl("tr", null, st);
      htmlEl("td", null, tr).appendChild(htmlEl("code", f.field));
      htmlEl("td", f.dtype, tr);
      htmlEl("td", f.definition, tr);
      htmlEl("td", f.missing ? `${Fmt.n(f.missing)} (${f.missing_pct}%)` : "–", tr, "num");
      htmlEl("td", f.profile, tr);
    });

    const ul = this.$("dq");
    q.issues.forEach(i => {
      const li = htmlEl("li", null, ul);
      htmlEl("span", i.category, li, "tag");
      li.appendChild(document.createTextNode(i.description));
    });
  }
}

new Dashboard(DATA).init();
