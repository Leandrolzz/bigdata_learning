'use strict';
/* ================= 大数据学习闯关平台 v1.1 - 前端交互 ================= */

const S = {
  app: null,          // app meta
  snap: null,         // 进度快照
  stageCache: {},     // stageId -> 完整阶段内容
  interview: null,    // 面试宝典
  view: 'home',
  stageId: null,
  chapterId: null,
  combo: 0,           // 连击（会话内）
  scrollPos: {},      // 章节/阶段滚动位置记忆（ch_xxx / st_xxx -> scrollY）
};

/* ---------------- 工具 ---------------- */
const $ = (sel, root) => (root || document).querySelector(sel);

function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    method: opts.method || 'GET',
    headers: { 'Content-Type': 'application/json' },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const data = await res.json();
  if (data.error) throw new Error(data.error);
  return data;
}

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

function toast(msg, kind) {
  const w = $('#toast-wrap');
  const t = el('div', 'toast' + (kind ? ' ' + kind : ''), msg);
  w.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transition = 'opacity .4s'; }, 2600);
  setTimeout(() => t.remove(), 3100);
}

function confetti() {
  const w = $('#confetti-wrap');
  const colors = ['#4f8cff', '#2ecc71', '#f5a623', '#ff5c5c', '#a78bfa', '#7ab0ff'];
  for (let i = 0; i < 46; i++) {
    const c = document.createElement('div');
    c.className = 'confetti';
    c.style.left = Math.random() * 100 + 'vw';
    c.style.background = colors[i % colors.length];
    c.style.animationDelay = (Math.random() * 0.35) + 's';
    w.appendChild(c);
    setTimeout(() => c.remove(), 1800);
  }
}

/* ---------------- 语法高亮（轻量，无依赖） ---------------- */
const PY_KW = new Set(('def class return if elif else for while in not and or import from as try except finally ' +
  'raise with lambda yield pass break continue global del assert is nonlocal None True False').split(' '));
const PY_BF = new Set(('print len range int str float list dict set tuple type open sum max min sorted enumerate ' +
  'zip map filter round abs input isinstance repr format input super bool bytes dict keys values items').split(' '));
const SQL_KW = new Set(('SELECT FROM WHERE GROUP HAVING ORDER BY LIMIT JOIN LEFT RIGHT INNER FULL OUTER ON AS DISTINCT ' +
  'UNION ALL AND OR NOT IN EXISTS BETWEEN LIKE IS NULL CASE WHEN THEN ELSE END COUNT SUM AVG MAX MIN OVER PARTITION ' +
  'ROW_NUMBER RANK DENSE_RANK LAG LEAD COALESCE INSERT INTO VALUES CREATE TABLE PRIMARY KEY DESC ASC').split(' '));

function hl(code, lang) {
  /* 单遍词法着色：字符串/注释/数字/关键字一次扫描完成，无占位符，杜绝字符损坏 */
  const isSql = String(lang || '').toLowerCase() === 'sql';
  const src = String(code == null ? '' : code);
  const e = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const tokenRe = /('(?:[^'\\\n]|\\.)*'|"(?:[^"\\\n]|\\.)*"|--[^\n]*|#[^\n]*|\b\d+(?:\.\d+)?\b|\b[A-Za-z_][A-Za-z0-9_]*\b)/y;
  let out = '';
  let i = 0;
  while (i < src.length) {
    tokenRe.lastIndex = 0;
    const m = tokenRe.exec(src.slice(i));
    if (m && m.index === 0) {
      const tok = m[0];
      const c0 = tok[0];
      if (c0 === "'" || c0 === '"') {
        out += '<span class="st">' + e(tok) + '</span>';
      } else if (c0 === '-' || c0 === '#') {
        out += '<span class="cm">' + e(tok) + '</span>';
      } else if (c0 >= '0' && c0 <= '9') {
        out += '<span class="nu">' + e(tok) + '</span>';
      } else if (isSql ? SQL_KW.has(tok.toUpperCase()) : PY_KW.has(tok)) {
        out += '<span class="kw">' + e(tok) + '</span>';
      } else if (!isSql && PY_BF.has(tok)) {
        out += '<span class="bf">' + e(tok) + '</span>';
      } else {
        out += e(tok);
      }
      i += tok.length;
    } else {
      out += e(src[i]);
      i++;
    }
  }
  return out;
}

function codeHtml(code, lang) {
  const l = String(lang || '').toLowerCase();
  if (l === 'sql') return hl(code, 'sql');
  if (l === 'python' || l === 'py') return hl(code, 'python');
  return esc(code);
}

/* ---------------- markdown 渲染 ---------------- */
function md(src) {
  if (!src) return '';
  /* 兼容历史内容：字面 \n（反斜杠+n）在代码围栏外自动转换为真实换行，
     这样 hands_on/analysis 里的 "1. ...\n2. ..." 能正确渲染成列表 */
  const raw = String(src).replace(/\r\n/g, '\n').split('\n');
  const lines = [];
  let inFence = false;
  for (const ln of raw) {
    if (ln.trim().startsWith('```')) { lines.push(ln); inFence = !inFence; continue; }
    lines.push(inFence ? ln : ln.replace(/\\n/g, '\n'));
  }
  const flat = [];
  for (const ln of lines) {
    if (ln.indexOf('\n') >= 0) flat.push.apply(flat, ln.split('\n'));
    else flat.push(ln);
  }
  const inline = (s) => esc(s)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  let html = '';
  let i = 0;
  while (i < flat.length) {
    const ln = flat[i];
    const t = ln.trim();
    if (!t) { i++; continue; }
    if (t.startsWith('```')) {
      const lang = t.slice(3).trim().split(/\s+/)[0];
      const buf = []; i++;
      while (i < flat.length && !flat[i].trim().startsWith('```')) { buf.push(flat[i]); i++; }
      i++;
      html += '<pre class="md-code"><code class="hl">' + codeHtml(buf.join('\n'), lang) + '</code></pre>';
      continue;
    }
    if (/^#{1,4}\s/.test(t)) {
      const m = t.match(/^(#{1,4})\s+(.*)/);
      const lv = Math.min(m[1].length + 2, 5);
      html += '<h' + lv + '>' + inline(m[2]) + '</h' + lv + '>';
      i++; continue;
    }
    if (t.startsWith('|') && i + 1 < flat.length && /^\|[\s\-:|]+\|$/.test(flat[i + 1].trim())) {
      const header = flat[i].split('|').slice(1, -1).map(s => s.trim());
      i += 2;
      const rows = [];
      while (i < flat.length && flat[i].trim().startsWith('|')) {
        rows.push(flat[i].split('|').slice(1, -1).map(s => s.trim()));
        i++;
      }
      html += '<div class="result-table"><table><thead><tr>' +
        header.map(h => '<th>' + inline(h) + '</th>').join('') +
        '</tr></thead><tbody>' +
        rows.map(r => '<tr>' + r.map(c => '<td>' + inline(c) + '</td>').join('') + '</tr>').join('') +
        '</tbody></table></div>';
      continue;
    }
    if (/^-\s/.test(t)) {
      const items = [];
      while (i < flat.length && /^\s*-\s/.test(flat[i])) {
        items.push(inline(flat[i].trim().replace(/^-\s+/, '')));
        i++;
      }
      html += '<ul>' + items.map(x => '<li>' + x + '</li>').join('') + '</ul>';
      continue;
    }
    if (/^\d+\.\s/.test(t)) {
      const items = [];
      while (i < flat.length && /^\s*\d+\.\s/.test(flat[i])) {
        items.push(inline(flat[i].trim().replace(/^\d+\.\s+/, '')));
        i++;
      }
      html += '<ol>' + items.map(x => '<li>' + x + '</li>').join('') + '</ol>';
      continue;
    }
    const buf = [ln]; i++;
    while (i < flat.length && flat[i].trim() !== '' &&
           !/^(#{1,4}\s|```|- |\d+\.\s|\|)/.test(flat[i].trim())) {
      buf.push(flat[i]); i++;
    }
    html += '<p>' + inline(buf.join(' ')) + '</p>';
  }
  return html;
}

/* ---------------- 快照工具 ---------------- */
function solvedOf(taskId) {
  const st = S.snap.tasks_state[taskId];
  return st ? !!st.solved : false;
}
function attemptsOf(taskId) {
  const st = S.snap.tasks_state[taskId];
  return st ? st.attempts : 0;
}
function applySnap(snap) { S.snap = snap; refreshShell(); }

function refreshShell() {
  renderSidebar();
  renderTopbar();
}

/* ---------------- 渲染：外壳 ---------------- */
function renderSidebar() {
  const nav = $('#stage-nav');
  nav.innerHTML = '';

  /* 面试宝典入口 */
  const iv = el('div', 'nav-item' + (S.view === 'interview' ? ' active' : ''));
  iv.innerHTML = '<span class="emo">🎤</span><span class="nm">面试宝典</span>';
  iv.addEventListener('click', goInterview);
  nav.appendChild(iv);

  S.snap.stages.forEach(st => {
    const active = (S.view === 'stage' && S.stageId === st.stage_id) ||
                   (S.view === 'chapter' && S.stageId === st.stage_id);
    const box = el('div', 'nav-stage' + (active ? ' open' : ''));
    const item = el('div', 'nav-item' + (active ? ' active' : ''));
    const pct = st.task_count ? Math.round(st.solved / st.task_count * 100) : 0;
    item.dataset.full = st.title;
    item.innerHTML =
      '<span class="emo">' + esc(st.emoji) + '</span>' +
      '<span class="nm">' + esc(st.title) + '</span>' +
      '<span class="pct">' + pct + '%</span>' +
      '<span class="chev">▾</span>';
    item.addEventListener('click', e => {
      if (e.target.classList.contains('chev')) { box.classList.toggle('open'); return; }
      goStage(st.stage_id);
    });
    box.appendChild(item);

    /* 章节列表（圆点标记进度） */
    const chList = el('div', 'ch-list');
    st.chapters.forEach(ch => {
      const done = ch.task_count > 0 && ch.solved === ch.task_count;
      const c = el('div', 'ch-item' + (S.view === 'chapter' && S.chapterId === ch.chapter_id ? ' active' : ''));
      c.dataset.full = ch.title;
      c.innerHTML =
        '<span class="dot' + (done ? ' done' : '') + '">' + (done ? '●' : '○') + '</span>' +
        '<span class="ch-name">' + esc(ch.title) + '</span>';
      c.addEventListener('click', () => goChapter(st.stage_id, ch.chapter_id));
      chList.appendChild(c);
    });
    box.appendChild(chList);
    nav.appendChild(box);
  });

  const su = $('#side-user');
  const lv = S.snap.level;
  su.innerHTML =
    '<span class="chip">Lv.<b>' + lv.level + '</b></span>' +
    '<span class="chip">⭐ <b>' + S.snap.xp + '</b> XP</span>' +
    '<span class="chip">📅 连续 <b>' + S.snap.streak + '</b> 天</span>';
}

function renderTopbar() {
  const bc = $('#breadcrumb');
  if (S.view === 'home') bc.innerHTML = '🏠 首页';
  else if (S.view === 'interview') bc.innerHTML = '<span class="bc-link" onclick="goHome()">🏠 首页</span> / 🎤 面试宝典';
  else if (S.view === 'stage') {
    const st = S.snap.stages.find(s => s.stage_id === S.stageId);
    bc.innerHTML = '<span class="bc-link" onclick="goHome()">🏠 首页</span> / ' + esc(st ? st.title : '');
  } else if (S.view === 'chapter') {
    const st = S.snap.stages.find(s => s.stage_id === S.stageId);
    let chTitle = '';
    const ch = st && st.chapters.find(c => c.chapter_id === S.chapterId);
    if (ch) chTitle = ch.title;
    bc.innerHTML = '<span class="bc-link" onclick="goHome()">🏠 首页</span> / ' +
      '<span class="bc-link" onclick="goStage(\'' + esc(S.stageId) + '\')">' + esc(st ? st.title : '') + '</span> / ' +
      esc(chTitle);
  }
  const ts = $('#top-stats');
  const lv = S.snap.level;
  const combo = S.combo >= 2 ? '<span class="stat-chip hot">🔥 连击 x' + S.combo + '</span>' : '';
  const checkinBtn = '<button id="btn-checkin" ' + (S.snap.plan.checkin_done ? 'disabled' : '') + '>' +
    (S.snap.plan.checkin_done ? '✅ 今日已打卡' : '📌 今日打卡 +10XP') + '</button>';
  ts.innerHTML =
    '<span class="stat-chip">Lv.' + lv.level + ' <b>' + S.snap.xp + '</b>/' + lv.nxt + ' XP</span>' +
    '<span class="stat-chip">📅 第 <b>' + S.snap.plan.day_index + '</b>/' + S.snap.plan.total_days + ' 天</span>' +
    combo + checkinBtn;
  const btn = $('#btn-checkin');
  if (btn) btn.addEventListener('click', doCheckin);
}

/* ---------------- 路由 ---------------- */
/* 滚动位置记忆：离开章节/阶段时保存，进入时恢复（首次进入回顶部） */
function saveScroll() {
  try {
    if (S.view === 'chapter' && S.chapterId) S.scrollPos['ch_' + S.chapterId] = window.scrollY || 0;
    else if (S.view === 'stage' && S.stageId) S.scrollPos['st_' + S.stageId] = window.scrollY || 0;
  } catch (e) { /* ignore */ }
}
function restoreScroll(key) {
  const y = S.scrollPos[key] || 0;
  requestAnimationFrame(() => window.scrollTo(0, y));
}

function goHome() {
  saveScroll();
  S.view = 'home'; S.stageId = null; S.chapterId = null;
  renderShell();
  renderHome();
  window.scrollTo(0, 0);
}
function goStage(id) {
  saveScroll();
  S.view = 'stage'; S.stageId = id; S.chapterId = null;
  renderShell();
  renderStage();
}
function goChapter(stageId, chapterId) {
  saveScroll();
  S.view = 'chapter'; S.stageId = stageId; S.chapterId = chapterId;
  renderShell();
  renderChapter();
}
function goInterview() {
  saveScroll();
  S.view = 'interview';
  renderShell();
  renderInterview();
  window.scrollTo(0, 0);
}
window.goHome = goHome;
window.goStage = goStage;
window.goChapter = goChapter;

function renderShell() {
  renderSidebar();
  renderTopbar();
  $('#view').innerHTML = '<div class="muted" style="text-align:center;padding:60px">加载中…</div>';
}

/* ---------------- 首页 ---------------- */
function renderHome() {
  const v = $('#view');
  const snap = S.snap;
  const lv = snap.level;
  const hero = el('div', 'hero');
  hero.innerHTML =
    '<h1>🚀 ' + esc(S.app.name) + '</h1>' +
    '<div class="muted">' + esc(S.app.description) + '</div>' +
    '<div class="row gap"><span class="day-badge">📅 学习第 ' + snap.plan.day_index + ' / ' + snap.plan.total_days + ' 天</span>' +
    '<span class="day-badge" style="background:#2ecc71">Lv.' + lv.level + '</span>' +
    '<button class="btn" style="margin-left:auto" onclick="goInterview()">🎤 面试宝典</button></div>' +
    '<div class="xp-line"><span style="font-size:13px;color:var(--text2)">经验</span>' +
    '<div class="bar grow"><i style="width:' + Math.round(lv.ratio * 100) + '%"></i></div>' +
    '<span class="muted">' + snap.xp + ' / ' + lv.nxt + '</span></div>';

  /* 今日计划 */
  const planCard = el('div', 'card');
  const today = snap.plan.today || [];
  let planHtml = '<h3>📖 今日学习计划（' + S.app.daily_minutes + ' 分钟 ≈ 2 小时）</h3>';
  if (!today.length) {
    planHtml += '<p class="muted">所有课程已完成，恭喜毕业！🎓</p>';
  }
  today.forEach(e => {
    planHtml += '<div class="plan-card gap">' +
      '<div class="p-day">D' + e.day + '</div>' +
      '<div class="grow"><div><b>' + esc(e.chapter_title) + '</b></div>' +
      '<div class="muted">' + esc(e.stage_title) + '</div>' +
      '<div class="plan-parts">' + e.parts.map(p =>
        '<span class="part-chip">' + esc(p.label) + ' <b>' + p.min + ' 分钟</b></span>').join('') +
      '</div>' +
      '<div class="gap"><button class="btn btn-primary btn-sm" onclick="goChapter(\'' + esc(e.stage_id) + '\',\'' + esc(e.chapter_id) + '\')">去学习 →</button></div>' +
      '</div></div>';
  });
  planCard.innerHTML = planHtml;

  /* 学习路径 */
  const pathCard = el('div', 'card');
  let pathHtml = '<h3>🗺️ 学习路径（共 ' + snap.total_tasks + ' 个闯关任务 · 全部章节自由访问，绿色圆点=通关）</h3>';
  snap.stages.forEach(st => {
    const pct = st.task_count ? Math.round(st.solved / st.task_count * 100) : 0;
    pathHtml += '<div class="path-card gap" data-sid="' + esc(st.stage_id) + '">' +
      '<span class="emo">' + esc(st.emoji) + '</span>' +
      '<div class="grow"><div class="st">' + esc(st.title) + '</div>' +
      '<div class="muted">' + esc(st.subtitle) + ' · ' + st.estimated_days + ' 天 · ' + st.solved + '/' + st.task_count + ' 任务</div>' +
      '<div class="bar gap"><i class="' + (pct === 100 ? 'ok' : '') + '" style="width:' + pct + '%"></i></div></div>' +
      '<span class="pct">' + pct + '%</span></div>';
  });
  pathCard.innerHTML = pathHtml;
  pathCard.querySelectorAll('.path-card').forEach(c => {
    c.addEventListener('click', () => goStage(c.dataset.sid));
  });

  /* 统计 */
  const statCard = el('div', 'card');
  const types = { choice: '选择题', multi: '多选题', fill: '填空题', order: '排序题', sql: 'SQL 题', python: '编程题' };
  let typeHtml = Object.entries(types).map(([k, label]) => {
    const total = S.snap.total_by_type ? (S.snap.total_by_type[k] || 0) : '?';
    return '<div class="stat-cell"><div class="v">' + (snap.solved_by_type[k] || 0) + (total !== '?' ? '/' + total : '') + '</div><div class="k">' + label + '</div></div>';
  }).join('');
  statCard.innerHTML =
    '<h3>📊 学习统计</h3><div class="stat-grid">' +
    '<div class="stat-cell"><div class="v">' + snap.solved_total + '/' + snap.total_tasks + '</div><div class="k">已完成任务</div></div>' +
    '<div class="stat-cell"><div class="v">' + snap.hands_count + '</div><div class="k">动手实践</div></div>' +
    '<div class="stat-cell"><div class="v">' + snap.streak + ' 天</div><div class="k">连续学习</div></div>' +
    '<div class="stat-cell"><div class="v">' + snap.badges.filter(b => b.earned).length + '</div><div class="k">已获徽章</div></div>' +
    typeHtml + '</div>' +
    '<div class="gap"><button class="btn btn-danger btn-sm" id="btn-reset">⚠ 重置全部进度（谨慎）</button></div>';

  /* 徽章墙 */
  const badgeCard = el('div', 'card');
  badgeCard.innerHTML = '<h3>🏅 徽章墙</h3><div class="badge-grid">' +
    snap.badges.map(b =>
      '<div class="badge-item' + (b.earned ? '' : ' off') + '">' +
      '<span class="bi">' + esc(b.icon) + '</span>' +
      '<div><div class="bn">' + esc(b.name) + '</div><div class="bd">' + esc(b.desc) + '</div></div></div>'
    ).join('') + '</div>';

  v.innerHTML = '';
  v.appendChild(hero);
  v.appendChild(planCard);
  v.appendChild(pathCard);
  v.appendChild(statCard);
  v.appendChild(badgeCard);

  $('#btn-reset').addEventListener('click', async () => {
    if (!confirm('确定要重置全部学习进度吗？此操作不可恢复！')) return;
    if (!confirm('再次确认：所有任务、XP、徽章都将被清空。')) return;
    await api('/api/reset', { method: 'POST', body: { confirm: 'RESET' } });
    location.reload();
  });
}

/* ---------------- 阶段页 ---------------- */
async function renderStage() {
  const v = $('#view');
  const stSum = S.snap.stages.find(s => s.stage_id === S.stageId);
  if (!stSum) { v.innerHTML = '<div class="card">阶段不存在</div>'; return; }
  let stage;
  if (S.stageCache[S.stageId]) stage = S.stageCache[S.stageId];
  else {
    v.innerHTML = '<div class="muted" style="text-align:center;padding:60px">加载中…</div>';
    stage = await api('/api/stage/' + S.stageId);
    S.stageCache[S.stageId] = stage;
  }
  const pct = stSum.task_count ? Math.round(stSum.solved / stSum.task_count * 100) : 0;
  const head = el('div', 'card');
  head.innerHTML =
    '<h2 class="view-title">' + esc(stSum.emoji) + ' ' + esc(stSum.title) + '</h2>' +
    '<div class="sub">' + esc(stSum.subtitle) + '</div>' +
    '<div class="md">' + md(stage.learning_goal || '') + '</div>' +
    '<div class="gap bar"><i class="' + (pct === 100 ? 'ok' : '') + '" style="width:' + pct + '%"></i></div>' +
    '<div class="muted gap">已完成 ' + stSum.solved + '/' + stSum.task_count + ' 个任务 · ' + pct + '%</div>';

  const list = el('div', '');
  stSum.chapters.forEach(ch => {
    const done = ch.task_count > 0 && ch.solved === ch.task_count;
    const cpct = ch.task_count ? Math.round(ch.solved / ch.task_count * 100) : 0;
    const item = el('div', 'chapter-item');
    item.innerHTML =
      '<span class="ci dot' + (done ? ' done' : '') + '">' + (done ? '●' : '○') + '</span>' +
      '<div class="grow"><div class="cn">' + esc(ch.title) + '</div>' +
      '<div class="cmeta">' + ch.solved + '/' + ch.task_count + ' 任务' +
      (ch.has_hands_on ? ' · 动手实践 ' + (ch.hands_done ? '✅' : '⬜') : '') + '</div></div>' +
      '<div class="bar" style="width:110px;flex:none"><i class="' + (cpct === 100 ? 'ok' : '') + '" style="width:' + cpct + '%"></i></div>';
    item.addEventListener('click', () => goChapter(S.stageId, ch.chapter_id));
    list.appendChild(item);
  });

  const navRow = el('div', 'row gap');
  const idx = S.snap.stages.findIndex(s => s.stage_id === S.stageId);
  if (idx > 0) {
    const prev = S.snap.stages[idx - 1];
    const b = el('button', 'btn', '← 上一阶段');
    b.addEventListener('click', () => goStage(prev.stage_id));
    navRow.appendChild(b);
  }
  const next = S.snap.stages[idx + 1];
  if (next) {
    const b = el('button', 'btn btn-primary', '下一阶段：' + esc(next.title) + ' →');
    b.addEventListener('click', () => goStage(next.stage_id));
    navRow.appendChild(b);
  }
  if (navRow.children.length) list.appendChild(navRow);

  v.innerHTML = '';
  v.appendChild(head);
  v.appendChild(list);
  restoreScroll('st_' + S.stageId);
}

/* ---------------- 章节页 ---------------- */
async function renderChapter() {
  const v = $('#view');
  const stSum = S.snap.stages.find(s => s.stage_id === S.stageId);
  let stage;
  if (S.stageCache[S.stageId]) stage = S.stageCache[S.stageId];
  else {
    v.innerHTML = '<div class="muted" style="text-align:center;padding:60px">加载中…</div>';
    stage = await api('/api/stage/' + S.stageId);
    S.stageCache[S.stageId] = stage;
  }
  const ch = stage.chapters.find(c => c.chapter_id === S.chapterId);
  if (!ch) { v.innerHTML = '<div class="card">章节不存在</div>'; return; }
  const chSum = stSum && stSum.chapters.find(c => c.chapter_id === S.chapterId);

  const head = el('div', 'ch-head');
  head.innerHTML = '<h2>' + esc(ch.title) + '</h2>' +
    '<div class="ch-goal">🎯 本章目标：' + esc(ch.goal || '') + '</div>';

  /* 知识点清单 */
  const kpCard = el('div', 'card kp-card');
  kpCard.innerHTML = '<h3>📋 本章知识点（' + (ch.kps ? ch.kps.length : 0) + ' 个，逐一掌握、不跳过）</h3>' +
    '<div class="kp-list">' + (ch.kps || []).map(k => '<span class="kp-item">' + esc(k) + '</span>').join('') +
    (ch.kps ? '' : '<span class="muted">内容扩充中…</span>') + '</div>';

  const theory = el('div', '');
  ch.theory.forEach(b => {
    if (b.type === 'text') {
      const d = el('div', 'theory-block tb-text md');
      d.innerHTML = md(b.content);
      theory.appendChild(d);
    } else if (b.type === 'code') {
      const d = el('div', 'theory-block code-block');
      d.innerHTML = '<div class="code-head"><span>' + esc(b.caption || (b.lang || 'code')) + '</span>' +
        '<button class="copy-btn" data-code="' + esc(b.content) + '">📋 复制</button></div>' +
        '<pre><code class="hl">' + codeHtml(b.content, b.lang) + '</code></pre>';
      theory.appendChild(d);
    } else if (b.type === 'tip' || b.type === 'warning' || b.type === 'enterprise') {
      const tags = { tip: '💡 小提示', warning: '⚠️ 注意', enterprise: '🏢 企业视角' };
      const d = el('div', 'tb-' + b.type + ' md');
      d.innerHTML = '<span class="tb-tag">' + tags[b.type] + '</span>' + md(b.content);
      theory.appendChild(d);
    }
  });
  theory.querySelectorAll('.copy-btn').forEach(b => {
    b.addEventListener('click', () => {
      navigator.clipboard.writeText(b.dataset.code).then(() => toast('已复制到剪贴板', 'good'));
    });
  });

  /* 动手实践 */
  const hands = el('div', 'card hands-card' + (chSum && chSum.hands_done ? ' done' : ''));
  hands.innerHTML = '<h3>🛠️ 动手实践</h3><div class="md">' + md(ch.hands_on || '') + '</div>';
  const hbtn = el('button', 'btn btn-success gap', chSum && chSum.hands_done ? '✅ 已完成' : '完成实践 +40XP');
  hbtn.disabled = !!(chSum && chSum.hands_done);
  hbtn.addEventListener('click', async () => {
    try {
      const res = await api('/api/hands_on', { method: 'POST', body: { chapter_id: S.chapterId } });
      applySnap(res.snapshot);
      hbtn.textContent = '✅ 已完成';
      hbtn.disabled = true;
      hands.classList.add('done');
      if (res.xp > 0) { toast('🛠️ 动手实践完成 +' + res.xp + ' XP', 'good'); }
      res.new_badges.forEach(b => toast('🏅 获得徽章：' + b.icon + ' ' + b.name, 'gold'));
      updateChapterFooter();
    } catch (e) { toast('操作失败：' + e.message, ''); }
  });
  hands.appendChild(hbtn);

  /* 任务 */
  const tasksBox = el('div', '');
  const tasks = ch.tasks || [];
  const solvedNow = tasks.filter(t => solvedOf(t.task_id)).length;
  tasksBox.appendChild(el('h3', 'sub gap', '🎮 闯关任务（' + tasks.length + ' 个 · 已完成 ' + solvedNow + '）'));
  tasks.forEach((task, i) => {
    tasksBox.appendChild(renderTask(task, i + 1, tasks.length));
  });

  /* 速记卡 */
  const cheat = renderCheatSheet(ch);

  /* 底部导航（动态刷新） */
  const foot = el('div', '', null);
  foot.id = 'ch-foot';

  v.innerHTML = '';
  v.appendChild(head);
  v.appendChild(kpCard);
  v.appendChild(theory);
  v.appendChild(hands);
  v.appendChild(tasksBox);
  if (cheat) v.appendChild(cheat);
  v.appendChild(foot);
  updateChapterFooter();
  restoreScroll('ch_' + S.chapterId);
}

/* 章节底部导航：通关后显示下一章按钮 */
function updateChapterFooter() {
  const foot = $('#ch-foot');
  if (!foot) return;
  const stSum = S.snap.stages.find(s => s.stage_id === S.stageId);
  const stage = S.stageCache[S.stageId];
  if (!stSum || !stage) return;
  const ch = stage.chapters.find(c => c.chapter_id === S.chapterId);
  if (!ch) return;
  const tasks = ch.tasks || [];
  const solvedNow = tasks.filter(t => solvedOf(t.task_id)).length;
  const allDone = tasks.length > 0 && solvedNow === tasks.length;
  const chapters = stSum.chapters;
  const ci = chapters.findIndex(c => c.chapter_id === S.chapterId);

  foot.innerHTML = '';
  if (allDone) {
    const banner = el('div', 'ch-done-banner');
    banner.innerHTML = '<div class="big">🎉 本章全部任务通关！</div>' +
      '<div class="muted" style="margin-top:6px">' + solvedNow + '/' + tasks.length + ' 题已通过' +
      (ch.qa ? ' · 下方速记卡可巩固复习' : '') + '</div>';
    foot.appendChild(banner);
  }
  const row = el('div', 'row gap');
  if (ci > 0) {
    const b = el('button', 'btn', '← ' + esc(chapters[ci - 1].title));
    b.addEventListener('click', () => goChapter(S.stageId, chapters[ci - 1].chapter_id));
    row.appendChild(b);
  }
  if (allDone && ci < chapters.length - 1) {
    const b = el('button', 'btn btn-success', '🎉 通关！下一章：' + esc(chapters[ci + 1].title) + ' →');
    b.addEventListener('click', () => goChapter(S.stageId, chapters[ci + 1].chapter_id));
    row.appendChild(b);
  } else if (allDone) {
    const b = el('button', 'btn btn-primary', '🏆 阶段任务完成，返回阶段页');
    b.addEventListener('click', () => goStage(S.stageId));
    row.appendChild(b);
  }
  if (!allDone) {
    row.appendChild(el('span', 'try-note', '已完成 ' + solvedNow + '/' + tasks.length + ' 个任务，全部通过后出现「下一章」按钮'));
  }
  foot.appendChild(row);
}

/* 速记卡（常见问题 + 术语表） */
function renderCheatSheet(ch) {
  if (!ch.qa && !ch.glossary) return null;
  const card = el('div', 'card');
  let html = '<h3>📌 本章速记卡 <span class="muted" style="font-weight:400;font-size:12.5px">通关后巩固：常见问题 + 重点词汇</span></h3>';
  if (ch.glossary && ch.glossary.length) {
    html += '<div class="glossary-wrap">' + ch.glossary.map(g =>
      '<div class="gl-item"><span class="gl-term">' + esc(g.term) + '</span><span class="gl-desc">' + esc(g.desc) + '</span></div>').join('') + '</div>';
  }
  if (ch.qa && ch.qa.length) {
    html += '<div class="qa-list">' + ch.qa.map(q =>
      '<div class="qa-item"><div class="qa-q">❓ ' + esc(q.q) + '<span class="qa-arrow">▾</span></div>' +
      '<div class="qa-a"><div class="md">' + md(q.a) + '</div></div></div>').join('') + '</div>';
  }
  card.innerHTML = html;
  card.querySelectorAll('.qa-item').forEach(item => {
    item.addEventListener('click', () => item.classList.toggle('open'));
  });
  return card;
}

/* ---------------- 面试宝典 ---------------- */
async function renderInterview() {
  const v = $('#view');
  if (!S.interview) {
    v.innerHTML = '<div class="muted" style="text-align:center;padding:60px">加载中…</div>';
    S.interview = await api('/api/interview');
  }
  const iv = S.interview;
  v.innerHTML = '';
  const head = el('div', 'card');
  head.innerHTML = '<h2 class="view-title">🎤 ' + esc(iv.title || '大数据面试宝典') + '</h2>' +
    '<div class="sub">' + esc(iv.intro || '') + '</div>' +
    '<label class="iv-mode"><input type="checkbox" id="iv-self"> 自测模式：点开问题不自动标记「已复习」，确认答对后手动勾选</label>';
  v.appendChild(head);

  iv.categories.forEach(cat => {
    const card = el('div', 'card iv-cat');
    const read = readReviewed(cat.id);
    card.innerHTML = '<h3>' + esc(cat.emoji) + ' ' + esc(cat.title) +
      ' <span class="muted iv-prog" style="font-weight:400;font-size:12.5px">' + read.size + '/' + cat.items.length + ' 已复习</span></h3>' +
      '<div class="iv-items">' + cat.items.map((it, i) =>
        '<div class="iv-item' + (read.has(String(i)) ? ' reviewed' : '') + '" data-i="' + i + '">' +
        '<div class="iv-q">Q' + (i + 1) + '. ' + esc(it.q) + '<span class="qa-arrow">▾</span></div>' +
        '<div class="iv-a"><div class="iv-a-body md">' + md(it.a) + '</div>' +
        (it.followup ? '<div class="iv-fu">🔁 面试官可能追问：' + esc(it.followup) + '</div>' : '') +
        '<button class="btn btn-sm iv-ok">✓ 我答对了，标记已复习</button></div></div>').join('') + '</div>';
    v.appendChild(card);

    card.querySelectorAll('.iv-item').forEach(item => {
      const qBtn = item.querySelector('.iv-q');
      qBtn.addEventListener('click', () => {
        const open = item.classList.toggle('open');
        if (open) {
          const selfMode = $('#iv-self') && $('#iv-self').checked;
          if (!selfMode) markReviewed(cat.id, item.dataset.i, card);
        }
      });
      const okBtn = item.querySelector('.iv-ok');
      okBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        markReviewed(cat.id, item.dataset.i, card);
        item.classList.add('reviewed');
      });
    });
  });

  const cb = $('#iv-self');
  if (cb) {
    cb.checked = localStorage.getItem('iv_self') === '1';
    cb.addEventListener('change', () => localStorage.setItem('iv_self', cb.checked ? '1' : '0'));
  }
}

function readReviewed(catId) {
  try { return new Set((localStorage.getItem('iv_' + catId) || '').split(',').filter(Boolean)); }
  catch (e) { return new Set(); }
}
function markReviewed(catId, i, card) {
  try {
    const set = readReviewed(catId);
    set.add(String(i));
    localStorage.setItem('iv_' + catId, Array.from(set).join(','));
    const prog = card.querySelector('.iv-prog');
    if (prog) prog.textContent = set.size + '/' + card.querySelectorAll('.iv-item').length + ' 已复习';
  } catch (e) { /* ignore */ }
}

/* ---------------- 任务渲染 ---------------- */
const TYPE_LABEL = {
  choice: '单选', multi: '多选', fill: '填空', order: '排序', sql: 'SQL 实战', python: '编程实战',
};

function renderTask(task, no, total) {
  const solved = solvedOf(task.task_id);
  const wrap = el('div', 'task-card' + (solved ? ' solved' : ''));
  const head = el('div', 'task-head');
  head.innerHTML =
    '<span class="task-type">' + (TYPE_LABEL[task.type] || task.type) + '</span>' +
    '<span class="task-title">任务 ' + no + '/' + total + '：' + esc(task.title) + '</span>' +
    '<span class="task-diff">' + '★'.repeat(task.difficulty || 1) + '</span>' +
    (solved ? '<span class="task-type" style="border-color:#2ecc71;color:#2ecc71">✅ 已通过</span>' : '');
  const q = el('div', 'task-question md');
  q.innerHTML = md(task.question);

  const body = el('div', 'task-body');
  let getAnswer = null;

  if (task.type === 'choice' || task.type === 'multi') {
    const list = el('div', 'opt-list');
    const selected = new Set();
    task.options.forEach((o, i) => {
      const item = el('div', 'opt-item');
      item.innerHTML = '<span class="ol">' + ('ABCDEFGHIJKLMNOPQRSTUVWXYZ'[i] || (i + 1)) + '</span><span class="md">' + md(o.text) + '</span>';
      item.addEventListener('click', () => {
        if (solved) return;
        if (task.type === 'choice') {
          selected.clear();
          list.querySelectorAll('.opt-item').forEach(x => x.classList.remove('selected'));
        }
        if (selected.has(String(i))) { selected.delete(String(i)); item.classList.remove('selected'); }
        else { selected.add(String(i)); item.classList.add('selected'); }
      });
      list.appendChild(item);
    });
    body.appendChild(list);
    if (task.type === 'multi') body.appendChild(el('div', 'quiz-note', '可多选，点击再次选择可取消。'));
    getAnswer = task.type === 'choice'
      ? () => (selected.size ? Array.from(selected)[0] : null)
      : () => Array.from(selected);
  } else if (task.type === 'fill') {
    const input = el('input');
    input.type = 'text';
    input.placeholder = '在此输入答案…';
    input.disabled = solved;
    body.appendChild(input);
    getAnswer = () => input.value;
  } else if (task.type === 'order') {
    const steps = task.steps;
    const picked = [];
    const box = el('div', 'order-steps');
    const seq = el('div', 'order-seq');
    const render = () => {
      box.innerHTML = '';
      steps.forEach((s, i) => {
        const c = el('div', 'order-chip' + (picked.includes(i) ? ' picked' : ''));
        c.innerHTML = '<span class="ol">' + (i + 1) + '</span><span>' + esc(s) + '</span>';
        c.addEventListener('click', () => {
          if (solved || picked.includes(i)) return;
          picked.push(i);
          render();
        });
        box.appendChild(c);
      });
      seq.innerHTML = picked.length ? picked.map((idx, k) =>
        '<div class="order-seq-item"><span class="os">' + (k + 1) + '.</span>' + esc(steps[idx]) + '</div>').join('')
        : '<div class="muted">按正确顺序依次点击左侧步骤</div>';
    };
    render();
    body.appendChild(box);
    body.appendChild(seq);
    const resetBtn = el('button', 'btn btn-ghost btn-sm', '↺ 重新选择');
    resetBtn.addEventListener('click', () => { picked.length = 0; render(); });
    body.appendChild(resetBtn);
    getAnswer = () => picked.slice();
  } else if (task.type === 'python' || task.type === 'sql') {
    const ta = el('textarea');
    ta.value = (task.code_context || '').replace(/\\n/g, '\n');
    ta.rows = 6;
    ta.className = 'ed-ta';
    body.appendChild(ta);

    /* Tab 键缩进（Python 规范用 4 空格，避免 TabError）；Shift+Tab 反缩进 */
    ta.addEventListener('keydown', (e) => {
      if (e.key !== 'Tab') return;
      e.preventDefault();
      const start = ta.selectionStart;
      const end = ta.selectionEnd;
      if (e.shiftKey) {
        /* 反缩进：删除当前行行首最多 4 个空格 */
        const lineStart = ta.value.lastIndexOf('\n', start - 1) + 1;
        const lead = ta.value.slice(lineStart, start).match(/^ */)[0].length;
        const del = Math.min(4, lead);
        if (del > 0) {
          ta.value = ta.value.slice(0, lineStart) + ta.value.slice(lineStart + del);
          ta.selectionStart = ta.selectionEnd = Math.max(lineStart, start - del);
        }
      } else {
        /* 缩进：插入 4 空格（多行选中时给每行加缩进） */
        if (start !== end && ta.value.slice(start, end).indexOf('\n') >= 0) {
          let sel = ta.value.slice(start, end);
          sel = sel.split('\n').map(l => '    ' + l).join('\n');
          ta.value = ta.value.slice(0, start) + sel + ta.value.slice(end);
          ta.selectionStart = start;
          ta.selectionEnd = start + sel.length;
        } else {
          ta.value = ta.value.slice(0, start) + '    ' + ta.value.slice(end);
          ta.selectionStart = ta.selectionEnd = start + 4;
        }
      }
      ta.dispatchEvent(new Event('input'));
    });

    /* 实时高亮预览（与编辑区分离，杜绝覆盖层错位） */
    const pvId = 'pv-' + task.task_id;
    const previewBox = el('div', 'ed-preview-box');
    previewBox.innerHTML =
      '<div class="ed-preview-head"><span>🖥 代码高亮预览</span>' +
      '<label class="iv-mode" style="margin-left:auto"><input type="checkbox" id="' + pvId + '" checked> 显示预览</label></div>' +
      '<pre class="ed-preview"><code class="hl"></code></pre>';
    const preEl = previewBox.querySelector('pre');
    const codeEl = previewBox.querySelector('code');
    const pvCb = previewBox.querySelector('input');
    const pvLang = task.type === 'sql' ? 'sql' : 'python';
    const renderPreview = () => {
      try { codeEl.innerHTML = hl(ta.value, pvLang); } catch (e) { /* 预览失败不影响输入 */ }
    };
    let pvTimer = null;
    ta.addEventListener('input', () => { clearTimeout(pvTimer); pvTimer = setTimeout(renderPreview, 120); });
    pvCb.addEventListener('change', () => { preEl.style.display = pvCb.checked ? '' : 'none'; });
    renderPreview();
    body.appendChild(previewBox);

    if (task.type === 'python') {
      body.appendChild(el('div', 'quiz-note', '🧪 可先点「运行」查看你的输出，确认无误后再「提交判题」。运行环境：本机 Python（仅标准库）。'));
    } else {
      const details = el('details');
      details.innerHTML = '<summary style="cursor:pointer;font-size:13px;color:var(--text2)">📦 查看测试数据（本题表结构与数据）</summary><pre style="margin-top:8px"><code class="hl">' + esc(task.setup || '') + '</code></pre>';
      body.appendChild(details);
      body.appendChild(el('div', 'quiz-note', '🧪 可先点「运行」查看你的查询结果，确认无误后再「提交判题」。提交后在内存 SQLite 中与标准结果比对。'));
    }
    const runOut = el('div', 'run-out');
    body.appendChild(runOut);

    const runBtn = el('button', 'btn', '▶ 运行（看输出）');
    runBtn.addEventListener('click', async () => {
      /* 重新运行时：收回上一次判题反馈（错误/正确内容都清掉），只展示本次运行输出 */
      fb.innerHTML = '';
      analysis.innerHTML = '';
      const code = ta.value;
      if (!code.trim()) { toast('代码为空，先写代码再运行', 'gold'); return; }
      runBtn.disabled = true;
      runBtn.textContent = '运行中…';
      runOut.innerHTML = '<div class="muted">⏳ 运行中…</div>';
      try {
        runOut.innerHTML = '';
        if (task.type === 'python') {
          const res = await api('/api/run_code', { method: 'POST', body: { code } });
          if (res.ok) {
            runOut.appendChild(panel('🧪 你的运行输出', '<pre class="run-pre"><code class="hl">' + hl(res.stdout || '（无输出）', 'python') + '</code></pre>', 'run-ok'));
          } else {
            runOut.appendChild(panel('❌ 运行报错', '<pre class="run-pre err">' + esc(res.stderr) + '</pre>', 'run-bad'));
          }
        } else {
          const res = await api('/api/run_sql', { method: 'POST', body: { task_id: task.task_id, sql: code } });
          if (res.ok) {
            runOut.appendChild(panel('🧪 你的查询结果（共 ' + res.rows.length + ' 行）', renderTableHTML(res.cols, res.rows), 'run-ok'));
          } else {
            runOut.appendChild(panel('❌ SQL 执行出错', '<pre class="run-pre err">' + esc(res.error) + '</pre>', 'run-bad'));
          }
        }
      } catch (e) {
        runOut.innerHTML = '';
        runOut.appendChild(panel('运行失败', '<pre class="run-pre err">' + esc(e.message) + '</pre>', 'run-bad'));
      }
      runBtn.disabled = false;
      runBtn.textContent = '▶ 运行（看输出）';
      /* 运行结束后把焦点还给代码框，方便直接继续输入 */
      try {
        ta.focus();
        const len = ta.value.length;
        ta.setSelectionRange(len, len);
      } catch (e) { /* ignore */ }
    });

    const actions = el('div', 'task-actions');
    const btn = el('button', 'btn btn-primary', '提交判题');
    const tryNote = el('span', 'try-note', '');
    actions.appendChild(runBtn);
    actions.appendChild(btn);
    actions.appendChild(tryNote);
    const fb = el('div', '');
    const analysis = el('div', '');
    wrap.appendChild(head);
    wrap.appendChild(q);
    wrap.appendChild(body);
    wrap.appendChild(actions);
    wrap.appendChild(fb);
    wrap.appendChild(analysis);

    if (solved) {
      btn.disabled = true;
      btn.textContent = '✅ 已完成';
      renderAnalysis(analysis, task, { analysis: task.analysis, reference: task.reference, enterprise_tip: task.enterprise_tip }, true);
      return wrap;
    }
    btn.addEventListener('click', async () => {
      const answer = ta.value;
      if (!answer.trim()) { toast('请先编写代码再提交', 'gold'); return; }
      btn.disabled = true;
      btn.textContent = '判定中…';
      try {
        const res = await api('/api/submit', { method: 'POST', body: { task_id: task.task_id, answer } });
        applySnap(res.snapshot);
        btn.disabled = false;
        btn.textContent = '提交判题';
        if (res.correct) {
          S.combo += 1;
          wrap.classList.add('solved');
          confetti();
          tryNote.textContent = res.already ? '该题之前已通过' : '第 ' + res.attempts + ' 次尝试通过';
          btn.disabled = true;
          btn.textContent = '✅ 已完成';
          toast('🎉 回答正确' + (res.xp ? ' +' + res.xp + ' XP' : '') + (S.combo >= 2 ? '（连击 x' + S.combo + '）' : ''), 'good');
          res.new_badges.forEach(b => toast('🏅 获得徽章：' + b.icon + ' ' + b.name, 'gold'));
          renderAnalysis(analysis, task, res, false);
          updateChapterFooter();
        } else {
          S.combo = 0;
          renderFeedback(fb, res, task);
          tryNote.textContent = '第 ' + res.attempts + ' 次尝试未通过';
          if (res.attempts >= 2) {
            const reveal = el('button', 'btn btn-sm', '💡 查看标准解题思路');
            reveal.addEventListener('click', () => {
              renderAnalysis(analysis, task, res, true);
              reveal.disabled = true;
              reveal.textContent = '📖 已显示';
            });
            fb.appendChild(reveal);
          }
          toast('❌ 没通过，看下方分析你的问题在哪里', '');
        }
      } catch (e) {
        btn.disabled = false;
        btn.textContent = '提交判题';
        toast('提交失败：' + e.message, '');
      }
    });
    return wrap;
  }

  /* 非代码题：通用操作区 */
  const actions = el('div', 'task-actions');
  const btn = el('button', 'btn btn-primary', '提交答案');
  const tryNote = el('span', 'try-note', '');
  const fb = el('div', '');
  const analysis = el('div', '');
  if (solved) {
    tryNote.textContent = '已通过' + (attemptsOf(task.task_id) > 1 ? '（尝试 ' + attemptsOf(task.task_id) + ' 次）' : '');
  }
  actions.appendChild(btn);
  actions.appendChild(tryNote);
  wrap.appendChild(head);
  wrap.appendChild(q);
  wrap.appendChild(body);
  wrap.appendChild(actions);
  wrap.appendChild(fb);
  wrap.appendChild(analysis);

  if (solved) {
    btn.disabled = true;
    btn.textContent = '✅ 已完成';
    renderAnalysis(analysis, task, { analysis: task.analysis, reference: task.reference, enterprise_tip: task.enterprise_tip }, true);
    return wrap;
  }
  btn.addEventListener('click', async () => {
    const answer = getAnswer();
    if (answer === null || answer === undefined || (Array.isArray(answer) && !answer.length) || (typeof answer === 'string' && !answer.trim())) {
      toast('请先完成题目再提交', 'gold');
      return;
    }
    btn.disabled = true;
    btn.textContent = '判定中…';
    try {
      const res = await api('/api/submit', { method: 'POST', body: { task_id: task.task_id, answer } });
      applySnap(res.snapshot);
      btn.disabled = false;
      btn.textContent = '提交答案';
      if (res.correct) {
        S.combo += 1;
        wrap.classList.add('solved');
        confetti();
        tryNote.textContent = res.already ? '该题之前已通过' : '第 ' + res.attempts + ' 次尝试通过';
        btn.disabled = true;
        btn.textContent = '✅ 已完成';
        toast('🎉 回答正确' + (res.xp ? ' +' + res.xp + ' XP' : '') + (S.combo >= 2 ? '（连击 x' + S.combo + '）' : ''), 'good');
        res.new_badges.forEach(b => toast('🏅 获得徽章：' + b.icon + ' ' + b.name, 'gold'));
        renderAnalysis(analysis, task, res, false);
        updateChapterFooter();
      } else {
        S.combo = 0;
        renderFeedback(fb, res, task);
        tryNote.textContent = '第 ' + res.attempts + ' 次尝试未通过';
        if (res.attempts >= 2) {
          const reveal = el('button', 'btn btn-sm', '💡 查看标准解题思路');
          reveal.addEventListener('click', () => {
            renderAnalysis(analysis, task, res, true);
            reveal.disabled = true;
            reveal.textContent = '📖 已显示';
          });
          fb.appendChild(reveal);
        }
        toast('❌ 没通过，看下方分析你的问题在哪里', '');
      }
    } catch (e) {
      btn.disabled = false;
      btn.textContent = '提交答案';
      toast('提交失败：' + e.message, '');
    }
  });
  return wrap;
}

function panel(title, html, cls) {
  const p = el('div', 'run-panel ' + (cls || ''));
  p.innerHTML = '<div class="rp-title">' + title + '</div>' + html;
  return p;
}

function renderTableHTML(cols, rows) {
  if (!cols || !cols.length) return '<div class="muted">（无结果）</div>';
  return '<div class="result-table"><table><thead><tr>' +
    cols.map(c => '<th>' + esc(c) + '</th>').join('') + '</tr></thead><tbody>' +
    rows.map(r => '<tr>' + r.map(c => '<td>' + esc(c) + '</td>').join('') + '</tr>').join('') +
    '</tbody></table></div>';
}

/* 判题反馈：始终先展示「你的运行结果」，再给差异分析 */
function renderFeedback(fb, res, task) {
  fb.innerHTML = '';
  const panelEl = el('div', 'fb-panel fb-bad');
  let html = '';
  if (res.user_display) {
    if (task && task.type === 'sql') {
      html += '<div class="fb-row"><span class="ft">🧪 你的查询结果（共 ' + res.user_display.row_count + ' 行）</span></div>' +
        renderTableHTML(res.user_display.cols, res.user_display.rows);
    } else {
      html += '<div class="fb-row"><span class="ft">🧪 你的运行输出</span></div><pre class="run-pre"><code class="hl">' +
        hl(res.user_display.stdout || '（无输出）', 'python') + '</code></pre>';
    }
  }
  html += (res.feedback || []).map(f => {
    const cls = f.type === 'error' ? 'ft' : (f.type === 'ok' ? 'ft ok' : 'ft ' + f.type);
    const icon = f.type === 'error' ? '❌' : (f.type === 'ok' ? '✅' : (f.type === 'hint' ? '💡' : '🔍'));
    const body = f.text ? '<pre>' + esc(f.text) + '</pre>' : '';
    return '<div class="fb-row"><span class="' + cls + '">' + icon + ' ' + esc(f.title) + '</span>' + body + '</div>';
  }).join('');
  /* 答错时不展示标准结果（标准答案只在答对或主动查看标准解题思路后显示） */
  panelEl.innerHTML = html || '<div class="fb-row"><span class="ft">❌ 未通过</span></div>';
  fb.appendChild(panelEl);
}

/* 标准解题思路 */
function renderAnalysis(analysis, task, res, isReveal) {
  analysis.innerHTML = '';
  const panelEl = el('div', 'analysis-panel');
  let html = '<h4>' + (isReveal ? '📖 标准解题思路（参考答案）' : '📖 标准解题思路') + '</h4>';
  if (isReveal) html += '<div class="muted" style="font-size:12.5px;margin-bottom:6px">先自己再想想，再对照答案。反复练习才能形成肌肉记忆。</div>';
  html += '<div class="md">' + md(res.analysis || '') + '</div>';

  if (task.type === 'python') {
    if (res.user_display) {
      html += '<div class="gap"><b>🧪 你的输出：</b></div><pre><code class="hl">' + hl(res.user_display.stdout || '（无输出）', 'python') + '</code></pre>';
    }
    if (res.expected_display && res.expected_display.stdout !== undefined) {
      html += '<div class="gap"><b>✅ 期望输出：</b></div><pre><code class="hl">' + hl(res.expected_display.stdout, 'python') + '</code></pre>';
    }
    if (res.reference) {
      html += '<div class="gap"><b>✅ 标准答案代码：</b></div><pre><code class="hl">' + hl(res.reference, 'python') + '</code></pre>';
    }
  }
  if (task.type === 'sql') {
    if (res.expected_display && res.expected_display.sql) {
      html += '<div class="gap"><b>✅ 标准 SQL：</b></div><pre><code class="hl">' + hl(res.expected_display.sql, 'sql') + '</code></pre>';
    }
    if (res.expected_display && res.expected_display.cols && res.expected_display.cols.length) {
      html += '<div class="gap"><b>标准结果（共 ' + res.expected_display.row_count + ' 行，显示前 ' + res.expected_display.rows.length + ' 行）：</b></div>' +
        renderTableHTML(res.expected_display.cols, res.expected_display.rows);
    }
  }
  if (res.enterprise_tip) {
    html += '<div class="enterprise-panel">🏢 <b>企业实战提示：</b>' + md(res.enterprise_tip) + '</div>';
  }
  panelEl.innerHTML = html;
  analysis.appendChild(panelEl);
}

/* ---------------- 打卡 ---------------- */
async function doCheckin() {
  try {
    const res = await api('/api/checkin', { method: 'POST', body: {} });
    applySnap(res.snapshot);
    if (res.new) {
      toast('📌 打卡成功 +' + res.xp + ' XP，连续 ' + res.streak + ' 天', 'good');
      res.new_badges.forEach(b => toast('🏅 获得徽章：' + b.icon + ' ' + b.name, 'gold'));
    } else {
      toast('今天已经打过卡啦', '');
    }
  } catch (e) { toast('打卡失败：' + e.message, ''); }
}

/* ---------------- 侧边栏：拖拽调宽 + 悬停提示 ---------------- */
function initSidebarResize() {
  const sb = $('#sidebar');
  try {
    const w = parseInt(localStorage.getItem('sidebar_w'), 10);
    if (w && w >= 170 && w <= 480) sb.style.width = w + 'px';
  } catch (e) { /* ignore */ }
  const handle = $('#sb-resize');
  if (!handle) return;
  let dragging = false;
  const endResize = () => {
    if (!dragging) return;
    dragging = false;
    document.body.classList.remove('resizing');
    try { localStorage.setItem('sidebar_w', String(parseInt(sb.style.width, 10) || 268)); } catch (e) { /* ignore */ }
  };
  handle.addEventListener('mousedown', (e) => {
    dragging = true;
    document.body.classList.add('resizing');
    e.preventDefault();
  });
  document.addEventListener('mousemove', (e) => {
    if (!dragging) return;
    const w = Math.max(170, Math.min(480, e.clientX));
    sb.style.width = w + 'px';
  });
  document.addEventListener('mouseup', endResize);
  document.addEventListener('pointerup', endResize);
  window.addEventListener('blur', endResize); /* 鼠标在窗口外松开也结束拖拽 */
}

function initTooltips() {
  const tip = el('div', 'sb-tip');
  document.body.appendChild(tip);
  document.addEventListener('mouseover', (e) => {
    const t = e.target.closest('[data-full]');
    if (!t || t.dataset.full === t.textContent.trim()) {
      tip.style.display = 'none';
      return;
    }
    tip.textContent = t.dataset.full;
    const r = t.getBoundingClientRect();
    tip.style.display = 'block';
    tip.style.left = Math.min(window.innerWidth - 360, r.right + 12) + 'px';
    tip.style.top = Math.max(8, r.top + r.height / 2 - 12) + 'px';
  });
  document.addEventListener('mouseout', (e) => {
    if (e.target.closest('[data-full]')) tip.style.display = 'none';
  });
}

/* ---------------- 启动 ---------------- */
(async function init() {
  try {
    const data = await api('/api/bootstrap');
    S.app = data.app;
    S.snap = data.snapshot;
    const byType = {};
    await Promise.all(S.snap.stages.map(async st => {
      try {
        const full = await api('/api/stage/' + st.stage_id);
        S.stageCache[st.stage_id] = full;
        full.chapters.forEach(ch => (ch.tasks || []).forEach(t => {
          byType[t.type] = (byType[t.type] || 0) + 1;
        }));
      } catch (e) { /* 忽略 */ }
    }));
    S.snap.total_by_type = byType;
    $('#logo').addEventListener('click', goHome);
    initSidebarResize();
    initTooltips();
    goHome();
  } catch (e) {
    $('#view').innerHTML = '<div class="card">加载失败：' + esc(e.message) + '<br>请确认服务已启动（双击 start.bat）。</div>';
  }
})();
