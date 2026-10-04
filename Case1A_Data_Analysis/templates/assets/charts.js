/* Chart library - small, dependency-free SVG chart classes sharing one base class. */
"use strict";

const SVG_NS = "http://www.w3.org/2000/svg";

const Fmt = {
  n: v => Math.round(v).toLocaleString("en-US"),
  pct: (v, d = 2) => (v * 100).toFixed(d) + "%",
  tick: v => +(v * 100).toFixed(2) + "%",
  compact: v => v >= 1000 ? +(v / 1000).toFixed(1) + "k" : String(Math.round(v)),
  thb: v => v >= 1000 ? +(v / 1000).toFixed(1) + "k" : Math.round(v).toLocaleString("en-US"),
};

function svgEl(tag, attrs = {}, parent = null) {
  const e = document.createElementNS(SVG_NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
}
function htmlEl(tag, text = null, parent = null, cls = "") {
  const e = document.createElement(tag);
  if (text != null) e.textContent = text;
  if (cls) e.className = cls;
  if (parent) parent.appendChild(e);
  return e;
}
function niceMax(v, steps = [0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05, 0.06, 0.08, 0.1]) {
  return steps.find(s => s >= v) || Math.ceil(v * 100) / 100;
}

/* ------------------------------------------------------------------ tooltip */
class Tooltip {
  constructor() {
    this.el = document.getElementById("tip") || htmlEl("div", null, document.body);
    this.el.id = "tip";
    this.el.setAttribute("role", "tooltip");
  }
  show(ev, title, rows) {
    this.el.replaceChildren();
    htmlEl("div", title, this.el, "t");
    rows.forEach(({label, value, color}) => {
      const r = htmlEl("div", null, this.el, "r");
      const k = htmlEl("i", null, r, "lk");
      k.style.background = color || "transparent";
      htmlEl("span", label, r);
      htmlEl("b", value, r);
    });
    this.el.style.display = "block";
    this.move(ev);
  }
  move(ev) {
    const x = Math.min(ev.clientX + 14, innerWidth - this.el.offsetWidth - 8);
    const y = Math.min(ev.clientY + 14, innerHeight - this.el.offsetHeight - 8);
    this.el.style.left = x + "px";
    this.el.style.top = y + "px";
  }
  hide() { this.el.style.display = "none"; }
  /** Attach hover + keyboard focus to a node; content() returns [title, rows]. */
  bind(node, content) {
    node.setAttribute("tabindex", "0");
    node.addEventListener("pointermove", ev => this.show(ev, ...content(ev)));
    node.addEventListener("pointerleave", () => this.hide());
    node.addEventListener("focus", () => {
      const b = node.getBoundingClientRect();
      this.show({clientX: b.left + b.width / 2, clientY: b.top}, ...content(null));
    });
    node.addEventListener("blur", () => this.hide());
  }
}
const tooltip = new Tooltip();

/* ------------------------------------------------------------------ base */
class Chart {
  constructor(host, width = 540, height = 260) {
    this.host = host;
    host.replaceChildren();
    this.W = width;
    this.H = height;
    this.svg = svgEl("svg", {viewBox: `0 0 ${width} ${height}`, role: "img"}, host);
  }
  text(x, y, str, opts = {}, parent = this.svg) {
    const t = svgEl("text", {x, y, "font-size": opts.size || 11, fill: opts.fill || "var(--muted)",
      "text-anchor": opts.anchor || "start", "font-weight": opts.weight || 400}, parent);
    if (opts.halo) { t.setAttribute("stroke", "var(--card)"); t.setAttribute("stroke-width", 4); t.setAttribute("paint-order", "stroke"); }
    t.textContent = str;
    return t;
  }
  line(x1, y1, x2, y2, stroke = "var(--grid)", width = 1, parent = this.svg) {
    return svgEl("line", {x1, y1, x2, y2, stroke, "stroke-width": width}, parent);
  }
  /** Bar path with a 4px rounded data-end; dir = right | up. */
  static barPath(x, y, w, h, dir, round = true) {
    if (w <= 0 || h <= 0) return "";
    if (dir === "right") {
      const r = round ? Math.min(4, w, h / 2) : 0;
      return `M${x},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h - r}Q${x + w},${y + h} ${x + w - r},${y + h}H${x}Z`;
    }
    if (dir === "left") {
      const r = round ? Math.min(4, w, h / 2) : 0;
      return `M${x + w},${y}H${x + r}Q${x},${y} ${x},${y + r}V${y + h - r}Q${x},${y + h} ${x + r},${y + h}H${x + w}Z`;
    }
    const r = round ? Math.min(4, h, w / 2) : 0;
    return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`;
  }
  /** Collapsible accessible table with the same numbers as the chart. */
  table(headers, rows) {
    const d = htmlEl("details", null, this.host);
    htmlEl("summary", "Show table", d);
    const t = htmlEl("table", null, d);
    const hr = htmlEl("tr", null, t);
    headers.forEach((h, i) => htmlEl("th", h, hr, i ? "num" : ""));
    rows.forEach(r => {
      const tr = htmlEl("tr", null, t);
      r.forEach((c, i) => htmlEl("td", c, tr, i ? "num" : ""));
    });
  }
}

/* ------------------------------------------------------------------ stacked horizontal bars (PA + Life) */
class StackedBarChart extends Chart {
  constructor(host, rows, avg) {
    const ROW = 28, TOP = 6;
    super(host, 540, TOP + rows.length * ROW + 22);
    const L = 150, R = 52, BAR = 16, H = this.H;
    const max = niceMax(Math.max(...rows.map(r => (r.pa + r.life) / r.n)) * 1.05);
    const x = v => L + (v / max) * (this.W - L - R);
    [0, max / 2, max].forEach(t => {
      this.line(x(t), TOP, x(t), H - 20);
      this.text(x(t), H - 6, Fmt.tick(t), {anchor: "middle"});
    });
    this.line(x(avg), TOP - 4, x(avg), H - 20, "var(--ink-2)");
    rows.forEach((r, i) => {
      const y = TOP + i * ROW + (ROW - BAR) / 2, pa = r.pa / r.n, life = r.life / r.n;
      const g = svgEl("g", {class: "mark-g"}, this.svg);
      this.text(L - 10, y + BAR / 2 + 4, r.cat, {anchor: "end", size: 12, fill: "var(--ink-2)"}, g);
      const wPa = x(pa) - L, wLife = x(pa + life) - x(pa);
      svgEl("path", {d: Chart.barPath(L, y, wPa, BAR, "right", wLife <= 2), fill: "var(--pa)", class: "mark"}, g);
      if (wLife > 2) svgEl("path", {d: Chart.barPath(L + wPa + 2, y, wLife - 2, BAR, "right"), fill: "var(--life)", class: "mark"}, g);
      this.text(x(pa + life) + 6, y + BAR / 2 + 4, Fmt.pct(pa + life), {size: 11.5, fill: "var(--ink)", weight: 600, halo: true}, g);
      const hit = svgEl("rect", {x: 0, y: TOP + i * ROW, width: this.W, height: ROW, fill: "transparent"}, g);
      tooltip.bind(hit, () => [`${r.cat} · ${Fmt.n(r.n)} customers`, [
        {label: "Total", value: Fmt.pct(pa + life)},
        {label: "PA", value: Fmt.pct(pa), color: "var(--pa)"},
        {label: "Life", value: Fmt.pct(life), color: "var(--life)"}]]);
    });
    this.table(["Group", "Customers", "PA", "Life", "Total"],
      rows.map(r => [r.cat, Fmt.n(r.n), Fmt.pct(r.pa / r.n), Fmt.pct(r.life / r.n), Fmt.pct((r.pa + r.life) / r.n)]));
  }
}

/* ------------------------------------------------------------------ single-series columns */
class ColumnChart extends Chart {
  /** rows: [{label, value, tip}] ; opts: {color, format, max, ref, refLabel, labelAll} */
  constructor(host, rows, opts) {
    super(host, 540, 230);
    const L = 44, B = 22, TOP = 18, H = this.H, n = rows.length;
    const band = (this.W - L) / n, bw = Math.min(24, band * 0.6);
    const max = opts.max;
    const y = v => TOP + (1 - v / max) * (H - TOP - B);
    [0, max / 2, max].forEach(t => {
      this.line(L, y(t), this.W, y(t), t ? "var(--grid)" : "var(--axis)");
      this.text(L - 6, y(t) + 4, opts.format(t), {anchor: "end"});
    });
    if (opts.ref != null) {
      this.line(L, y(opts.ref), this.W, y(opts.ref), "var(--ink-2)");
      this.text(this.W, y(opts.ref) - 4, opts.refLabel, {anchor: "end", fill: "var(--ink-2)"});
    }
    const vals = rows.map(r => r.value);
    const hi = vals.indexOf(Math.max(...vals)), lo = vals.indexOf(Math.min(...vals));
    rows.forEach((r, i) => {
      const cx = L + band * i + band / 2;
      const g = svgEl("g", {class: "mark-g"}, this.svg);
      svgEl("path", {d: Chart.barPath(cx - bw / 2, y(r.value), bw, y(0) - y(r.value), "up"), fill: opts.color, class: "mark"}, g);
      this.text(cx, H - 6, r.label, {anchor: "middle", fill: "var(--ink-2)"}, g);
      if (opts.labelAll || i === hi || i === lo)
        this.text(cx, y(r.value) - 5, opts.format(r.value, true), {anchor: "middle", fill: "var(--ink)", weight: 600, halo: true}, g);
      const hit = svgEl("rect", {x: L + band * i, y: TOP, width: band, height: H - TOP - B, fill: "transparent"}, g);
      tooltip.bind(hit, () => r.tip);
    });
    this.table(opts.headers, rows.map(r => r.row));
  }
}

/* ------------------------------------------------------------------ multi-series line with crosshair */
class LineChart extends Chart {
  /** labels: x labels ; series: [{name, values, color, width, area}] ; opts: {yMax, yFormat, tipTitle, xEvery, diag} */
  constructor(host, labels, series, opts) {
    super(host, 540, opts.height || 240);
    const L = 44, R = 12, B = 24, TOP = 14, H = this.H, n = labels.length;
    const x = i => L + (n === 1 ? 0 : i / (n - 1)) * (this.W - L - R);
    const y = v => TOP + (1 - v / opts.yMax) * (H - TOP - B);
    this.x = x; this.y = y;
    (opts.yTicks || [0, opts.yMax / 2, opts.yMax]).forEach(t => {
      this.line(L, y(t), this.W - R, y(t), t ? "var(--grid)" : "var(--axis)");
      this.text(L - 6, y(t) + 4, opts.yFormat(t), {anchor: "end"});
    });
    labels.forEach((lab, i) => {
      if (i % (opts.xEvery || 1) === 0) this.text(x(i), H - 6, lab, {anchor: "middle", fill: "var(--ink-2)"});
    });
    if (opts.diag) svgEl("line", {x1: x(0), y1: y(0), x2: x(n - 1), y2: y(opts.yMax), stroke: "var(--muted)", "stroke-width": 1.5}, this.svg);
    series.forEach(s => {
      const pts = s.values.map((v, i) => `${x(i)},${y(v)}`).join(" ");
      if (s.area) svgEl("polygon", {points: `${x(0)},${y(0)} ${pts} ${x(n - 1)},${y(0)}`, fill: s.color, opacity: 0.1}, this.svg);
      svgEl("polyline", {points: pts, fill: "none", stroke: s.color, "stroke-width": s.width || 2,
        "stroke-linejoin": "round", "stroke-linecap": "round"}, this.svg);
    });
    // crosshair layer
    const cross = svgEl("g", {style: "display:none", "pointer-events": "none"}, this.svg);
    const vline = this.line(0, TOP, 0, H - B, "var(--axis)", 1, cross);
    const dots = series.map(s => svgEl("circle", {r: 4, fill: s.color, stroke: "var(--card)", "stroke-width": 2}, cross));
    const overlay = svgEl("rect", {x: L, y: TOP, width: this.W - L - R, height: H - TOP - B, fill: "transparent"}, this.svg);
    const nearest = ev => {
      if (!ev) return n - 1;
      const b = this.svg.getBoundingClientRect();
      const px = (ev.clientX - b.left) / b.width * this.W;
      return Math.max(0, Math.min(n - 1, Math.round((px - L) / (this.W - L - R) * (n - 1))));
    };
    tooltip.bind(overlay, ev => {
      const i = nearest(ev);
      cross.style.display = "";
      vline.setAttribute("x1", x(i)); vline.setAttribute("x2", x(i));
      dots.forEach((d, k) => { d.setAttribute("cx", x(i)); d.setAttribute("cy", y(series[k].values[i])); });
      return [opts.tipTitle(labels[i], i), series.filter(s => !s.noTip).map(s => ({label: s.name, value: opts.yFormat(s.values[i], true), color: s.color}))];
    });
    overlay.addEventListener("pointerleave", () => cross.style.display = "none");
    overlay.addEventListener("blur", () => cross.style.display = "none");
    if (opts.table) this.table(opts.table.headers, opts.table.rows);
  }
  /** Direct label at a point (used sparingly: endpoint / highlight). */
  annotate(i, v, str, color) {
    svgEl("circle", {cx: this.x(i), cy: this.y(v), r: 5, fill: color, stroke: "var(--card)", "stroke-width": 2}, this.svg);
    this.text(this.x(i) + 9, this.y(v) + 14, str, {fill: "var(--ink)", weight: 600, size: 12, halo: true});
  }
}

/* ------------------------------------------------------------------ heatmap */
class HeatmapChart extends Chart {
  static RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"];
  static color(t) {
    const R = HeatmapChart.RAMP, p = Math.max(0, Math.min(1, t)) * (R.length - 1), i = Math.floor(p), f = p - i;
    const a = R[i], b = R[Math.min(i + 1, R.length - 1)];
    const ch = (h, k) => parseInt(h.slice(1 + 2 * k, 3 + 2 * k), 16);
    return "#" + [0, 1, 2].map(k => Math.round(ch(a, k) + (ch(b, k) - ch(a, k)) * f).toString(16).padStart(2, "0")).join("");
  }
  constructor(host, hm) {
    const L = 64, TOP = 26, CH = 34;
    super(host, 540, TOP + hm.rows.length * CH + 58);
    const CW = (this.W - L) / hm.cols.length;
    const rates = hm.cells.filter(c => c.rate != null).map(c => c.rate);
    const lo = Math.min(...rates), hi = Math.max(...rates);
    this.text(L + (this.W - L) / 2, 10, `${hm.col_title} (THB / month) →`, {anchor: "middle", fill: "var(--ink-2)"});
    hm.cols.forEach((c, j) => this.text(L + CW * j + CW / 2, TOP - 4, c, {anchor: "middle"}));
    hm.rows.forEach((r, i) => this.text(L - 8, TOP + CH * i + CH / 2 + 4, r, {anchor: "end", fill: "var(--ink-2)"}));
    this.text(4, TOP - 4, hm.row_title + " ↓", {fill: "var(--ink-2)"});
    hm.cells.forEach(c => {
      const i = hm.rows.indexOf(c.r), j = hm.cols.indexOf(c.c);
      const g = svgEl("g", {class: "mark-g"}, this.svg);
      const t = c.rate == null ? null : (c.rate - lo) / (hi - lo);
      svgEl("rect", {x: L + CW * j + 1, y: TOP + CH * i + 1, width: CW - 2, height: CH - 2, rx: 3,
        fill: t == null ? "var(--grid)" : HeatmapChart.color(t), class: "mark"}, g);
      this.text(L + CW * j + CW / 2, TOP + CH * i + CH / 2 + 4, c.rate == null ? "–" : Fmt.pct(c.rate, 1),
        {anchor: "middle", size: 11, fill: t == null ? "var(--muted)" : t > 0.45 ? "#ffffff" : "#0b0b0b", weight: 600}, g);
      const hit = svgEl("rect", {x: L + CW * j, y: TOP + CH * i, width: CW, height: CH, fill: "transparent"}, g);
      tooltip.bind(hit, () => [`Age ${c.r} · income ${c.c}`, [
        {label: "Acceptance", value: c.rate == null ? "too few customers" : Fmt.pct(c.rate)},
        {label: "Customers", value: Fmt.n(c.n)}]]);
    });
    // scale legend
    const ly = TOP + hm.rows.length * CH + 18, lw = 200, lx = this.W - lw;
    const defs = svgEl("defs", {}, this.svg);
    const grad = svgEl("linearGradient", {id: "hm-grad-" + Math.random().toString(36).slice(2)}, defs);
    HeatmapChart.RAMP.forEach((c, k) => svgEl("stop", {offset: k / (HeatmapChart.RAMP.length - 1), "stop-color": c}, grad));
    svgEl("rect", {x: lx, y: ly, width: lw, height: 8, rx: 2, fill: `url(#${grad.id})`}, this.svg);
    this.text(lx, ly + 22, Fmt.pct(lo, 1), {});
    this.text(lx + lw, ly + 22, Fmt.pct(hi, 1), {anchor: "end"});
    this.text(lx - 8, ly + 8, "Acceptance rate", {anchor: "end"});
    this.text(L, ly + 8, "– = fewer than 300 customers", {});
    this.table(["Age", "Income", "Customers", "Acceptance"],
      hm.cells.map(c => [c.r, c.c, Fmt.n(c.n), c.rate == null ? "–" : Fmt.pct(c.rate)]));
  }
}

/* ------------------------------------------------------------------ bubble / opportunity matrix */
class BubbleChart extends Chart {
  /** points: [{cat, series, n, buyers, rate}] ; colors: {series: cssColor} */
  constructor(host, points, colors, avg) {
    super(host, 540, 300);
    const L = 48, R = 16, TOP = 14, B = 34, H = this.H;
    const xMin = 300, xMax = Math.max(...points.map(p => p.n)) * 1.3;
    const yMax = niceMax(Math.max(...points.map(p => p.rate)) * 1.12);
    const lx = v => L + (Math.log10(v) - Math.log10(xMin)) / (Math.log10(xMax) - Math.log10(xMin)) * (this.W - L - R);
    const y = v => TOP + (1 - v / yMax) * (H - TOP - B);
    const rMax = Math.max(...points.map(p => p.buyers));
    const r = b => 4 + Math.sqrt(b / rMax) * 16;
    [0, yMax / 2, yMax].forEach(t => {
      this.line(L, y(t), this.W - R, y(t), t ? "var(--grid)" : "var(--axis)");
      this.text(L - 6, y(t) + 4, Fmt.tick(t), {anchor: "end"});
    });
    [500, 1000, 2000, 5000, 10000, 20000, 50000].filter(v => v < xMax).forEach(v => {
      this.line(lx(v), TOP, lx(v), H - B);
      this.text(lx(v), H - B + 14, Fmt.compact(v), {anchor: "middle"});
    });
    this.text(L + (this.W - L - R) / 2, H - 4, "Customers contacted (log scale) →", {anchor: "middle", fill: "var(--ink-2)"});
    this.line(L, y(avg), this.W - R, y(avg), "var(--ink-2)");
    this.text(L + 4, y(avg) - 4, "average " + Fmt.pct(avg), {fill: "var(--ink-2)", halo: true});
    [...points].sort((a, b) => b.buyers - a.buyers).forEach(p => {
      const g = svgEl("g", {class: "mark-g"}, this.svg);
      svgEl("circle", {cx: lx(p.n), cy: y(p.rate), r: r(p.buyers), fill: colors[p.series], "fill-opacity": 0.75,
        stroke: "var(--card)", "stroke-width": 2, class: "mark"}, g);
      const hit = svgEl("circle", {cx: lx(p.n), cy: y(p.rate), r: Math.max(12, r(p.buyers)), fill: "transparent"}, g);
      tooltip.bind(hit, () => [`Age ${p.cat} · ${p.series}`, [
        {label: "Acceptance", value: Fmt.pct(p.rate), color: colors[p.series]},
        {label: "Customers", value: Fmt.n(p.n)}, {label: "Buyers", value: Fmt.n(p.buyers)}]]);
    });
    // label the highest-rate and biggest-buyer bubbles, skipping any label that would collide
    const pick = [...new Set([...[...points].sort((a, b) => b.rate - a.rate).slice(0, 3),
                              ...[...points].sort((a, b) => b.buyers - a.buyers).slice(0, 2)])];
    const placed = [];
    pick.forEach(p => {
      const str = `${p.cat} · ${p.series}`, w = str.length * 6, cx = lx(p.n), rad = r(p.buyers);
      const right = cx + rad + 4 + w <= this.W - R;
      const box = {x1: right ? cx + rad + 4 : cx - rad - 4 - w, y1: y(p.rate) - 8};
      box.x2 = box.x1 + w; box.y2 = box.y1 + 14;
      if (placed.some(b => box.x1 < b.x2 && box.x2 > b.x1 && box.y1 < b.y2 && box.y2 > b.y1)) return;
      placed.push(box);
      this.text(right ? box.x1 : box.x2, y(p.rate) + 4, str, {fill: "var(--ink)", size: 11, halo: true, anchor: right ? "start" : "end"});
    });
    this.table(["Age · segment", "Customers", "Buyers", "Acceptance"],
      points.map(p => [`${p.cat} · ${p.series}`, Fmt.n(p.n), Fmt.n(p.buyers), Fmt.pct(p.rate)]));
  }
}

/* ------------------------------------------------------------------ diverging bars around an index of 100 */
class DivergingBarChart extends Chart {
  constructor(host, rows) {
    const ROW = 22, TOP = 8;
    super(host, 540, TOP + rows.length * ROW + 26);
    const L = 180, R = 40, BAR = 14, H = this.H;
    const ext = Math.max(...rows.map(r => Math.abs(r.index - 100))) * 1.1;
    const mid = L + (this.W - L - R) / 2;
    const x = d => mid + d / ext * (this.W - L - R) / 2;
    [-50, 0, 50].filter(d => Math.abs(d) <= ext).forEach(d => {
      this.line(x(d), TOP, x(d), H - 20, d ? "var(--grid)" : "var(--axis)");
      this.text(x(d), H - 6, String(100 + d), {anchor: "middle"});
    });
    rows.forEach((r, i) => {
      const yy = TOP + i * ROW + (ROW - BAR) / 2, d = r.index - 100, pos = d >= 0;
      const g = svgEl("g", {class: "mark-g"}, this.svg);
      this.text(L - 10, yy + BAR / 2 + 4, r.cat, {anchor: "end", size: 11.5, fill: "var(--ink-2)"}, g);
      const w = Math.abs(x(d) - mid);
      svgEl("path", {d: Chart.barPath(pos ? mid : mid - w, yy, w, BAR, pos ? "right" : "left"),
        fill: pos ? "var(--pos)" : "var(--neg)", class: "mark"}, g);
      this.text(pos ? x(d) + 5 : x(d) - 5, yy + BAR / 2 + 4, Math.round(r.index), {anchor: pos ? "start" : "end", fill: "var(--ink)", weight: 600, halo: true}, g);
      const hit = svgEl("rect", {x: 0, y: TOP + i * ROW, width: this.W, height: ROW, fill: "transparent"}, g);
      tooltip.bind(hit, () => [r.cat, [{label: "Index (avg = 100)", value: Math.round(r.index), color: pos ? "var(--pos)" : "var(--neg)"},
        {label: "Acceptance", value: Fmt.pct(r.rate)}, {label: "Customers", value: Fmt.n(r.n)}]]);
    });
    if (rows.length > 8) this.line(0, TOP + (rows.length / 2) * ROW, this.W, TOP + (rows.length / 2) * ROW, "var(--grid)");
    this.table(["Group", "Index", "Acceptance", "Customers"], rows.map(r => [r.cat, Math.round(r.index), Fmt.pct(r.rate), Fmt.n(r.n)]));
  }
}

/* ------------------------------------------------------------------ dot + IQR range */
class DotRangeChart extends Chart {
  /** metric: {metric, groups: [{outcome, p25, median, p75, n}]} ; colors: {outcome: css} */
  constructor(host, metric, colors) {
    const ROW = 34, TOP = 6;
    super(host, 360, TOP + metric.groups.length * ROW + 24);
    const L = 74, R = 20, H = this.H;
    const max = Math.max(...metric.groups.map(g => g.p75)) * 1.1;
    const x = v => L + v / max * (this.W - L - R);
    [0, max / 2, max].forEach(t => {
      this.line(x(t), TOP, x(t), H - 20);
      this.text(x(t), H - 6, Fmt.thb(t), {anchor: "middle"});
    });
    metric.groups.forEach((g, i) => {
      const yy = TOP + i * ROW + ROW / 2, c = colors[g.outcome];
      const grp = svgEl("g", {class: "mark-g"}, this.svg);
      this.text(L - 10, yy + 4, g.outcome, {anchor: "end", size: 12, fill: "var(--ink-2)"}, grp);
      svgEl("line", {x1: x(g.p25), x2: x(g.p75), y1: yy, y2: yy, stroke: c, "stroke-width": 6, "stroke-linecap": "round", opacity: 0.35, class: "mark"}, grp);
      svgEl("circle", {cx: x(g.median), cy: yy, r: 6, fill: c, stroke: "var(--card)", "stroke-width": 2, class: "mark"}, grp);
      this.text(x(g.median), yy - 10, Fmt.thb(g.median), {anchor: "middle", fill: "var(--ink)", weight: 600, halo: true}, grp);
      const hit = svgEl("rect", {x: 0, y: TOP + i * ROW, width: this.W, height: ROW, fill: "transparent"}, grp);
      tooltip.bind(hit, () => [`${metric.metric} · ${g.outcome}`, [
        {label: "Median", value: Fmt.n(g.median), color: c}, {label: "25th pct", value: Fmt.n(g.p25)},
        {label: "75th pct", value: Fmt.n(g.p75)}]]);
    });
    this.table(["Outcome", "25th pct", "Median", "75th pct"], metric.groups.map(g => [g.outcome, Fmt.n(g.p25), Fmt.n(g.median), Fmt.n(g.p75)]));
  }
}

/* ------------------------------------------------------------------ single-series horizontal bars */
class HBarChart extends Chart {
  constructor(host, rows, opts) {
    const ROW = 24, TOP = 4;
    super(host, 540, TOP + rows.length * ROW + 22);
    const L = 170, R = 56, BAR = 14, H = this.H;
    const max = Math.max(...rows.map(r => r.value)) * 1.05;
    const x = v => L + v / max * (this.W - L - R);
    [0, max / 2, max].forEach(t => {
      this.line(x(t), TOP, x(t), H - 20);
      this.text(x(t), H - 6, opts.format(t), {anchor: "middle"});
    });
    rows.forEach((r, i) => {
      const yy = TOP + i * ROW + (ROW - BAR) / 2;
      const g = svgEl("g", {class: "mark-g"}, this.svg);
      this.text(L - 10, yy + BAR / 2 + 4, r.label, {anchor: "end", size: 12, fill: "var(--ink-2)"}, g);
      svgEl("path", {d: Chart.barPath(L, yy, Math.max(1, x(r.value) - L), BAR, "right"), fill: opts.color, class: "mark"}, g);
      this.text(x(r.value) + 6, yy + BAR / 2 + 4, opts.format(r.value), {fill: "var(--ink)", weight: 600, halo: true}, g);
      const hit = svgEl("rect", {x: 0, y: TOP + i * ROW, width: this.W, height: ROW, fill: "transparent"}, g);
      tooltip.bind(hit, () => [r.label, [{label: opts.valueName, value: opts.format(r.value), color: opts.color}]]);
    });
    this.table(["Feature", opts.valueName], rows.map(r => [r.label, opts.format(r.value)]));
  }
}

/* ------------------------------------------------------------------ sparkline (hero tile) */
class Sparkline {
  constructor(host, values, color) {
    const W = 140, H = 44;
    const svg = svgEl("svg", {viewBox: `0 0 ${W} ${H}`, width: W, height: H, "aria-hidden": "true"}, host);
    const max = Math.max(...values), min = Math.min(...values);
    const x = i => 2 + i / (values.length - 1) * (W - 8), y = v => 4 + (1 - (v - min) / (max - min || 1)) * (H - 10);
    svgEl("polyline", {points: values.map((v, i) => `${x(i)},${y(v)}`).join(" "), fill: "none", stroke: "var(--muted)",
      "stroke-width": 1.5, "stroke-linejoin": "round"}, svg);
    const last = values.length - 1;
    svgEl("circle", {cx: x(last), cy: y(values[last]), r: 3.5, fill: color, stroke: "var(--card)", "stroke-width": 2}, svg);
  }
}
