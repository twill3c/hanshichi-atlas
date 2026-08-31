/* 半七アトラス — リーダー(F-11)
 *
 * 本文は data/story/{no}.json のノード列から組む。ルビは <ruby><rt> で出し、
 * 入力者注は本文と区別できる形で残す(落とすと底本の訂正が見えなくなる)。
 */
'use strict';

const qs = new URLSearchParams(location.search);
let INDEX = null;

function yearsLabel(story) {
  const parts = story.cases
    .filter((c) => c.years.length)
    .map((c) => {
      const t = c.years.length > 1 ? c.years.join(c.spans ? '–' : ' / ') : String(c.years[0]);
      return c.uncertain ? t + '?' : t;
    });
  return parts.join('、');
}

/** ノード列を段落に組む。空行が段落の切れ目。 */
function render(nodes, mount) {
  mount.textContent = '';
  let p = document.createElement('p');
  let blank = 0;

  const flush = () => {
    if (p.childNodes.length) mount.appendChild(p);
    p = document.createElement('p');
  };

  for (const n of nodes) {
    if (n.t === 'br') {
      blank += 1;
      if (blank >= 2) flush();
      continue;
    }
    if (n.t === 's') {
      const v = n.v.replace(/\n/g, '');
      if (v) { p.appendChild(document.createTextNode(v)); blank = 0; }
      continue;
    }
    blank = 0;
    if (n.t === 'r') {
      const ruby = document.createElement('ruby');
      ruby.appendChild(document.createTextNode(n.b));
      const rt = document.createElement('rt');
      rt.textContent = n.y;
      ruby.appendChild(rt);
      p.appendChild(ruby);
    } else if (n.t === 'g') {
      p.appendChild(document.createTextNode(n.v));
    } else if (n.t === 'n') {
      const s = document.createElement('span');
      s.className = 'note';
      s.textContent = n.v;
      p.appendChild(s);
    }
  }
  flush();
  if (!mount.childNodes.length) mount.textContent = '(本文がありません)';
}

async function load(no) {
  const story = INDEX.stories.find((s) => s.no === no) || INDEX.stories[0];
  no = story.no;
  history.replaceState(null, '', 'reader.html?w=' + no);

  document.title = `${story.no} ${story.title} — 半七アトラス`;
  document.getElementById('title').textContent = story.title;
  document.getElementById('sub').textContent = `半七捕物帳 ${story.no} — 岡本綺堂`;

  const y = yearsLabel(story);
  document.getElementById('meta').textContent =
    `${story.kind}${y ? ' / 事件年 ' + y : ''} / ${story.chars.toLocaleString('ja-JP')} 字 / ルビ ${story.ruby.toLocaleString('ja-JP')}`;

  const ev = document.getElementById('evidence');
  const src = story.cases.find((c) => c.years.length)?.evidence || story.reason;
  if (src) { ev.textContent = src; ev.hidden = false; } else { ev.hidden = true; }

  document.getElementById('pick').value = no;

  const i = INDEX.stories.findIndex((s) => s.no === no);
  const prev = INDEX.stories[i - 1];
  const next = INDEX.stories[i + 1];
  const pn = document.getElementById('prevnext');
  pn.textContent = '';
  if (prev) {
    const a = document.createElement('a');
    a.href = 'reader.html?w=' + prev.no;
    a.textContent = `← ${prev.no} ${prev.title}`;
    pn.appendChild(a);
  }
  if (prev && next) pn.appendChild(document.createTextNode('　'));
  if (next) {
    const a = document.createElement('a');
    a.href = 'reader.html?w=' + next.no;
    a.textContent = `${next.no} ${next.title} →`;
    pn.appendChild(a);
  }

  const mount = document.getElementById('body');
  mount.textContent = '読み込み中…';
  const data = await (await fetch(`data/story/${no}.json`)).json();
  render(data.nodes, mount);
}

async function main() {
  INDEX = await (await fetch('data/index.json')).json();
  const pick = document.getElementById('pick');
  for (const s of INDEX.stories) {
    const o = document.createElement('option');
    o.value = s.no;
    o.textContent = `${s.no} ${s.title}`;
    pick.appendChild(o);
  }
  pick.addEventListener('change', () => load(pick.value));

  const tgl = document.getElementById('rubytoggle');
  tgl.addEventListener('click', () => {
    const on = tgl.getAttribute('aria-pressed') === 'true';
    tgl.setAttribute('aria-pressed', String(!on));
    document.getElementById('body').classList.toggle('no-ruby', on);
  });

  await load(qs.get('w') || '01');
}

main();
