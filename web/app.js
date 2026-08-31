/* 半七アトラス — 年表ビュー(F-08)
 *
 * 図は SVG を素で組む。ラベル・凡例・軸は、図を描いたのと同じデータから導く
 * (座標を決め打ちしない — HC-045)。
 */
'use strict';

const SVG_NS = 'http://www.w3.org/2000/svg';
const KIND_EDO = '半七の事件';
const KIND_OLD = '半七以前の聞き伝え';
const KIND_NONE = '確定できない';

const el = (name, attrs = {}, parent = null) => {
  const n = document.createElementNS(SVG_NS, name);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  if (parent) parent.appendChild(n);
  return n;
};

const fmt = (n) => n.toLocaleString('ja-JP');

/* 事件年の列(一話に事件が二つあることがある) */
function caseEntries(story) {
  const out = [];
  story.cases.forEach((c, i) => {
    if (!c.years.length) return;
    out.push({ story, idx: i, years: c.years, year: c.years[0], c });
  });
  return out;
}

function yearsLabel(story) {
  const parts = story.cases
    .filter((c) => c.years.length)
    .map((c) => {
      const t = c.years.length > 1 ? c.years.join(c.spans ? '–' : ' / ') : String(c.years[0]);
      return c.uncertain ? t + '?' : t;
    });
  return parts.length ? parts.join('、') : '';
}

/* ------------------------------------------------------------------ 図 */

function drawTimeline(svg, opts) {
  const { lanes, x0, x1, width, ticks, caption } = opts;
  svg.textContent = '';
  const title = el('title', {}, svg);
  title.textContent = opts.title;

  const M = { l: 14, r: 14, t: 10, b: 26 };
  const R = 4.5;
  const STEP = R * 2 + 2;
  const LABEL_H = 18;
  const PAD = 8;

  /* レーンの高さは**データから導く**。定数で決め打ちすると、
   * 同じ年に事件が集まったときに点がレーンからはみ出す(実測で 7 段になる年がある)。 */
  for (const lane of lanes) {
    const per = new Map();
    for (const d of lane.points) per.set(d.year, (per.get(d.year) || 0) + 1);
    lane.maxStack = Math.max(1, ...per.values());
    lane.h = LABEL_H + lane.maxStack * STEP + PAD;
  }
  const lifeH = opts.life ? 34 : 0;
  const lanesH = lanes.reduce((a, l) => a + l.h, 0);
  const H = M.t + lanesH + lifeH + M.b;
  svg.setAttribute('viewBox', `0 0 ${width} ${H}`);
  svg.setAttribute('height', H);

  const sx = (y) => M.l + ((y - x0) / (x1 - x0)) * (width - M.l - M.r);

  /* 軸(下) */
  const axis = el('g', { class: 'axis' }, svg);
  const baseY = M.t + lanesH + lifeH + 6;
  el('line', { x1: M.l, x2: width - M.r, y1: baseY, y2: baseY }, axis);
  for (const t of ticks) {
    const x = sx(t);
    el('line', { x1: x, x2: x, y1: baseY, y2: baseY + 4 }, axis);
    const tx = el('text', { x, y: baseY + 17, 'text-anchor': 'middle' }, axis);
    tx.textContent = String(t);
  }

  /* 半七の生涯 — レーンの下、軸の上に自分の帯を持つ。
   * 点の上に重ねると、明治の点と生涯の印が衝突する(実測)。 */
  if (opts.life) {
    const g = el('g', {}, svg);
    const y = M.t + lanesH + 12;
    el('line', {
      x1: sx(opts.life.from), x2: sx(opts.life.to), y1: y, y2: y,
      stroke: 'var(--life)', 'stroke-width': 2,
    }, g);
    for (const m of opts.life.marks) {
      const x = sx(m.year);
      el('line', { x1: x, x2: x, y1: y - 5, y2: y + 5, stroke: 'var(--life)', 'stroke-width': 2 }, g);
      const t = el('text', { x, y: y + 19, 'text-anchor': 'middle', class: 'axis' }, g);
      t.setAttribute('fill', 'var(--ink-3)');
      t.setAttribute('font-size', '11');
      t.textContent = m.label;
    }
  }

  /* 縦の目印(生年など)。図の外の注記に頼らず、図の中で言う。 */
  for (const gd of opts.guides || []) {
    const g = el('g', {}, svg);
    const x = sx(gd.year);
    el('line', {
      x1: x, x2: x, y1: M.t + 4, y2: M.t + lanesH + 4,
      stroke: 'var(--life)', 'stroke-width': 1, 'stroke-dasharray': '3 3',
    }, g);
    const t = el('text', { x: x + 5, y: M.t + 12, class: 'lane-label' }, g);
    t.setAttribute('fill', 'var(--ink-3)');
    t.setAttribute('font-size', '11');
    t.textContent = gd.label;
  }

  /* 各レーン */
  let top = M.t;
  lanes.forEach((lane) => {
    const g = el('g', {}, svg);
    const lab = el('text', { x: M.l, y: top + 12, class: 'lane-label' }, g);
    lab.textContent = lane.label;
    /* レーンの見出し線 —— 見出しと、遠く離れた点とを目でつなぐ */
    el('line', {
      x1: M.l, x2: width - M.r,
      y1: top + lane.h - PAD + 2, y2: top + lane.h - PAD + 2,
      stroke: 'var(--border)', 'stroke-width': 1,
    }, g);

    /* 同じ年の点は縦に積む(重ねない) */
    const byYear = new Map();
    for (const d of lane.points) {
      const k = d.year;
      if (!byYear.has(k)) byYear.set(k, []);
      byYear.get(k).push(d);
    }
    const r = R;
    const floor = top + lane.h - PAD - r;
    for (const [year, list] of byYear) {
      list.forEach((d, i) => {
        const cx = sx(year);
        const cy = floor - i * STEP;
        const c = el('circle', {
          cx, cy, r,
          class: 'dot',
          fill: lane.hollow ? 'none' : lane.color,
          stroke: lane.hollow ? 'var(--ink-3)' : 'var(--bg)',
          'stroke-width': lane.hollow ? 2 : 1.5,
          tabindex: '0',
          role: 'link',
        }, g);
        c.dataset.no = d.story.no;
        c.dataset.label = d.label;
        c.dataset.detail = d.detail || '';
      });
    }
    top += lane.h;
  });

  if (caption) document.getElementById(opts.captionId).textContent = caption;
}

/* --------------------------------------------------------------- 吹き出し */

function wireTips(root) {
  const tip = document.getElementById('tip');
  const show = (t, x, y) => {
    tip.innerHTML = '';
    const b = document.createElement('b');
    b.textContent = t.dataset.label;
    tip.appendChild(b);
    if (t.dataset.detail) {
      const q = document.createElement('span');
      q.className = 'q';
      q.textContent = t.dataset.detail;
      tip.appendChild(q);
    }
    tip.hidden = false;
    const r = tip.getBoundingClientRect();
    const left = Math.min(Math.max(8, x - r.width / 2), window.innerWidth - r.width - 8);
    const top = y - r.height - 12 < 8 ? y + 18 : y - r.height - 12;
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
  };
  const hide = () => { tip.hidden = true; };

  root.addEventListener('mouseover', (e) => {
    const t = e.target.closest('.dot');
    if (t) show(t, e.clientX, e.clientY);
  });
  root.addEventListener('mousemove', (e) => {
    const t = e.target.closest('.dot');
    if (t && !tip.hidden) show(t, e.clientX, e.clientY);
  });
  root.addEventListener('mouseout', (e) => { if (e.target.closest('.dot')) hide(); });
  root.addEventListener('focusin', (e) => {
    const t = e.target.closest('.dot');
    if (!t) return;
    const r = t.getBoundingClientRect();
    show(t, r.left + r.width / 2, r.top);
  });
  root.addEventListener('focusout', hide);
  const open = (t) => { location.href = 'reader.html?w=' + t.dataset.no; };
  root.addEventListener('click', (e) => {
    const t = e.target.closest('.dot');
    if (t) open(t);
  });
  root.addEventListener('keydown', (e) => {
    const t = e.target.closest('.dot');
    if (t && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); open(t); }
  });
}

/* ------------------------------------------------------------------ 表 */

function renderTable(data, state) {
  const tbody = document.querySelector('#tbl tbody');
  tbody.textContent = '';
  let rows = data.stories.slice();
  if (state.kind) rows = rows.filter((s) => s.kind === state.kind);
  if (state.sort === 'year') {
    rows.sort((a, b) => {
      const ay = caseEntries(a)[0]?.year ?? Infinity;
      const by = caseEntries(b)[0]?.year ?? Infinity;
      return ay - by || a.no.localeCompare(b.no);
    });
  } else {
    rows.sort((a, b) => a.no.localeCompare(b.no));
  }

  for (const s of rows) {
    const tr = document.createElement('tr');
    const add = (txt, cls) => {
      const td = document.createElement('td');
      if (cls) td.className = cls;
      td.textContent = txt;
      tr.appendChild(td);
      return td;
    };
    add(s.no, 'num');
    const t = document.createElement('td');
    const a = document.createElement('a');
    a.href = 'reader.html?w=' + s.no;
    a.textContent = s.title;
    t.appendChild(a);
    tr.appendChild(t);

    const y = yearsLabel(s);
    const yd = add(y || '—', 'yr');
    if (!y) yd.classList.add('muted');

    const kd = document.createElement('td');
    const sp = document.createElement('span');
    sp.className = 'kind';
    const sw = document.createElement('span');
    sw.className = 'swatch';
    if (s.kind === KIND_EDO) sw.style.background = 'var(--edo)';
    else if (s.kind === KIND_OLD) sw.style.background = 'var(--old)';
    else { sw.className = 'swatch hollow'; }
    sp.append(sw, document.createTextNode(s.kind));
    kd.appendChild(sp);
    tr.appendChild(kd);

    add(fmt(s.chars), 'num');
    add(fmt(s.ruby), 'num');
    add(s.cases.find((c) => c.years.length)?.evidence || s.reason || '');
    tbody.appendChild(tr);
  }
  document.getElementById('rowcount').textContent = `${rows.length} 話`;
}

/* ---------------------------------------------------------------- 起動 */

async function main() {
  const data = await (await fetch('data/index.json')).json();
  const stories = data.stories;

  /* タイル */
  const edoYears = stories.filter((s) => s.kind === KIND_EDO).flatMap((s) => caseEntries(s).map((e) => e.year));
  const tiles = [
    ['69', '話', '青空文庫に揃う全編'],
    [String(data.counts[KIND_EDO]), '話', '半七が手がけた事件'],
    [`${Math.min(...edoYears)}–${Math.max(...edoYears)}`, '', 'その事件年の幅'],
    [String(data.counts[KIND_NONE]), '話', '年を確定できない(空欄で出す)'],
    [String(data.hanshichi.birth_year), '年', '半七の生年(本文の三つの言明が収束)'],
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

  /* 凡例 — 図に出るものだけを並べる */
  const legend = document.getElementById('legend');
  const legendItems = [
    ['swatch', 'var(--edo)', '江戸の事件'],
    ['swatch hollow', null, '明治の語り(年を書く 8 話)'],
    ['swatch rule', null, '半七の生涯'],
  ];
  for (const [cls, color, label] of legendItems) {
    const s = document.createElement('span');
    const sw = document.createElement('span');
    sw.className = cls;
    if (color) sw.style.background = color;
    s.append(sw, document.createTextNode(label));
    legend.appendChild(s);
  }

  /* 主図 */
  const edoPoints = stories
    .filter((s) => s.kind === KIND_EDO)
    .flatMap((s) => caseEntries(s).map((e) => ({
      story: s,
      year: e.year,
      label: `${s.no} ${s.title} — ${yearsLabel(s)}`,
      detail: e.c.evidence,
    })));
  const framePoints = stories
    .filter((s) => s.frame_years.length)
    .flatMap((s) => s.frame_years.map((y) => ({
      story: s,
      year: y,
      label: `${s.no} ${s.title} — 語りの年 ${y}`,
      detail: '本文が明治の年を書いている話',
    })));

  const h = data.hanshichi;
  drawTimeline(document.getElementById('main-chart'), {
    title: '半七の生涯の上に置いた、江戸の事件と明治の語りの年表',
    captionId: 'main-caption',
    x0: 1820, x1: 1902, width: 940,
    ticks: [1820, 1830, 1840, 1850, 1860, 1870, 1880, 1890, 1900],
    lanes: [
      { label: '江戸の事件', color: 'var(--edo)', points: edoPoints },
      { label: '明治の語り', hollow: true, points: framePoints },
    ],
    life: {
      from: h.birth_year, to: 1895,
      marks: [
        { year: h.birth_year, label: `生 ${h.birth_year}` },
        { year: h.first_case_year, label: `初陣 ${h.first_case_year}` },
        { year: 1895, label: '73 歳' },
      ],
    },
    caption: `事件 ${edoPoints.length} 件 / 語りの年 ${framePoints.length} 件。点をたどるとその話を読める。`,
  });

  /* 生前の図 */
  const oldPoints = stories
    .filter((s) => s.kind === KIND_OLD)
    .flatMap((s) => caseEntries(s).map((e) => ({
      story: s,
      year: e.year,
      label: `${s.no} ${s.title} — ${e.year}`,
      detail: e.c.evidence,
    })));
  const oy = oldPoints.map((p) => p.year);
  drawTimeline(document.getElementById('old-chart'), {
    title: '半七の生前に置かれた 5 話の年表',
    captionId: 'old-caption',
    x0: 1740, x1: 1830, width: 940,
    ticks: [1740, 1760, 1780, 1800, 1820],
    lanes: [{ label: '半七以前の聞き伝え', color: 'var(--old)', points: oldPoints }],
    guides: [{ year: h.birth_year, label: `半七生 ${h.birth_year}` }],
    caption: `${new Set(oldPoints.map((p) => p.story.no)).size} 話 / ${oldPoints.length} 件。${Math.min(...oy)}–${Math.max(...oy)} 年。`
      + ` 18「槍突き」の二度目の流行だけは生年より後だが、そのとき半七は数え三つで、探索したのは別の者である。`,
  });

  wireTips(document.body);

  /* 表 */
  const state = { sort: 'no', kind: '' };
  const sel = document.getElementById('kindsel');
  for (const k of data.kinds) {
    const o = document.createElement('option');
    o.value = k;
    o.textContent = `${k}(${data.counts[k] || 0})`;
    sel.appendChild(o);
  }
  sel.addEventListener('change', () => { state.kind = sel.value; renderTable(data, state); });
  for (const b of document.querySelectorAll('button.seg')) {
    b.addEventListener('click', () => {
      state.sort = b.dataset.sort;
      for (const o of document.querySelectorAll('button.seg')) {
        o.setAttribute('aria-pressed', String(o === b));
      }
      renderTable(data, state);
    });
  }
  renderTable(data, state);

  /* 相互参照 */
  const rt = document.querySelector('#reftbl tbody');
  for (const r of data.crossrefs.filter((r) => r.agrees !== null)) {
    const tr = document.createElement('tr');
    for (const v of [
      `${r.from} → ${r.to}『${r.title}』`,
      r.evidence,
      String(r.expected),
      r.actual.join(' / '),
      r.agrees ? '一致' : '食い違い',
    ]) {
      const td = document.createElement('td');
      td.textContent = v;
      tr.appendChild(td);
    }
    rt.appendChild(tr);
  }

  /* 同じ出来事 */
  const et = document.querySelector('#evtbl tbody');
  let disagree = 0;
  for (const ev of data.shared_events) {
    if (!ev.month_agrees || !ev.year_agrees) disagree += 1;
    ev.mentions.forEach((m, i) => {
      const tr = document.createElement('tr');
      for (const v of [
        i === 0 ? ev.event : '',
        m.story,
        m.date_text,
        String(m.year),
        m.month === null ? '—' : String(m.month) + ' 月',
      ]) {
        const td = document.createElement('td');
        td.textContent = v;
        tr.appendChild(td);
      }
      et.appendChild(tr);
    });
  }
  document.getElementById('events-note').textContent =
    `別々の話が同じ江戸の出来事に触れる箇所を突き合わせた。${data.shared_events.length} 件のうち ` +
    `${disagree} 件で日付が食い違う。どちらの日付も綺堂が本文に書いたもので、こちらの判定が入る余地は無い。`;
}

main();
