// SPDX-License-Identifier: Apache-2.0
'use strict';
const $ = id => document.getElementById(id);
const translations = {
  zh: {brand:'随机键入 · 自由草稿',local:'仅在本地运行',title:'让字符，随心落下。',subtitle:'设置节奏，开始随机键入。这里也是你的自由草稿空间。',settings:'键入设置',rhythm:'随机间隔范围',fast:'快 · 每秒 30 次',slow:'慢 · 每 5 分钟 1 次',jitter:'实际间隔在下方最小值与最大值之间随机取值',minimum:'最小间隔（秒）',maximum:'最大间隔（秒）',hint:'按任意键退出随机键入模式',clear:'一键清屏',draft:'草稿记录',characters:'个字符',unlimited:'自由编辑 · 无长度限制',footer:'为简单的键入而生',start:'三秒后开始键入',cancel:'取消 / 停止',ready:'就绪',running:'随机键入中',countdown:'秒后开始',placeholder:'从这里开始，写点什么……',saved:'草稿自动保存在此浏览器',unsaved:'浏览器存储已满或不可用，草稿仅保留在当前页面',invalid:'请输入有效间隔：1/30 至 300 秒，且最小值不得大于最大值。'},
  en: {brand:'Random typing · Free drafting',local:'Runs locally',title:'Let the characters flow.',subtitle:'Find your rhythm and start typing at random. A little space for your own words, too.',settings:'Typing settings',rhythm:'Random interval range',fast:'Fast · 30 times / second',slow:'Slow · Once / 5 minutes',jitter:'Each interval is randomly chosen between the bounds',minimum:'Minimum interval (seconds)',maximum:'Maximum interval (seconds)',hint:'Press any key to exit random typing mode',clear:'Clear draft',draft:'Draft space',characters:'characters',unlimited:'Edit freely · No length limit',footer:'A little space to type',start:'Start typing in 3 seconds',cancel:'Cancel / Stop',ready:'Ready',running:'Typing at random',countdown:'seconds to start',placeholder:'Start here. Make room for a thought…',saved:'Draft autosaved in this browser',unsaved:'Browser storage is full or unavailable; draft is kept in this page only',invalid:'Enter valid intervals from 1/30 to 300 seconds. Minimum must not exceed maximum.'}
};
let lang = 'zh', mode = 'idle', timer, countdown = 3, storageOK = true;
const alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
const minimum = 1 / 30;
try { $('draft').value = localStorage.getItem('typper-draft') || ''; lang = localStorage.getItem('typper-language') === 'en' ? 'en' : 'zh'; } catch { storageOK = false; }
function render() {
  const t = translations[lang];
  document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
  document.querySelectorAll('[data-i18n]').forEach(el => el.textContent = t[el.dataset.i18n]);
  $('draft').placeholder = t.placeholder; $('draft').setAttribute('aria-label', t.draft);
  $('start-label').textContent = mode === 'idle' ? t.start : t.cancel;
  $('status').textContent = mode === 'running' ? t.running : mode === 'countdown' ? `${countdown} ${t.countdown}` : t.ready;
  $('status').classList.toggle('running', mode !== 'idle');
  $('save-note').textContent = storageOK ? t.saved : t.unsaved;
  $('speed-text').textContent = `${Number($('minimum').value).toLocaleString(lang,{maximumFractionDigits:4})} – ${Number($('maximum').value).toLocaleString(lang,{maximumFractionDigits:4})} ${lang === 'zh' ? '秒 / 次' : 's / character'}`;
  $('minimum').disabled = $('maximum').disabled = $('speed').disabled = mode !== 'idle';
}
function save() {
  $('count').textContent = $('draft').value.length.toLocaleString();
  try { localStorage.setItem('typper-draft', $('draft').value); storageOK = true; } catch { storageOK = false; }
  $('save-note').textContent = translations[lang][storageOK ? 'saved' : 'unsaved'];
}
function stop() { clearTimeout(timer); mode = 'idle'; render(); }
function schedule() {
  const low = Number($('minimum').value), high = Number($('maximum').value);
  timer = setTimeout(() => {
    if (mode !== 'running') return;
    const draft = $('draft'), position = draft.selectionStart;
    draft.setRangeText(alphabet[Math.floor(Math.random() * alphabet.length)], position, draft.selectionEnd, 'end');
    draft.scrollTop = draft.scrollHeight; save(); schedule();
  }, (low + Math.random() * (high - low)) * 1000);
}
$('start').addEventListener('click', () => {
  if (mode !== 'idle') { stop(); return; }
  const low = Number($('minimum').value), high = Number($('maximum').value);
  if (!$('minimum').value || !$('maximum').value || !Number.isFinite(low) || !Number.isFinite(high) || low < minimum || high > 300 || low > high) { $('error').textContent = translations[lang].invalid; return; }
  $('error').textContent = ''; mode = 'countdown'; countdown = 3; render();
  function tick() { timer = setTimeout(() => { countdown--; if (countdown === 0) { mode = 'running'; $('draft').focus(); render(); schedule(); } else { render(); tick(); } }, 1000); }
  tick();
});
document.addEventListener('keydown', event => { if (mode !== 'idle') { event.preventDefault(); event.stopPropagation(); stop(); } }, true);
$('clear').addEventListener('click', () => { stop(); $('draft').value = ''; save(); });
$('draft').addEventListener('input', save);
$('language').addEventListener('click', () => { lang = lang === 'zh' ? 'en' : 'zh'; try {localStorage.setItem('typper-language',lang);} catch {} $('error').textContent = ''; render(); });
$('speed').addEventListener('input', () => {
  const value = minimum * Math.pow(300 / minimum, Number($('speed').value) / 1000);
  $('minimum').value = Math.max(minimum, value / 1.5).toPrecision(8);
  if (Number($('minimum').value) < minimum) $('minimum').value = minimum;
  $('maximum').value = Math.min(300, value * 1.5).toPrecision(8);
  // Slider endpoints allow an exact fixed frequency at both limits.
  if ($('speed').value === '0') $('minimum').value = $('maximum').value = minimum;
  if ($('speed').value === '1000') $('minimum').value = $('maximum').value = 300;
  $('error').textContent = ''; render();
});
for (const id of ['minimum','maximum']) $(id).addEventListener('input', () => { $('error').textContent = ''; render(); });
// Leaving the page cancels a pending start or typing session.
window.addEventListener('pagehide', stop);
render(); save();
