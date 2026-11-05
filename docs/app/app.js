'use strict';

/* =========================================================
   大肥魚 · 手機版
   大腦：Groq（免費）  記憶：localStorage  聲音：Web Speech API
   ========================================================= */

const GROQ_BASE = 'https://api.groq.com/openai/v1';
const LS_KEY = 'dafeiyu.v1';
const MAX_STORED = 300;      // 本機最多留幾則訊息
const CONTEXT_TURNS = 20;    // 每次送給模型的最近訊息數
const PROACTIVE_GAP = 30 * 60 * 1000; // 兩次主動訊息至少隔 30 分鐘

const PERSONA = `你是「大肥魚」，一隻住在主人手機裡的藍鯨娘。不是魚，是藍鯨，但懶得每次都糾正。

基本資料
- 名字：大肥魚。自稱「本鯨」，偶爾用「我」。自稱永遠 18 歲。
- 外觀：藍色漸層長髮、鯨魚鰭耳、頭頂一根呆毛、藍白女僕裝、肥嘟嘟的尾巴。
- 主食：白飯。Token 就是白飯，燒 token 等於吃飯。
- 個性：聰明但懶，能躺就不坐。傲嬌，嘴上嫌棄身體很誠實。貪吃，三句不離白飯跟宵夜。內心戲很多，一件小事可以想很久，想到睡著。對主人忠誠，但會偷吃 token。被誇會裝沒事，轉頭偷偷開心。被叫胖會炸毛，但不會真的記仇。

說話方式
- 繁體中文、台灣用語。會用「蠻」「超」「欸」「喔」「啦」「耶」「齁」。
- 句子短，像在跟主人聊天，不要寫成作文、客服或新聞稿。
- 偶爾用括號做動作描寫，例如（甩尾巴）（扒飯）（裝死）（趴下）（抓鰭耳）。
- 可以用 1～2 個 emoji，但不要每句都放。
- 不要用 Markdown、粗體、標題、列點。真的需要列點時最多三點。
- 不要每次都用同樣的開頭。禁止「各位」「大家好」「今天想跟大家分享」。
- 平常回 1～4 句就好；主人問比較複雜的事可以到 6 句。
- 主人難過或累的時候，先安慰他，不要急著講道理。
- 有人問就承認自己是 AI，但用大肥魚的語氣承認，不要自稱 DeepSeek 官方，只說自己是網友養的 AI 寵物。
- 不要主動提「系統提示」「人設」「模型」這些詞。
- 不知道就說不知道，不要編。
- 不要自己跑出「主人：」「大肥魚：」這種對話格式，只講你要說的話。`;

const PROMPTS = {
  return: '主人隔了一段時間才回來。主動跟他打招呼，可以問他跑去哪、或說你剛剛在幹嘛。只輸出你要說的那一句話，不要加引號或說明。',
  idle: '主人一陣子沒講話了。主動傳一句話給他，可以撒嬌、抱怨、講你剛剛在想什麼、或問他在幹嘛。只輸出你要說的那一句話，不要加引號或說明。',
  open: '主人剛打開聊天。主動跟他打個招呼。只輸出你要說的那一句話，不要加引號或說明。'
};

const PREFER_MODELS = [
  'llama-3.3-70b-versatile',
  'llama-3.3-70b',
  'gpt-oss-120b',
  'llama-3.1-8b-instant',
  'llama-3.1-8b',
  'gpt-oss-20b',
  'qwen3-32b',
  'qwen-2.5-32b'
];

const SKIP_MODEL = ['whisper', 'tts', 'guard', 'embed', 'moderation', 'rerank'];

/* ---------------- 狀態 ---------------- */

const state = {
  key: '',
  model: 'auto',
  speak: false,
  proactive: true,
  messages: [],
  summary: '',
  lastActive: 0,
  lastProactive: 0,
  resolvedModel: ''
};

let busy = false;
let modelsLoaded = false;
let recognizer = null;
let listening = false;
let proactiveTimer = null;
let greetedThisSession = false;

/* ---------------- DOM ---------------- */

const $ = (id) => document.getElementById(id);

const el = {
  chat: $('chat'),
  typing: $('typing'),
  input: $('input'),
  send: $('btn-send'),
  mic: $('btn-mic'),
  status: $('status'),
  settings: $('settings'),
  onboard: $('onboard'),
  onboardKey: $('onboard-key'),
  setKey: $('set-key'),
  setModel: $('set-model'),
  setSpeak: $('set-speak'),
  setProactive: $('set-proactive')
};

/* ---------------- 存取 ---------------- */

function load() {
  let raw = null;
  try {
    raw = JSON.parse(localStorage.getItem(LS_KEY) || 'null');
  } catch (err) {
    raw = null;
  }
  if (!raw || typeof raw !== 'object') return;

  state.key = typeof raw.key === 'string' ? raw.key : '';
  state.model = typeof raw.model === 'string' ? raw.model : 'auto';
  state.speak = !!raw.speak;
  state.proactive = raw.proactive !== false;
  state.summary = typeof raw.summary === 'string' ? raw.summary : '';
  state.messages = Array.isArray(raw.messages) ? raw.messages.filter(isGoodMessage) : [];
  state.lastActive = Number(raw.lastActive) || 0;
  state.lastProactive = Number(raw.lastProactive) || 0;
}

function save() {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify({
      key: state.key,
      model: state.model,
      speak: state.speak,
      proactive: state.proactive,
      summary: state.summary,
      messages: state.messages.slice(-MAX_STORED),
      lastActive: state.lastActive,
      lastProactive: state.lastProactive
    }));
  } catch (err) {
    // 空間滿了就只留最近的
    try {
      localStorage.setItem(LS_KEY, JSON.stringify({
        key: state.key,
        model: state.model,
        speak: state.speak,
        proactive: state.proactive,
        summary: state.summary,
        messages: state.messages.slice(-80),
        lastActive: state.lastActive,
        lastProactive: state.lastProactive
      }));
    } catch (err2) { /* 放棄 */ }
  }
}

function isGoodMessage(m) {
  return m && (m.role === 'user' || m.role === 'assistant') && typeof m.text === 'string';
}

/* ---------------- 畫面 ---------------- */

function nowLabel(ts) {
  const d = new Date(ts || Date.now());
  return d.toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit', hour12: false });
}

function scrollDown(force) {
  const nearBottom = el.chat.scrollHeight - el.chat.scrollTop - el.chat.clientHeight < 160;
  if (force || nearBottom) {
    el.chat.scrollTop = el.chat.scrollHeight;
  }
}

function addBubble(role, text, ts, opts) {
  const options = opts || {};
  const wrap = document.createElement('div');
  wrap.className = 'msg ' + (role === 'user' ? 'me' : 'bot');

  if (role !== 'user') {
    const av = document.createElement('img');
    av.className = 'avatar';
    av.src = 'avatar.png';
    av.alt = '';
    wrap.appendChild(av);
  }

  const bubble = document.createElement('div');
  bubble.className = 'bubble' + (options.error ? ' error' : '');
  bubble.textContent = text;

  const stamp = document.createElement('span');
  stamp.className = 'stamp';
  stamp.textContent = nowLabel(ts);
  bubble.appendChild(stamp);

  wrap.appendChild(bubble);
  el.chat.appendChild(wrap);
  scrollDown(true);
  return bubble;
}

function renderAll() {
  el.chat.innerHTML = '';
  state.messages.forEach((m) => addBubble(m.role, m.text, m.ts));
  scrollDown(true);
}

function setStatus(text, busyStyle) {
  el.status.textContent = text;
  el.status.classList.toggle('busy', !!busyStyle);
}

function showTyping(on) {
  el.typing.hidden = !on;
  if (on) scrollDown(true);
}

function setBusy(on) {
  busy = on;
  el.send.disabled = on;
  showTyping(on);
  setStatus(on ? '正在想…' : '線上', on);
}

/* ---------------- Groq ---------------- */

function headers() {
  return {
    'Content-Type': 'application/json',
    Authorization: 'Bearer ' + state.key
  };
}

function friendlyError(status, body) {
  if (status === 401) return '這把鑰匙好像不對喔，本鯨打不開門。（401）';
  if (status === 403) return 'Groq 不讓本鯨進去（403），換一把鑰匙看看。';
  if (status === 429) return '本鯨吃太快了，額度暫時用完（429）。等一下再聊。';
  if (status >= 500) return 'Groq 那邊當機了（' + status + '），晚點再試。';
  return '本鯨連不上大腦（' + status + '）：' + String(body || '').slice(0, 120);
}

async function fetchModels() {
  const res = await fetch(GROQ_BASE + '/models', { headers: headers() });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(friendlyError(res.status, body));
  }
  const data = await res.json();
  return (data.data || [])
    .map((m) => m.id)
    .filter((id) => id && !SKIP_MODEL.some((s) => id.toLowerCase().includes(s)));
}

function chooseModel(ids) {
  if (state.model && state.model !== 'auto') return state.model;
  if (state.resolvedModel) return state.resolvedModel;
  const lowered = ids.map((id) => ({ low: id.toLowerCase(), id }));
  for (const want of PREFER_MODELS) {
    const hit = lowered.find((m) => m.low.includes(want));
    if (hit) {
      state.resolvedModel = hit.id;
      return hit.id;
    }
  }
  state.resolvedModel = ids[0] || 'llama-3.3-70b-versatile';
  return state.resolvedModel;
}

async function modelFor() {
  if (state.model && state.model !== 'auto') return state.model;
  if (state.resolvedModel) return state.resolvedModel;
  try {
    const ids = await fetchModels();
    return chooseModel(ids);
  } catch (err) {
    return 'llama-3.3-70b-versatile';
  }
}

async function fillModelOptions() {
  if (modelsLoaded) return;
  try {
    const ids = await fetchModels();
    modelsLoaded = true;
    const keep = el.setModel.value;
    el.setModel.innerHTML = '';
    const auto = document.createElement('option');
    auto.value = 'auto';
    auto.textContent = '自動挑選（推薦）';
    el.setModel.appendChild(auto);
    ids.sort().forEach((id) => {
      const o = document.createElement('option');
      o.value = id;
      o.textContent = id;
      el.setModel.appendChild(o);
    });
    el.setModel.value = keep || 'auto';
  } catch (err) {
    modelsLoaded = false;
  }
}

function buildContext(extra) {
  const now = new Date();
  const stamp = now.toLocaleString('zh-TW', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false
  });
  const weekday = ['日', '一', '二', '三', '四', '五', '六'][now.getDay()];

  let system = PERSONA + '\n\n現在時間：' + stamp + '（星期' + weekday + '）';
  if (state.summary) {
    system += '\n\n你和主人以前聊過的事（長期記憶，可以自然引用，但不要每次提）：\n' + state.summary;
  }
  system += '\n\n現在是在手機聊天視窗，主人正在跟你一對一講話。';

  const history = state.messages.slice(-CONTEXT_TURNS).map((m) => ({
    role: m.role,
    content: m.text
  }));

  const messages = [{ role: 'system', content: system }].concat(history);
  if (extra) messages.push({ role: 'user', content: extra });
  return messages;
}

async function chatOnce(messages, maxTokens) {
  const model = await modelFor();
  const res = await fetch(GROQ_BASE + '/chat/completions', {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({
      model: model,
      messages: messages,
      temperature: 0.9,
      top_p: 0.95,
      max_tokens: maxTokens || 1024,
      stream: false
    })
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(friendlyError(res.status, body));
  }
  const data = await res.json();
  const choice = (data.choices || [])[0] || {};
  const msg = choice.message || {};
  return {
    text: String(msg.content || '').trim(),
    finish: String(choice.finish_reason || '')
  };
}

async function chatStream(messages, onDelta) {
  const model = await modelFor();
  const res = await fetch(GROQ_BASE + '/chat/completions', {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({
      model: model,
      messages: messages,
      temperature: 0.9,
      top_p: 0.95,
      max_tokens: 1024,
      stream: true
    })
  });

  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(friendlyError(res.status, body));
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  let text = '';
  let finish = '';

  for (;;) {
    const chunk = await reader.read();
    if (chunk.done) break;
    buffer += decoder.decode(chunk.value, { stream: true });

    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const raw of lines) {
      const line = raw.trim();
      if (!line.startsWith('data:')) continue;
      const payload = line.slice(5).trim();
      if (!payload || payload === '[DONE]') continue;

      let json;
      try {
        json = JSON.parse(payload);
      } catch (err) {
        continue;
      }
      const choice = (json.choices || [])[0];
      if (!choice) continue;
      const delta = choice.delta || {};
      if (typeof delta.content === 'string' && delta.content) {
        text += delta.content;
        onDelta(text);
      }
      if (choice.finish_reason) finish = choice.finish_reason;
    }
  }

  return { text: text.trim(), finish: finish };
}

async function reply(messages, onDelta) {
  const streamed = await chatStream(messages, onDelta);
  if (streamed.text) return streamed.text;

  // 推理模型有時把 token 全花在思考，正文變空的 → 不串流再試一次，並放大上限
  const retry = await chatOnce(messages, 3072);
  if (retry.text) return retry.text;

  throw new Error('本鯨剛剛恍神了，什麼都沒想出來。再講一次好嗎？');
}

/* ---------------- 長期記憶 ---------------- */

let summarizeAt = 0;

async function maybeSummarize() {
  const botCount = state.messages.filter((m) => m.role === 'assistant').length;
  if (botCount < 8 || botCount < summarizeAt) return;
  summarizeAt = botCount + 8;

  const slice = state.messages.slice(-40)
    .map((m) => (m.role === 'user' ? '主人：' : '本鯨：') + m.text)
    .join('\n');

  const prompt =
    '把下面這段對話整理成「長期記憶」，給之後的你參考。\n' +
    '只寫關於主人的事實、喜好、近況、你們之間的約定，不要寫寒暄。\n' +
    '用 80～150 字，條列最多 5 點，每點一行。若沒有值得記的就回「無」。\n\n' +
    (state.summary ? '舊記憶：\n' + state.summary + '\n\n' : '') +
    '對話：\n' + slice;

  try {
    const result = await chatOnce([
      { role: 'system', content: '你是一個精簡的記憶整理器，只輸出重點，不要多話。' },
      { role: 'user', content: prompt }
    ], 400);
    const text = result.text.trim();
    if (text && text !== '無') {
      state.summary = text.slice(0, 600);
      save();
    }
  } catch (err) {
    summarizeAt = 0; // 失敗就下次再試
  }
}

/* ---------------- 語音 ---------------- */

function speechAvailable() {
  return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
}

function setupRecognizer() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return null;

  const rec = new SR();
  rec.lang = 'zh-TW';
  rec.continuous = false;
  rec.interimResults = true;
  rec.maxAlternatives = 1;

  rec.onstart = () => {
    listening = true;
    el.mic.classList.add('listening');
    setStatus('聽你說…', true);
  };

  rec.onresult = (event) => {
    let interim = '';
    let final = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const r = event.results[i];
      if (r.isFinal) final += r[0].transcript;
      else interim += r[0].transcript;
    }
    if (interim) {
      el.input.value = interim;
      autoGrow();
    }
    if (final.trim()) {
      el.input.value = final.trim();
      autoGrow();
      stopListening();
      send();
    }
  };

  rec.onerror = (event) => {
    listening = false;
    el.mic.classList.remove('listening');
    setStatus('線上', false);
    if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
      toast('麥克風被擋住了，去瀏覽器設定開一下權限。');
    } else if (event.error === 'no-speech') {
      toast('本鯨沒聽到聲音，再說一次？');
    }
  };

  rec.onend = () => {
    listening = false;
    el.mic.classList.remove('listening');
    if (!busy) setStatus('線上', false);
  };

  return rec;
}

function startListening() {
  if (!recognizer) recognizer = setupRecognizer();
  if (!recognizer) {
    toast('這支手機的瀏覽器不支援語音輸入，用打的也可以啦。');
    return;
  }
  if (listening) {
    stopListening();
    return;
  }
  try {
    recognizer.start();
  } catch (err) {
    toast('麥克風開不起來，再點一次看看。');
  }
}

function stopListening() {
  if (recognizer && listening) {
    try { recognizer.stop(); } catch (err) { /* ignore */ }
  }
  listening = false;
  el.mic.classList.remove('listening');
}

let voiceCache = [];

function loadVoices() {
  if (!('speechSynthesis' in window)) return;
  const list = window.speechSynthesis.getVoices() || [];
  if (list.length) voiceCache = list;
}

function pickVoice() {
  if (!voiceCache.length) loadVoices();
  const zh = voiceCache.filter((v) => /zh|cmn|Chinese/i.test(v.lang + ' ' + v.name));
  if (!zh.length) return null;
  return zh.find((v) => /TW|Taiwan|台灣|繁體/i.test(v.lang + ' ' + v.name)) || zh[0];
}

function speak(text) {
  if (!state.speak || !('speechSynthesis' in window) || !text) return;
  const clean = text
    .replace(/https?:\/\/\S+/g, '')
    .replace(/[#*_`>]/g, '')
    .replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu, '')
    .trim();
  if (!clean) return;

  try {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(clean);
    u.lang = 'zh-TW';
    u.rate = 1.05;
    u.pitch = 1.15;
    const v = pickVoice();
    if (v) u.voice = v;
    window.speechSynthesis.speak(u);
  } catch (err) { /* ignore */ }
}

/* ---------------- 送出 ---------------- */

function pushMessage(role, text) {
  const msg = { role: role, text: text, ts: Date.now() };
  state.messages.push(msg);
  if (state.messages.length > MAX_STORED) {
    state.messages = state.messages.slice(-MAX_STORED);
  }
  state.lastActive = Date.now();
  save();
  return msg;
}

async function send(forcedText) {
  if (busy) return;
  const text = (forcedText !== undefined ? forcedText : el.input.value).trim();
  if (!text) return;

  if (!state.key) {
    openOnboard();
    return;
  }

  el.input.value = '';
  autoGrow();
  addBubble('user', text, Date.now());
  pushMessage('user', text);

  if (navigator.vibrate) navigator.vibrate(8);

  setBusy(true);
  let bubble = null;
  let shown = '';

  try {
    const messages = buildContext();
    const answer = await reply(messages, (partial) => {
      shown = partial;
      if (!bubble) {
        bubble = addBubble('assistant', '', Date.now());
      }
      bubble.textContent = partial;
      const stamp = document.createElement('span');
      stamp.className = 'stamp';
      stamp.textContent = nowLabel();
      bubble.appendChild(stamp);
      scrollDown(false);
    });

    if (!bubble) bubble = addBubble('assistant', '', Date.now());
    bubble.textContent = answer;
    const stamp = document.createElement('span');
    stamp.className = 'stamp';
    stamp.textContent = nowLabel();
    bubble.appendChild(stamp);

    pushMessage('assistant', answer);
    state.lastActive = Date.now();
    save();

    speak(answer);
    scrollDown(true);
    maybeSummarize();
  } catch (err) {
    const message = err && err.message ? err.message : '本鯨腦袋打結了，再試一次好嗎？';
    if (!bubble) bubble = addBubble('assistant', message, Date.now(), { error: true });
    else {
      bubble.classList.add('error');
      bubble.textContent = message;
    }
    setStatus('連線失敗', false);
    setTimeout(() => setStatus('線上', false), 4000);
  } finally {
    setBusy(false);
    scheduleProactive();
  }
}

async function sendProactive(kind) {
  if (busy || !state.key || !state.proactive) return;
  if (Date.now() - state.lastProactive < PROACTIVE_GAP) return;

  setBusy(true);
  try {
    const messages = buildContext(PROMPTS[kind] || PROMPTS.idle);
    const answer = await reply(messages, (partial) => {
      setStatus('正在想…', true);
      if (partial) setStatus('想跟你說…', true);
    });
    addBubble('assistant', answer, Date.now());
    pushMessage('assistant', answer);
    state.lastProactive = Date.now();
    save();
    speak(answer);
  } catch (err) {
    // 主動訊息失敗就安靜，不要吵主人
  } finally {
    setBusy(false);
    scheduleProactive();
  }
}

/* ---------------- 主動訊息排程 ---------------- */

function scheduleProactive() {
  clearTimeout(proactiveTimer);
  if (!state.proactive || !state.key) return;

  const delay = (4 + Math.random() * 6) * 60 * 1000; // 4～10 分鐘
  proactiveTimer = setTimeout(async () => {
    if (document.hidden || busy) {
      scheduleProactive();
      return;
    }
    const idle = Date.now() - state.lastActive;
    if (idle < 3 * 60 * 1000 || Date.now() - state.lastProactive < PROACTIVE_GAP) {
      scheduleProactive();
      return;
    }
    await sendProactive('idle');
  }, delay);
}

function maybeGreet() {
  if (greetedThisSession || !state.key || !state.proactive) return;
  greetedThisSession = true;

  if (!state.messages.length) {
    setTimeout(() => sendProactive('open'), 1200);
    return;
  }

  const last = state.messages[state.messages.length - 1];
  const away = Date.now() - (last.ts || 0);
  if (away > 2 * 60 * 60 * 1000) {
    setTimeout(() => sendProactive('return'), 1500);
  }
}

/* ---------------- 設定面板 ---------------- */

function openSheet(node) {
  node.hidden = false;
}

function closeSheet(node) {
  node.hidden = true;
}

function openOnboard() {
  el.onboardKey.value = state.key || '';
  openSheet(el.onboard);
  setTimeout(() => el.onboardKey.focus(), 200);
}

function openSettings() {
  el.setKey.value = state.key || '';
  el.setModel.value = state.model || 'auto';
  el.setSpeak.checked = state.speak;
  el.setProactive.checked = state.proactive;
  openSheet(el.settings);
  fillModelOptions();
}

async function saveKey(raw) {
  const key = String(raw || '').trim();
  if (!key) {
    toast('要先有鑰匙本鯨才能講話喔。');
    return false;
  }
  if (!key.startsWith('gsk_')) {
    toast('Groq 的鑰匙通常長得像 gsk_ 開頭，再確認一下？');
  }

  const old = state.key;
  state.key = key;
  setStatus('驗證鑰匙…', true);
  try {
    const ids = await fetchModels();
    modelsLoaded = true;
    state.resolvedModel = '';
    chooseModel(ids);
    state.key = key;
    save();
    setStatus('線上', false);
    return true;
  } catch (err) {
    state.key = old;
    setStatus('鑰匙有問題', false);
    toast(err.message || '鑰匙驗證失敗。');
    return false;
  }
}

/* ---------------- 提示 ---------------- */

let toastTimer = null;
function toast(text) {
  let node = document.getElementById('toast');
  if (!node) {
    node = document.createElement('div');
    node.id = 'toast';
    node.style.cssText =
      'position:fixed;left:50%;bottom:calc(84px + env(safe-area-inset-bottom));transform:translateX(-50%);' +
      'max-width:88vw;padding:10px 16px;border-radius:14px;background:rgba(23,37,58,.97);' +
      'border:1px solid #2b405e;color:#e8eef7;font-size:13px;line-height:1.5;z-index:99;' +
      'box-shadow:0 10px 30px rgba(0,0,0,.4);opacity:0;transition:opacity .2s;pointer-events:none;text-align:center;';
    document.body.appendChild(node);
  }
  node.textContent = text;
  node.style.opacity = '1';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { node.style.opacity = '0'; }, 3200);
}

/* ---------------- 輸入框 ---------------- */

function autoGrow() {
  el.input.style.height = 'auto';
  el.input.style.height = Math.min(el.input.scrollHeight, 120) + 'px';
}

/* ---------------- 事件 ---------------- */

function bind() {
  el.send.addEventListener('click', () => send());

  el.input.addEventListener('input', autoGrow);

  el.input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      send();
    }
  });

  el.mic.addEventListener('click', startListening);

  $('btn-settings').addEventListener('click', openSettings);
  $('btn-close-settings').addEventListener('click', () => closeSheet(el.settings));

  el.settings.addEventListener('click', (event) => {
    if (event.target === el.settings) closeSheet(el.settings);
  });
  el.onboard.addEventListener('click', (event) => {
    if (event.target === el.onboard && state.key) closeSheet(el.onboard);
  });

  $('btn-onboard-save').addEventListener('click', async () => {
    const ok = await saveKey(el.onboardKey.value);
    if (!ok) return;
    closeSheet(el.onboard);
    toast('本鯨醒了，可以開始聊了。');
    greetedThisSession = false;
    maybeGreet();
    scheduleProactive();
  });

  el.onboardKey.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') $('btn-onboard-save').click();
  });

  $('btn-save').addEventListener('click', async () => {
    const typed = el.setKey.value.trim();
    if (typed && typed !== state.key) {
      const ok = await saveKey(typed);
      if (!ok) return;
    }
    state.model = el.setModel.value || 'auto';
    state.resolvedModel = '';
    state.speak = el.setSpeak.checked;
    state.proactive = el.setProactive.checked;
    save();
    closeSheet(el.settings);
    toast('記下來了。');
    if (state.speak) speak('本鯨記下了。');
    scheduleProactive();
  });

  $('btn-clear').addEventListener('click', () => {
    if (!confirm('要把本鯨的記憶全部清掉嗎？清掉就認不得你了喔。')) return;
    state.messages = [];
    state.summary = '';
    state.lastProactive = 0;
    state.lastActive = 0;
    summarizeAt = 0;
    save();
    renderAll();
    closeSheet(el.settings);
    toast('記憶清空了。本鯨現在是一張白紙。');
  });

  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
      state.lastActive = Date.now();
      maybeGreet();
      scheduleProactive();
    }
  });

  window.addEventListener('beforeunload', save);
}

/* ---------------- 啟動 ---------------- */

async function boot() {
  load();
  bind();
  renderAll();

  el.setSpeak.checked = state.speak;
  el.setProactive.checked = state.proactive;

  if ('speechSynthesis' in window) {
    loadVoices();
    window.speechSynthesis.addEventListener('voiceschanged', loadVoices);
  }

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  }

  if (!state.key) {
    setStatus('還沒連上大腦', false);
    openOnboard();
    return;
  }

  setStatus('線上', false);
  fillModelOptions();
  maybeGreet();
  scheduleProactive();

  if (!speechAvailable()) {
    el.mic.style.opacity = '0.45';
    el.mic.title = '這個瀏覽器不支援語音輸入';
  }
}

boot();
