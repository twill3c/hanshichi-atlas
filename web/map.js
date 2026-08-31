/* 半七アトラス — 捜査圏(F-09)
 *
 * 下敷きの地図タイルは使わない。外部へ取りに行かない静的ページのままにするためでもあり、
 * 現代の地図を敷くと「江戸の地図」に見えてしまうためでもある。点の位置は経緯度そのもの。
 *
 * ラベルは図を描いたのと同じデータから置き、重なったら出さない(HC-045)。
 */
'use strict';

const SVG_NS = 'http://www.w3.org/2000/svg';
const el = (name, attrs = {}, parent = null) => {
  const n = document.createElementNS(SVG_NS, name);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  if (parent) parent.appendChild(n);
  return n;
};
const fmt = (n) => n.toLocaleString('ja-JP');

/** 半七の家を含む町。三河町そのものは辞書に無い。 */
const ANCHOR = '神田';

/** 言及で重みを付けた分位で「核」の枠を決める。外れ値に枠を引っぱらせない。 */
function coreBox(places, q = 0.06) {
  const spread = (key) => {
    const xs = [];
    for (const p of places) for (let i = 0; i < p.mentions; i++) xs.push(p[key]);
    xs.sort((a, b) => a - b);
    const lo = xs[Math.floor(xs.length * q)];
    const hi = xs[Math.min(xs.length - 1, Math.ceil(xs.length * (1 - q)))];
    return [lo, hi];
  };
  const [lat0, lat1] = spread('lat');
  const [lon0, lon1] = spread('lon');
  const padLat = (lat1 - lat0) * 0.12, padLon = (lon1 - lon0) * 0.12;
  return { lat0: lat0 - padLat, lat1: lat1 + padLat, lon0: lon0 - padLon, lon1: lon1 + padLon };
}

const inBox = (p, b) => p.lat >= b.lat0 && p.lat <= b.lat1 && p.lon >= b.lon0 && p.lon <= b.lon1;

function draw(svg, places, opts) {
  svg.textContent = '';
  const t = el('title', {}, svg);
  t.textContent = '半七捕物帳に出る江戸の地名の配置';

  const W = 940;
  const M = { l: 16, r: 16, t: 16, b: 34 };
  const lats = places.map((p) => p.lat);
  const lons = places.map((p) => p.lon);
  const box = opts.box || {
    lat0: Math.min(...lats), lat1: Math.max(...lats),
    lon0: Math.min(...lons), lon1: Math.max(...lons),
  };
  const { lat0, lat1, lon0, lon1 } = box;
  /* 緯度による経度の縮みを入れて、南北と東西の縮尺を合わせる */
  const k = Math.cos(((lat0 + lat1) / 2) * Math.PI / 180);
  const innerW = W - M.l - M.r;
  const scale = innerW / ((lon1 - lon0) * k);
  const innerH = (lat1 - lat0) * scale;
  const H = innerH + M.t + M.b;
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('height', H);

  const sx = (lon) => M.l + (lon - lon0) * k * scale;
  const sy = (lat) => M.t + (lat1 - lat) * scale;

  /* 目盛り —— 縮尺が分からない図は読めない */
  const km = 2;
  const barPx = (km / 111.32 / k) * scale;
  const g0 = el('g', {}, svg);
  const by = H - M.b + 16;
  el('line', { x1: M.l, x2: M.l + barPx, y1: by, y2: by, stroke: 'var(--ink-3)', 'stroke-width': 2 }, g0);
  for (const x of [M.l, M.l + barPx]) {
    el('line', { x1: x, x2: x, y1: by - 4, y2: by + 4, stroke: 'var(--ink-3)', 'stroke-width': 2 }, g0);
  }
  const lab = el('text', { x: M.l + barPx + 8, y: by + 4, class: 'axis' }, g0);
  lab.setAttribute('fill', 'var(--ink-3)');
  lab.setAttribute('font-size', '11');
  lab.textContent = `${km} km`;

  const rOf = (n) => 3 + Math.sqrt(n) * 1.6;
  const sorted = places.slice().sort((a, b) => b.mentions - a.mentions);

  /* 点 */
  const gp = el('g', {}, svg);
  for (const p of sorted) {
    const on = !opts.highlight || opts.highlight.has(p.label);
    const c = el('circle', {
      cx: sx(p.lon), cy: sy(p.lat), r: rOf(p.mentions),
      class: 'dot',
      fill: p.label === ANCHOR ? 'none' : 'var(--edo)',
      stroke: p.label === ANCHOR ? 'var(--accent)' : 'var(--bg)',
      'stroke-width': p.label === ANCHOR ? 2.5 : 1.2,
      opacity: on ? 0.85 : 0.16,
      tabindex: '0',
    }, gp);
    c.dataset.label = p.label;
    c.dataset.detail = `${fmt(p.mentions)} 回 / ${p.stories.length} 話`;
  }

  /* ラベル —— 他のラベルにも**点の丸**にも重ならないときだけ出す。
   * ラベル同士だけを見ていたときは、文字が別の丸の上に乗った(実測 2026-09-01)。 */
  const boxes = sorted.map((p) => {
    const r = rOf(p.mentions);
    return { x: sx(p.lon) - r, y: sy(p.lat) - r, w: r * 2, h: r * 2 };
  });
  const overlaps = (b) => boxes.some((o) =>
    b.x < o.x + o.w && b.x + b.w > o.x && b.y < o.y + o.h && b.y + b.h > o.y);
  const gl = el('g', {}, svg);
  let placed = 0;
  for (const p of sorted) {
    if (opts.highlight && !opts.highlight.has(p.label)) continue;
    const x = sx(p.lon) + rOf(p.mentions) + 4;
    const y = sy(p.lat) + 4;
    const w = p.label.length * 11 + 2;
    const box = { x, y: y - 10, w, h: 13 };
    if (x + w > W - M.r || overlaps(box)) continue;
    boxes.push(box);
    placed += 1;
    const tx = el('text', { x, y, class: 'lane-label' }, gl);
    tx.setAttribute('font-size', '11');
    tx.textContent = p.label;
  }
  if (opts.frame) {
    el('rect', {
      x: sx(opts.frame.lon0), y: sy(opts.frame.lat1),
      width: sx(opts.frame.lon1) - sx(opts.frame.lon0),
      height: sy(opts.frame.lat0) - sy(opts.frame.lat1),
      fill: 'none', stroke: 'var(--accent)', 'stroke-width': 1.5, 'stroke-dasharray': '4 3',
    }, svg);
  }
  return { labelled: placed };
}

function wireTips(root) {
  const tip = document.getElementById('tip');
  const show = (t, x, y) => {
    tip.innerHTML = '';
    const b = document.createElement('b');
    b.textContent = t.dataset.label;
    tip.appendChild(b);
    const q = document.createElement('span');
    q.className = 'q';
    q.textContent = t.dataset.detail;
    tip.appendChild(q);
    tip.hidden = false;
    const r = tip.getBoundingClientRect();
    tip.style.left = Math.min(Math.max(8, x - r.width / 2), window.innerWidth - r.width - 8) + 'px';
    tip.style.top = (y - r.height - 12 < 8 ? y + 18 : y - r.height - 12) + 'px';
  };
  root.addEventListener('mouseover', (e) => {
    const t = e.target.closest('.dot');
    if (t) show(t, e.clientX, e.clientY);
  });
  root.addEventListener('mousemove', (e) => {
    const t = e.target.closest('.dot');
    if (t && !tip.hidden) show(t, e.clientX, e.clientY);
  });
  root.addEventListener('mouseout', (e) => { if (e.target.closest('.dot')) tip.hidden = true; });
  root.addEventListener('focusin', (e) => {
    const t = e.target.closest('.dot');
    if (!t) return;
    const r = t.getBoundingClientRect();
    show(t, r.left + r.width / 2, r.top);
  });
  root.addEventListener('focusout', () => { tip.hidden = true; });
}

function list(title, items) {
  const wrap = document.createElement('div');
  const h = document.createElement('p');
  h.className = 'note';
  h.innerHTML = '';
  h.textContent = title;
  const ul = document.createElement('p');
  ul.className = 'evidence';
  ul.textContent = items.join('、');
  wrap.append(h, ul);
  return wrap;
}

async function main() {
  const data = await (await fetch('data/index.json')).json();
  const P = data.places;
  const svg = document.getElementById('map-chart');

  const tiles = [
    [String(P.mapped.length), '', '置けた地名'],
    [fmt(P.mentions), '回', 'その延べ言及'],
    [String(P.unresolved.length + P.not_in_gazetteer.length), '', '置けなかった地名'],
    [String(P.rejected), '', '地名として採らなかった見出し語'],
  ];
  const tw = document.getElementById('tiles');
  for (const [v, unit, k] of tiles) {
    const d = document.createElement('div');
    d.className = 'tile';
    const vv = document.createElement('div');
    vv.className = 'v';
    vv.textContent = v;
    if (unit) { const s = document.createElement('small'); s.textContent = unit; vv.appendChild(s); }
    const kk = document.createElement('div');
    kk.className = 'k';
    kk.textContent = k;
    d.append(vv, kk);
    tw.appendChild(d);
  }

  const sel = document.getElementById('storysel');
  for (const s of data.stories) {
    const o = document.createElement('option');
    o.value = s.no;
    o.textContent = `${s.no} ${s.title}`;
    sel.appendChild(o);
  }

  const wide = document.getElementById('wide-chart');
  const core = coreBox(P.mapped);
  const inner = P.mapped.filter((p) => inBox(p, core));
  const coreMentions = inner.reduce((a, p) => a + p.mentions, 0);

  const render = () => {
    const no = sel.value;
    const highlight = no ? new Set(P.by_story[no].map((m) => m.label)) : null;
    const r = draw(svg, inner, { highlight, box: core });
    const pct = Math.round((coreMentions / P.mentions) * 100);
    document.getElementById('map-caption').textContent =
      `この枠に ${inner.length} 地名 / 延べ ${fmt(coreMentions)} 回(全体の ${pct}%)。`
      + `名前を出したのは ${r.labelled} 件で、丸に重なる分は出していない。丸の大きさは言及の多さ。`;
    const rw = draw(wide, P.mapped, { highlight, frame: core });
    document.getElementById('wide-caption').textContent =
      `置けた地名 ${P.mapped.length} 件すべて / 延べ ${fmt(P.mentions)} 回。名前を出したのは ${rw.labelled} 件。`;
    document.getElementById('storynote').textContent = no
      ? `この話に出る地名 ${highlight.size} 件`
      : '';
  };
  sel.addEventListener('change', render);
  render();
  wireTips(document.body);

  const tb = document.querySelector('#ptbl tbody');
  for (const p of P.mapped) {
    const tr = document.createElement('tr');
    for (const v of [p.label, fmt(p.mentions), String(p.stories.length), p.lat.toFixed(4), p.lon.toFixed(4), p.qids.join(' ')]) {
      const td = document.createElement('td');
      td.textContent = v;
      tr.appendChild(td);
    }
    tr.children[1].className = 'num';
    tr.children[2].className = 'num';
    tb.appendChild(tr);
  }
  document.getElementById('mapped-note').textContent =
    `座標はすべて Wikidata の地物のもので、Q 番号を添えてある。${P.method}。`;

  const miss = document.getElementById('missing');
  miss.appendChild(list(
    `辞書に無い地名(${P.not_in_gazetteer.length}件) —— 半七の家である神田三河町がここに入る`,
    P.not_in_gazetteer));
  if (P.unresolved.length) {
    miss.appendChild(list(
      `同名の地物が離れて複数あり、座標を一つに決められなかった地名(${P.unresolved.length}件)`,
      P.unresolved.map((u) => u.label)));
  }

  const rt = document.querySelector('#rtbl tbody');
  for (const r of P.rejected_examples) {
    const tr = document.createElement('tr');
    for (const v of [r.label, r.reason]) {
      const td = document.createElement('td');
      td.textContent = v;
      tr.appendChild(td);
    }
    rt.appendChild(tr);
  }
  document.getElementById('reject-note').textContent =
    `本文に当たった見出し語のうち ${P.rejected} 件は地名として採らなかった。`
    + `部分文字列・人名・屋号・普通名詞、そして座標が本文の指す場所と違うもの。理由をすべて書いてある。`;
}

main();
