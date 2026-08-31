/* 半七アトラス — ルビの地層(F-10)
 *
 * 図は散布図が一枚だけ。系統は一つなので凡例は置かない(題が何を描いているかを言う)。
 * 軸の目盛りも figcaption も、図を描いたのと同じデータから出す(HC-045)。
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
const pct = (x) => (x * 100).toFixed(1) + '%';

/** 目盛りの刻みを、値の幅から決める。決め打ちしない。 */
function ticks(lo, hi, want = 5) {
  const raw = (hi - lo) / want;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) || mag * 10;
  const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) out.push(Math.round(v));
  return out;
}

function scatter(svg, stories) {
  svg.textContent = '';
  const t = el('title', {}, svg);
  t.textContent = '話ごとの字数とルビ数の散布図';

  const W = 940, H = 460;
  const M = { l: 62, r: 18, t: 14, b: 46 };
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('height', H);

  const xs = stories.map((s) => s.chars), ys = stories.map((s) => s.ruby);
  const x1 = Math.max(...xs) * 1.04, y1 = Math.max(...ys) * 1.06;
  const sx = (v) => M.l + (v / x1) * (W - M.l - M.r);
  const sy = (v) => H - M.b - (v / y1) * (H - M.t - M.b);

  const g = el('g', { class: 'axis' }, svg);
  el('line', { x1: M.l, x2: W - M.r, y1: H - M.b, y2: H - M.b }, g);
  el('line', { x1: M.l, x2: M.l, y1: M.t, y2: H - M.b }, g);
  for (const v of ticks(0, x1, 5)) {
    el('line', { x1: sx(v), x2: sx(v), y1: H - M.b, y2: H - M.b + 4 }, g);
    const tx = el('text', { x: sx(v), y: H - M.b + 18, 'text-anchor': 'middle' }, g);
    tx.textContent = fmt(v);
  }
  for (const v of ticks(0, y1, 5)) {
    el('line', { x1: M.l - 4, x2: W - M.r, y1: sy(v), y2: sy(v), opacity: v ? 0.35 : 1 }, g);
    const tx = el('text', { x: M.l - 8, y: sy(v) + 4, 'text-anchor': 'end' }, g);
    tx.textContent = fmt(v);
  }
  const xl = el('text', { x: (M.l + W - M.r) / 2, y: H - 6, 'text-anchor': 'middle', class: 'axis' }, g);
  xl.setAttribute('fill', 'var(--ink-3)');
  xl.textContent = '本文の字数';
  const yl = el('text', { x: 14, y: (M.t + H - M.b) / 2, class: 'axis', transform: `rotate(-90 14 ${(M.t + H - M.b) / 2})`, 'text-anchor': 'middle' }, g);
  yl.setAttribute('fill', 'var(--ink-3)');
  yl.textContent = 'ルビの数';

  /* 全体の比を通る直線 —— 各点がそこからどれだけ離れるかを見るための補助線 */
  const totChars = xs.reduce((a, b) => a + b, 0);
  const totRuby = ys.reduce((a, b) => a + b, 0);
  const slope = totRuby / totChars;
  el('line', {
    x1: sx(0), y1: sy(0), x2: sx(x1), y2: sy(slope * x1),
    stroke: 'var(--ink-3)', 'stroke-width': 1, 'stroke-dasharray': '4 4',
  }, svg);

  const gp = el('g', {}, svg);
  for (const s of stories) {
    const c = el('circle', {
      cx: sx(s.chars), cy: sy(s.ruby), r: 5,
      class: 'dot', fill: 'var(--edo)', stroke: 'var(--bg)', 'stroke-width': 1.2,
      opacity: 0.85, tabindex: '0',
    }, gp);
    c.dataset.label = `${s.no} ${s.title}`;
    c.dataset.detail = `${fmt(s.chars)} 字 / ルビ ${fmt(s.ruby)} 件 / ${s.density} 件・千字`;
  }
  return { slope };
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
  root.addEventListener('mouseover', (e) => { const t = e.target.closest('.dot'); if (t) show(t, e.clientX, e.clientY); });
  root.addEventListener('mousemove', (e) => { const t = e.target.closest('.dot'); if (t && !tip.hidden) show(t, e.clientX, e.clientY); });
  root.addEventListener('mouseout', (e) => { if (e.target.closest('.dot')) tip.hidden = true; });
  root.addEventListener('focusin', (e) => {
    const t = e.target.closest('.dot');
    if (!t) return;
    const r = t.getBoundingClientRect();
    show(t, r.left + r.width / 2, r.top);
  });
  root.addEventListener('focusout', () => { tip.hidden = true; });
}

function fill(sel, rows) {
  const tb = document.querySelector(sel);
  tb.textContent = '';
  for (const cells of rows) {
    const tr = document.createElement('tr');
    cells.forEach((v, i) => {
      const td = document.createElement('td');
      td.textContent = v;
      if (typeof v === 'string' && /^[\d,]+$/.test(v) && i > 0) td.className = 'num';
      tr.appendChild(td);
    });
    tb.appendChild(tr);
  }
}

async function main() {
  const R = await (await fetch('data/ruby.json')).json();
  const f = R.first_occurrence, p = R.per_story_rate;

  const tiles = [
    [fmt(R.total), '件', 'ルビの総数'],
    [fmt(R.unique_words), '', '語と読みの組(異なり)'],
    [pct(f.rate), '', 'ルビが付くとき、その話での初出である割合'],
    [pct(p.early_rate), '', '同じ語が、現れる話のうち振られる割合'],
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

  document.getElementById('finding').textContent =
    `ルビが付くとき、それはほぼ必ずその話での初出である —— 掃除した ${fmt(R.clean_bases)} 語で `
    + `${fmt(f.ruby_on_first)}/${fmt(f.ruby_on_first + f.ruby_elsewhere)} = ${pct(f.rate)}。`
    + `ところが同じ語は、現れる話のうち ${pct(p.early_rate)} でしか振られない。`
    + `つまり「難しいから振る」のではなく、話ごとに振るか振らないかが分かれている。`;
  document.getElementById('finding2').textContent =
    `なぜ分かれるのかは、本文だけからは説明できなかった。底本の早い巻(一〜三)と遅い巻(四〜六)の`
    + `両方に現れる ${fmt(p.words)} 語で比べても、振られる割合は ${pct(p.early_rate)} と ${pct(p.late_rate)} でほとんど変わらず、`
    + `話の長さとの相関も弱い(r = ${R.correlations.chars_vs_density})。校訂が巻の途中で緩んだ、とは言えない。`;

  const s = scatter(document.getElementById('scatter'), R.stories);
  const C = R.correlations;
  document.getElementById('scatter-caption').textContent =
    `${R.stories.length} 話。破線は全体の比(千字あたり ${(s.slope * 1000).toFixed(1)} 件)。`
    + `字数とルビ数の相関は r = ${C.chars_vs_ruby} だが、これは長い話の梃子にかなり支えられている ——`
    + ` 最長の ${C.longest.no}「${C.longest.title}」(${fmt(C.longest.chars)} 字)を外すと ${C.chars_vs_ruby_without_longest}、`
    + `長い上位 5 話を外すと ${C.chars_vs_ruby_without_top5} まで下がる。`;
  wireTips(document.body);

  fill('#vtbl tbody', R.volumes.map((v) => [
    `第${v.vol}巻`, String(v.stories), fmt(v.chars), fmt(v.ruby), v.density.toFixed(1)]));
  const ds = R.volumes.map((v) => v.density);
  document.getElementById('vol-note').textContent =
    `底本は 6 巻に分かれている。千字あたりの密度は ${Math.min(...ds).toFixed(1)} から ${Math.max(...ds).toFixed(1)} まで幅があるが、`
    + `上に書いたとおり、この差を校訂の方針の違いとして説明することはできなかった。`;

  fill('#mtbl tbody', R.multi_yomi.map((m) => [
    m.base, Object.entries(m.yomi).map(([y, n]) => `${y}(${n})`).join(' / ')]));
  document.getElementById('multi-note').textContent =
    `${fmt(R.multi_yomi_count)} 語に二通り以上の読みが付いている。多い順に ${R.multi_yomi.length} 件。`
    + `同じ字でも読みが違えば別の語なので、上の数え方ではこれらを外してある。`;

  const words = R.words;
  const q = document.getElementById('q');
  const renderWords = () => {
    const v = q.value.trim();
    const rows = (v ? words.filter((w) => w.base.includes(v) || w.yomi.includes(v)) : words).slice(0, 400);
    fill('#wtbl tbody', rows.map((w) => [w.base, w.yomi, fmt(w.count), String(w.stories)]));
    document.getElementById('wcount').textContent =
      v ? `${fmt(rows.length)} 件(先頭 400 件まで)` : `全 ${fmt(words.length)} 件のうち先頭 400 件`;
  };
  q.addEventListener('input', renderWords);
  renderWords();

  fill('#etbl tbody', f.exceptions.map((e) => [e.story, e.base, e.excerpt]));
  document.getElementById('exc-note').textContent =
    `初出にルビが無く、あとの出現に付いていた例が ${fmt(f.ruby_elsewhere)} 件あった。先頭 ${f.exceptions.length} 件を挙げる。`;
}

main();
