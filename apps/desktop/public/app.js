const chatForm = document.getElementById("chatForm");
const userInput = document.getElementById("userInput");
const chatHistory = document.getElementById("chatHistory");
const chatScroll = document.getElementById("chatScroll");
const avatarMouth = document.getElementById("avatarMouth");
const avatarFace = document.getElementById("avatarFace");
const lipSyncStatus = document.getElementById("lipSyncStatus");
const modelStatus = document.getElementById("modelStatus");
const backendStatus = document.getElementById("backendStatus");
const voiceStatus = document.getElementById("voiceStatus");
const fileProtocolBanner = document.getElementById("fileProtocolBanner");
const sessionLine = document.getElementById("sessionLine");
const modeBadge = document.getElementById("modeBadge");
const healthPill = document.getElementById("healthPill");
const typingRow = document.getElementById("typingRow");
const typingLabel = document.getElementById("typingLabel");
const btnSend = document.getElementById("btnSend");
const btnHealth = document.getElementById("btnHealth");
const btnClear = document.getElementById("btnClear");
const btnSettings = document.getElementById("btnSettings");
const settingsPanel = document.getElementById("settingsPanel");
const apiBaseInput = document.getElementById("apiBaseInput");
const btnSaveApi = document.getElementById("btnSaveApi");
const btnResetApi = document.getElementById("btnResetApi");
const metricModel = document.getElementById("metricModel");
const metricTts = document.getElementById("metricTts");
const metricAudio = document.getElementById("metricAudio");
const themeSelect = document.getElementById("themeSelect");
const localeSelect = document.getElementById("localeSelect");
const voiceSelect = document.getElementById("voiceSelect");
const speedSelect = document.getElementById("speedSelect");
const speedFieldLabel = document.getElementById("speedFieldLabel");
const voiceFilterInput = document.getElementById("voiceFilterInput");
const voiceAgeFilterEl = document.getElementById("voiceAgeFilter");
const faceAgeSegment = document.getElementById("faceAgeSegment");
const voiceSearchLabel = document.getElementById("voiceSearchLabel");
const voiceAgeFilterLabel = document.getElementById("voiceAgeFilterLabel");
const faceAgeLabel = document.getElementById("faceAgeLabel");
const settingsForm = document.getElementById("settingsForm");
const settingsFieldsLlm = document.getElementById("settingsFieldsLlm");
const settingsFieldsPiper = document.getElementById("settingsFieldsPiper");
const settingsFieldsRag = document.getElementById("settingsFieldsRag");
const settingsFieldsSafety = document.getElementById("settingsFieldsSafety");
const settingsPathsList = document.getElementById("settingsPathsList");
const settingsPathsHint = document.getElementById("settingsPathsHint");
const settingsNoteLlm = document.getElementById("settingsNoteLlm");
const settingsNotePiper = document.getElementById("settingsNotePiper");
const settingsNoteRag = document.getElementById("settingsNoteRag");
const settingsNotePaths = document.getElementById("settingsNotePaths");
const settingsStatus = document.getElementById("settingsStatus");
const btnSaveSettings = document.getElementById("btnSaveSettings");
const btnReloadSettings = document.getElementById("btnReloadSettings");

const SETTINGS_GROUP_EL = {
  llm: settingsFieldsLlm,
  piper: settingsFieldsPiper,
  rag: settingsFieldsRag,
  safety: settingsFieldsSafety,
};

const PATH_LABELS = {
  appDataDir: "User data root",
  envFile: "Settings file (.env)",
  piperModelsDir: "Piper voice models",
  audioDir: "Generated audio cache",
  ragIndexDir: "RAG vector index",
  faqPath: "FAQ dataset (bundled)",
  voiceAvatarMap: "Voice → avatar map",
  bundledMode: "Desktop bundle mode",
};

const STORAGE_API = "smartAvatarApiBase";
const STORAGE_THEME = "smartAvatarTheme";
const STORAGE_LOCALE = "smartAvatarLocale";
const STORAGE_VOICE_FA = "smartAvatarVoiceFa";
const STORAGE_VOICE_EN = "smartAvatarVoiceEn";
const STORAGE_SPEAKING_SPEED = "smartAvatarSpeakingSpeed";
const STORAGE_VOICE_FILTER = "smartAvatarVoiceFilter";
const STORAGE_VOICE_AGE_FILTER = "smartAvatarVoiceAgeFilter";
const STORAGE_FACE_AGE = "smartAvatarFaceAge";

const THEMES = [
  { id: "blue", label: "Blue" },
  { id: "black", label: "Black" },
  { id: "white", label: "White" },
  { id: "red", label: "Red" },
  { id: "green", label: "Green" },
  { id: "yellow", label: "Yellow" },
  { id: "purple", label: "Purple" },
];

const mouthTimers = [];
let allVoices = [];
let voiceAgeFilterBucket = "young";
let faceAgeBucket = "young";
let voiceFilterDebounceTimer = 0;

const sessionId = crypto.randomUUID();
if (sessionLine) {
  sessionLine.textContent = `Session ${sessionId.slice(0, 8)}…`;
}

const STATIC_UI_PORTS = new Set(["5173", "5500", "4173", "3000"]);

let injectedDesktopApiBase = null;

function isTauriDesktopShell() {
  return window.__PERSONA_DESKTOP__ === true;
}

const desktopBackendReady =
  isTauriDesktopShell() && window.__personaDesktopReady
    ? window.__personaDesktopReady
    : Promise.resolve();

function isLocalHttpUi() {
  const { protocol, hostname } = window.location;
  return (
    (protocol === "http:" || protocol === "https:") &&
    (hostname === "127.0.0.1" || hostname === "localhost")
  );
}

function isBackendServedUi() {
  if (!isLocalHttpUi()) {
    return false;
  }
  const port = window.location.port;
  if (!port) {
    return true;
  }
  return !STATIC_UI_PORTS.has(port);
}

function defaultApiBaseSuggestion() {
  if (isBackendServedUi()) {
    return window.location.origin;
  }
  return "http://127.0.0.1:8000";
}

function readStoredApiBase() {
  const raw = window.localStorage.getItem(STORAGE_API);
  if (raw === null) {
    return null;
  }
  const trimmed = raw.trim();
  return trimmed === "" ? "" : trimmed.replace(/\/$/, "");
}

function resolveApiBase() {
  if (window.__PERSONA_API_BASE__) {
    return String(window.__PERSONA_API_BASE__).replace(/\/$/, "");
  }
  if (injectedDesktopApiBase) {
    return injectedDesktopApiBase;
  }

  const params = new URLSearchParams(window.location.search);
  if (params.has("api")) {
    const v = params.get("api").trim();
    return v.replace(/\/$/, "");
  }

  // Backend-served UI (browser at sidecar port): API is same origin.
  if (isBackendServedUi()) {
    return window.location.origin;
  }

  const stored = readStoredApiBase();
  if (stored !== null) {
    return stored;
  }

  return defaultApiBaseSuggestion();
}

const FETCH_TIMEOUT_MS = 8000;

async function fetchWithTimeout(url, options = {}) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    window.clearTimeout(timer);
  }
}

let API_BASE = resolveApiBase();

function apiUrl(path) {
  const p = path.startsWith("/") ? path : `/${path}`;
  if (!API_BASE) {
    return p;
  }
  return `${API_BASE.replace(/\/$/, "")}${p}`;
}

function syncApiInput() {
  if (!apiBaseInput) {
    return;
  }
  apiBaseInput.value = API_BASE || "";
}

function setSettingsStatus(text, isError = false) {
  if (!settingsStatus) {
    return;
  }
  settingsStatus.textContent = text || "";
  settingsStatus.style.color = isError ? "var(--danger)" : "";
}

function activateSettingsTab(tabId) {
  document.querySelectorAll(".settings-tab").forEach((btn) => {
    const active = btn.getAttribute("data-settings-tab") === tabId;
    btn.classList.toggle("is-active", active);
    btn.setAttribute("aria-selected", String(active));
  });
  document.querySelectorAll(".settings-section").forEach((panel) => {
    const active = panel.getAttribute("data-settings-panel") === tabId;
    panel.classList.toggle("is-active", active);
    panel.hidden = !active;
  });
}

function createSettingsField(spec) {
  const wrap = document.createElement("label");
  wrap.className = "field";
  wrap.dataset.settingKey = spec.key;

  const label = document.createElement("span");
  label.textContent = spec.label;
  wrap.appendChild(label);

  let input;
  if (spec.type === "bool") {
    input = document.createElement("select");
    ["true", "false"].forEach((v) => {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v === "true" ? "Yes" : "No";
      input.appendChild(opt);
    });
    input.value = String(spec.value || "false").toLowerCase() === "true" ? "true" : "false";
  } else if (spec.type === "secret") {
    input = document.createElement("input");
    input.type = "password";
    input.autocomplete = "off";
    input.placeholder = spec.masked ? `Saved (${spec.masked}) — leave blank to keep` : "Enter key";
    input.value = "";
  } else {
    input = document.createElement("input");
    input.type = spec.type === "number" ? "number" : "text";
    input.value = spec.value ?? "";
    if (spec.type === "number") {
      input.step = "any";
    }
  }
  input.id = `setting-${spec.key}`;
  input.name = spec.key;
  wrap.appendChild(input);
  return wrap;
}

function renderSettingsSnapshot(snapshot) {
  if (!snapshot) {
    return;
  }
  const byGroup = { llm: [], piper: [], rag: [], safety: [] };
  (snapshot.fields || []).forEach((spec) => {
    if (byGroup[spec.group]) {
      byGroup[spec.group].push(spec);
    }
  });
  Object.entries(SETTINGS_GROUP_EL).forEach(([group, container]) => {
    if (!container) {
      return;
    }
    container.innerHTML = "";
    byGroup[group].forEach((spec) => {
      container.appendChild(createSettingsField(spec));
    });
  });

  if (settingsNoteLlm && snapshot.notes) {
    settingsNoteLlm.textContent = snapshot.notes.llmModels || "";
  }
  if (settingsNotePiper && snapshot.notes) {
    settingsNotePiper.textContent = snapshot.notes.piperVoices || "";
  }
  if (settingsNoteRag && snapshot.notes) {
    settingsNoteRag.textContent = snapshot.notes.ragIndex || "";
  }
  if (settingsNotePaths && snapshot.notes) {
    settingsNotePaths.textContent = snapshot.notes.restart || "";
  }

  if (settingsPathsList && snapshot.paths) {
    settingsPathsList.innerHTML = "";
    Object.entries(snapshot.paths).forEach(([key, value]) => {
      const row = document.createElement("div");
      const dt = document.createElement("dt");
      dt.textContent = PATH_LABELS[key] || key;
      const dd = document.createElement("dd");
      if (key === "bundledMode") {
        dd.textContent = value ? "Desktop / PyInstaller sidecar" : "Development";
      } else {
        dd.textContent = String(value);
      }
      row.append(dt, dd);
      settingsPathsList.appendChild(row);
    });
  }

  if (settingsPathsHint && snapshot.paths?.envFile) {
    settingsPathsHint.textContent = `Settings saved to ${snapshot.paths.envFile}`;
  }
}

function collectSettingsPayload() {
  const values = {};
  document.querySelectorAll("[data-setting-key]").forEach((wrap) => {
    const key = wrap.dataset.settingKey;
    const input = wrap.querySelector("input, select");
    if (!input || !key) {
      return;
    }
    if (input.type === "password" && !input.value.trim()) {
      return;
    }
    values[key] = input.value.trim();
  });
  return values;
}

async function loadSettingsFromBackend() {
  setSettingsStatus("Loading…");
  try {
    const response = await fetchWithTimeout(apiUrl("/settings"));
    if (!response.ok) {
      throw new Error(String(response.status));
    }
    const data = await response.json();
    renderSettingsSnapshot(data);
    setSettingsStatus("");
    return data;
  } catch (error) {
    setSettingsStatus(`Could not load settings (${error.message})`, true);
    return null;
  }
}

async function saveSettingsToBackend() {
  setSettingsStatus("Saving…");
  try {
    const response = await fetchWithTimeout(apiUrl("/settings"), {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ values: collectSettingsPayload() }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || String(response.status));
    }
    const data = await response.json();
    renderSettingsSnapshot(data);
    setSettingsStatus("Saved. Refreshing voices and status…");
    await fetchVoiceConfig();
    await checkBackend();
    setSettingsStatus("Saved.");
  } catch (error) {
    setSettingsStatus(`Save failed: ${error.message}`, true);
  }
}

document.querySelectorAll(".settings-tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    activateSettingsTab(btn.getAttribute("data-settings-tab") || "llm");
  });
});

settingsForm?.addEventListener("submit", (e) => {
  e.preventDefault();
  saveSettingsToBackend();
});

btnReloadSettings?.addEventListener("click", () => {
  loadSettingsFromBackend();
});

function getLocale() {
  const v = localeSelect?.value;
  return v === "en" ? "en" : "fa";
}

function voiceStorageKey() {
  return getLocale() === "en" ? STORAGE_VOICE_EN : STORAGE_VOICE_FA;
}

function scrollChatToBottom() {
  const el = chatScroll || chatHistory;
  if (el) {
    el.scrollTop = el.scrollHeight;
  }
}

function initThemeSelect() {
  if (!themeSelect) {
    return;
  }
  themeSelect.innerHTML = "";
  THEMES.forEach((t) => {
    const opt = document.createElement("option");
    opt.value = t.id;
    opt.textContent = t.label;
    themeSelect.appendChild(opt);
  });
  const stored = window.localStorage.getItem(STORAGE_THEME);
  const pick = stored && THEMES.some((x) => x.id === stored) ? stored : "blue";
  themeSelect.value = pick;
  document.documentElement.setAttribute("data-theme", pick);
}

function applyTheme(themeId) {
  const id = THEMES.some((t) => t.id === themeId) ? themeId : "blue";
  document.documentElement.setAttribute("data-theme", id);
  window.localStorage.setItem(STORAGE_THEME, id);
  if (themeSelect) {
    themeSelect.value = id;
  }
}

function initLocaleSelect() {
  if (!localeSelect) {
    return;
  }
  const stored = window.localStorage.getItem(STORAGE_LOCALE);
  localeSelect.value = stored === "en" ? "en" : "fa";
}

function applyChatChrome() {
  const loc = getLocale();
  document.documentElement.lang = loc === "fa" ? "fa" : "en";
  if (chatScroll) {
    chatScroll.classList.toggle("chat-rtl", loc === "fa");
  }
  if (typingLabel) {
    typingLabel.textContent =
      loc === "fa" ? "دستیار در حال فکر کردن…" : "Assistant is thinking…";
  }
  if (userInput) {
    userInput.placeholder =
      loc === "fa"
        ? "پیام را بنویسید… (Enter ارسال، Shift+Enter خط جدید)"
        : "Type your message… (Enter to send, Shift+Enter for newline)";
  }
  if (speedFieldLabel) {
    speedFieldLabel.textContent =
      loc === "fa" ? "سرعت گفتار" : "Speech speed";
  }
  if (speedSelect) {
    const optLow = speedSelect.querySelector("option[value='low']");
    const optMed = speedSelect.querySelector("option[value='medium']");
    const optHi = speedSelect.querySelector("option[value='high']");
    if (optLow && optMed && optHi) {
      if (loc === "fa") {
        optLow.textContent = "آرام";
        optMed.textContent = "متوسط";
        optHi.textContent = "تند";
      } else {
        optLow.textContent = "Low";
        optMed.textContent = "Medium";
        optHi.textContent = "High";
      }
    }
  }
  const ageL =
    loc === "fa"
      ? { child: "کودک", young: "جوان", old: "مسن" }
      : { child: "Child", young: "Young", old: "Old" };
  if (voiceSearchLabel) {
    voiceSearchLabel.textContent = loc === "fa" ? "جستجوی صدا" : "Search voices";
  }
  if (voiceAgeFilterLabel) {
    voiceAgeFilterLabel.textContent = loc === "fa" ? "گروه سنی صدا" : "Voice age";
  }
  if (faceAgeLabel) {
    faceAgeLabel.textContent = loc === "fa" ? "سن چهره" : "Portrait age";
  }
  if (voiceFilterInput) {
    voiceFilterInput.placeholder = loc === "fa" ? "فیلتر نام…" : "Filter by name…";
  }
  voiceAgeFilterEl?.querySelectorAll("[data-voice-age]").forEach((btn) => {
    const k = btn.getAttribute("data-voice-age");
    if (k && ageL[k]) {
      btn.textContent = ageL[k];
    }
  });
  faceAgeSegment?.querySelectorAll("[data-face-age]").forEach((btn) => {
    const k = btn.getAttribute("data-face-age");
    if (k && ageL[k]) {
      btn.textContent = ageL[k];
    }
  });
}

function initSpeedSelect() {
  if (!speedSelect) {
    return;
  }
  const raw = window.localStorage.getItem(STORAGE_SPEAKING_SPEED);
  const ok = raw === "low" || raw === "medium" || raw === "high";
  speedSelect.value = ok ? raw : "medium";
  if (!ok) {
    window.localStorage.setItem(STORAGE_SPEAKING_SPEED, "medium");
  }
}

function getSpeakingSpeed() {
  const v = speedSelect?.value;
  if (v === "low" || v === "high") {
    return v;
  }
  return "medium";
}

function voicesForLocale(locale) {
  return allVoices.filter((v) => v.locale === locale);
}

function normalizedVoiceAge(meta) {
  const raw = String(meta?.voiceAge ?? meta?.voice_age ?? "young")
    .trim()
    .toLowerCase();
  if (raw === "child" || raw === "old") {
    return raw;
  }
  return "young";
}

function voiceMatchesAgeFilter(meta, bucket) {
  const va = normalizedVoiceAge(meta);
  if (bucket === "child") {
    return va === "child";
  }
  if (bucket === "old") {
    return va === "old";
  }
  return va === "young";
}

function voicesFilteredForUi(locale) {
  let list = voicesForLocale(locale);
  const q = (voiceFilterInput?.value || "").trim().toLowerCase();
  if (q) {
    list = list.filter((v) => {
      const id = String(v.id || "").toLowerCase();
      const label = String(v.label || "").toLowerCase();
      return id.includes(q) || label.includes(q);
    });
  }
  return list.filter((v) => voiceMatchesAgeFilter(v, voiceAgeFilterBucket));
}

function readVoiceAgeFilterBucket() {
  const raw = window.localStorage.getItem(STORAGE_VOICE_AGE_FILTER);
  return raw === "child" || raw === "young" || raw === "old" ? raw : "young";
}

function readFaceAgeBucket() {
  const raw = window.localStorage.getItem(STORAGE_FACE_AGE);
  return raw === "child" || raw === "young" || raw === "old" ? raw : "young";
}

function syncVoiceAgeFilterButtons() {
  if (!voiceAgeFilterEl) {
    return;
  }
  voiceAgeFilterEl.querySelectorAll(".seg-btn").forEach((btn) => {
    const ok = btn.getAttribute("data-voice-age") === voiceAgeFilterBucket;
    btn.classList.toggle("is-selected", ok);
  });
}

function syncFaceAgeButtons() {
  if (!faceAgeSegment) {
    return;
  }
  faceAgeSegment.querySelectorAll(".seg-btn").forEach((btn) => {
    const ok = btn.getAttribute("data-face-age") === faceAgeBucket;
    btn.classList.toggle("is-selected", ok);
  });
}

function initVoiceAndFaceChrome() {
  voiceAgeFilterBucket = readVoiceAgeFilterBucket();
  faceAgeBucket = readFaceAgeBucket();
  if (voiceFilterInput) {
    voiceFilterInput.value = window.localStorage.getItem(STORAGE_VOICE_FILTER) || "";
  }
  syncVoiceAgeFilterButtons();
  syncFaceAgeButtons();
  syncAvatarFaceDisplay();
}

function syncAvatarFaceDisplay() {
  if (!avatarFace) {
    return;
  }
  avatarFace.dataset.age = faceAgeBucket;
}

function populateVoiceSelect() {
  if (!voiceSelect) {
    return;
  }
  const locale = getLocale();
  const list = voicesFilteredForUi(locale);
  const stored = window.localStorage.getItem(voiceStorageKey());
  const prev = voiceSelect.value;
  voiceSelect.innerHTML = "";
  if (list.length === 0) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent =
      locale === "fa"
        ? "(صدا با این فیلتر یافت نشد)"
        : "(No voice matches this filter)";
    voiceSelect.appendChild(opt);
    voiceSelect.disabled = true;
    voiceSelect.setAttribute("data-empty-voices", "1");
    return;
  }
  voiceSelect.disabled = false;
  voiceSelect.removeAttribute("data-empty-voices");
  list.forEach((v) => {
    const opt = document.createElement("option");
    opt.value = v.id;
    opt.textContent = v.label || v.id;
    voiceSelect.appendChild(opt);
  });
  let preferred =
    stored && list.some((x) => x.id === stored)
      ? stored
      : prev && list.some((x) => x.id === prev)
        ? prev
        : list[0].id;
  voiceSelect.value = preferred;
  window.localStorage.setItem(voiceStorageKey(), preferred);
}

function getSelectedVoiceId() {
  if (!voiceSelect) {
    return null;
  }
  if (voiceSelect.getAttribute("data-empty-voices") === "1") {
    return null;
  }
  const v = voiceSelect.value.trim();
  return v || null;
}

async function fetchVoiceConfig() {
  try {
    const response = await fetchWithTimeout(apiUrl("/config"));
    if (!response.ok) {
      throw new Error(String(response.status));
    }
    const data = await response.json();
    allVoices = Array.isArray(data.voices) ? data.voices : [];
  } catch (_e) {
    allVoices = [];
  }
  populateVoiceSelect();
}

function formatClock() {
  const d = new Date();
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

function setHealthPill(ok, label) {
  if (!healthPill) {
    return;
  }
  healthPill.textContent = label;
  healthPill.classList.remove("pill-ok", "pill-warn", "pill-muted");
  healthPill.classList.add(ok ? "pill-ok" : "pill-warn");
}

function resetMetrics() {
  if (metricModel) {
    metricModel.textContent = "—";
  }
  if (metricTts) {
    metricTts.textContent = "—";
  }
  if (metricAudio) {
    metricAudio.textContent = "—";
  }
}

function applyMetrics(meta) {
  if (!meta || !meta.latencyMs) {
    return;
  }
  const lat = meta.latencyMs;
  if (metricModel) {
    metricModel.textContent = `${lat.model ?? "—"} ms`;
  }
  if (metricTts) {
    metricTts.textContent = `${lat.tts ?? "—"} ms`;
  }
  if (metricAudio && meta.durationMs != null) {
    metricAudio.textContent = `${meta.durationMs} ms`;
  }
}

function roleLabel(role) {
  const loc = getLocale();
  if (role === "user") {
    return loc === "fa" ? "شما" : "You";
  }
  if (role === "error") {
    return loc === "fa" ? "خطا" : "Error";
  }
  return loc === "fa" ? "دستیار" : "Assistant";
}

function addMessage(text, role, options = {}) {
  const wrap = document.createElement("div");
  wrap.className = `msg msg-${role}`;
  const meta = document.createElement("div");
  meta.className = "msg-meta";
  meta.textContent = `${roleLabel(role)} · ${formatClock()}`;
  const body = document.createElement("div");
  body.className = "msg-body";
  body.textContent = text;
  if (options.error) {
    wrap.classList.add("msg-error");
  }
  wrap.append(meta, body);
  chatHistory.appendChild(wrap);
  scrollChatToBottom();
}

function seedWelcome() {
  const loc = getLocale();
  const text =
    loc === "fa"
      ? "سلام. آماده‌ام تا با آرامش و به‌صورت مرحله‌به‌مرحله همراهت باشم."
      : "Hello. I am here to support you calmly, one step at a time.";
  addMessage(text, "assistant");
}

function setTyping(visible) {
  if (!typingRow) {
    return;
  }
  typingRow.classList.toggle("hidden", !visible);
  typingRow.setAttribute("aria-hidden", visible ? "false" : "true");
  if (visible) {
    scrollChatToBottom();
  }
}

function setBusy(busy) {
  if (btnSend) {
    btnSend.disabled = busy;
  }
  if (userInput) {
    userInput.disabled = busy;
  }
  if (speedSelect) {
    speedSelect.disabled = busy;
  }
  if (voiceSelect) {
    const empty = voiceSelect.getAttribute("data-empty-voices") === "1";
    voiceSelect.disabled = empty;
  }
  if (voiceFilterInput) {
    voiceFilterInput.disabled = busy;
  }
  voiceAgeFilterEl?.querySelectorAll(".seg-btn").forEach((b) => {
    b.disabled = busy;
  });
  faceAgeSegment?.querySelectorAll(".seg-btn").forEach((b) => {
    b.disabled = busy;
  });
}

function mouthScaleForFace() {
  if (!avatarFace) {
    return 1;
  }
  const a = avatarFace.getAttribute("data-age") || "young";
  if (a === "child") {
    return 0.88;
  }
  if (a === "old") {
    return 0.92;
  }
  return 1;
}

function resetMouth() {
  const sc = mouthScaleForFace();
  avatarMouth.style.width = `${Math.round(44 * sc)}px`;
  avatarMouth.style.height = `${Math.round(16 * sc)}px`;
  if (avatarFace) {
    avatarFace.classList.remove("speaking");
  }
}

function clearLipSyncTimers() {
  while (mouthTimers.length) {
    clearTimeout(mouthTimers.pop());
  }
}

function applyVisemeFrame(frame) {
  const weight = Number(frame.weight || 0.7);
  const widthMap = {
    viseme_closed: 42,
    viseme_open: 48,
    viseme_fv: 46,
    viseme_tight: 40,
  };
  const heightMap = {
    viseme_closed: 13,
    viseme_open: 28,
    viseme_fv: 20,
    viseme_tight: 17,
  };
  const baseWidth = widthMap[frame.viseme] || 44;
  const baseHeight = heightMap[frame.viseme] || 16;
  const sc = mouthScaleForFace();
  avatarMouth.style.width = `${Math.round((baseWidth + weight * 6) * sc)}px`;
  avatarMouth.style.height = `${Math.round((baseHeight + weight * 7) * sc)}px`;
}

function runVisemeTimeline(visemes) {
  clearLipSyncTimers();
  if (!Array.isArray(visemes) || visemes.length === 0) {
    resetMouth();
    lipSyncStatus.textContent = "Ready";
    return;
  }

  if (avatarFace) {
    avatarFace.classList.add("speaking");
  }
  lipSyncStatus.textContent = "Animating";
  let lastEnd = 0;
  visemes.forEach((frame) => {
    const start = Number(frame.startMs || 0);
    const end = Number(frame.endMs || start + 80);
    lastEnd = Math.max(lastEnd, end);
    mouthTimers.push(setTimeout(() => applyVisemeFrame(frame), start));
  });

  mouthTimers.push(
    setTimeout(() => {
      resetMouth();
      lipSyncStatus.textContent = "Ready";
    }, lastEnd + 30),
  );
}

function getAudioUrl(audioPath, cacheBust) {
  if (!audioPath) {
    return "";
  }
  if (audioPath.startsWith("http://") || audioPath.startsWith("https://")) {
    return audioPath;
  }
  if (audioPath.startsWith("/")) {
    const base = apiUrl(audioPath);
    if (cacheBust) {
      const sep = base.includes("?") ? "&" : "?";
      return `${base}${sep}v=${encodeURIComponent(String(cacheBust))}`;
    }
    return base;
  }
  return "";
}

function playAssistantAudio(audioPath, cacheBust) {
  const url = getAudioUrl(audioPath, cacheBust);
  if (!url) {
    return null;
  }
  const audio = new Audio(url);
  audio.play().catch(() => {
    backendStatus.textContent =
      getLocale() === "fa"
        ? "پخش صدا مسدود است — یک‌بار صفحه را بزنید یا پخش خودکار را اجازه دهید."
        : "Audio playback blocked — click the page or allow autoplay.";
  });
  return audio;
}

async function parseJsonSafe(response) {
  const text = await response.text();
  if (!text) {
    return {};
  }
  try {
    return JSON.parse(text);
  } catch (_e) {
    return { _raw: text };
  }
}

async function checkBackend() {
  if (voiceStatus) {
    voiceStatus.textContent = "…";
  }
  setHealthPill(false, "Checking");
  if (backendStatus) {
    backendStatus.textContent = "Checking…";
  }
  if (modeBadge) {
    modeBadge.textContent = "…";
  }

  try {
    const response = await fetchWithTimeout(apiUrl("/health"));
    if (!response.ok) {
      throw new Error(`Health HTTP ${response.status}`);
    }
    const data = await parseJsonSafe(response);
    const modelLabel = data.modelName ? String(data.modelName) : "model";
    modelStatus.textContent = `OK · ${modelLabel}`;
    const ttsOk = Boolean(data.ttsConfigured);
    const tts = data.tts || {};
    const nVoices = typeof tts.voiceCount === "number" ? tts.voiceCount : 0;
    if (voiceStatus) {
      if (ttsOk) {
        const vid = getSelectedVoiceId();
        const vmeta = allVoices.find((x) => x.id === vid);
        voiceStatus.textContent = vmeta ? vmeta.label : "Piper ready";
      } else if (!tts.piperExecutableOk) {
        voiceStatus.textContent = "Set PIPER_BIN → piper.exe";
      } else if (nVoices === 0) {
        voiceStatus.textContent = "No .onnx voices in folder";
      } else {
        voiceStatus.textContent = "TTS incomplete";
      }
    }
    backendStatus.textContent = ttsOk
      ? `Connected · ${API_BASE || window.location.origin}`
      : `API online · Piper: executable + voice .onnx + .onnx.json (${nVoices} listed)`;
    setHealthPill(true, "Online");
    if (modeBadge) {
      modeBadge.textContent = ttsOk ? "Live" : "Partial";
    }
  } catch (error) {
    modelStatus.textContent = "Unreachable";
    if (voiceStatus) {
      voiceStatus.textContent = "—";
    }
    const timedOut = error instanceof Error && error.name === "AbortError";
    const target = API_BASE || window.location.origin || "(same origin)";
    backendStatus.textContent = timedOut
      ? `Local backend timed out (${target}). Not an internet issue — start Ollama/Piper or rebuild the desktop sidecar.`
      : `No backend at ${target}. Settings → Connection: clear API URL for desktop app.`;
    setHealthPill(false, "Offline");
    if (modeBadge) {
      modeBadge.textContent = "Offline";
    }
  }
}

async function requestAssistant(userText, voiceIdOverride) {
  const voiceId =
    voiceIdOverride !== undefined ? voiceIdOverride : getSelectedVoiceId();
  const response = await fetch(apiUrl("/chat/respond"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      sessionId,
      userText,
      emotionHint: null,
      locale: getLocale(),
      voiceId,
      speakingSpeed: getSpeakingSpeed(),
      avatarFaceAge: faceAgeBucket,
    }),
  });

  const data = await parseJsonSafe(response);

  if (!response.ok) {
    let detail = data.detail;
    if (Array.isArray(detail)) {
      detail = detail.map((x) => x.msg || JSON.stringify(x)).join("; ");
    }
    if (detail == null && data._raw) {
      detail = data._raw.slice(0, 400);
    }
    throw new Error(detail || `Request failed (${response.status})`);
  }

  return data;
}

async function bootstrap() {
  initThemeSelect();
  initLocaleSelect();
  initSpeedSelect();
  initVoiceAndFaceChrome();
  applyChatChrome();

  if (isTauriDesktopShell()) {
    if (backendStatus) {
      backendStatus.textContent = "Starting local backend…";
    }
    setHealthPill(false, "Starting");
    try {
      await desktopBackendReady;
      API_BASE = resolveApiBase();
      syncApiInput();
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      if (backendStatus) {
        backendStatus.textContent = msg;
      }
      setHealthPill(false, "Offline");
      if (modeBadge) {
        modeBadge.textContent = "Offline";
      }
      return;
    }
  }

  await fetchVoiceConfig();
  await checkBackend();
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = userInput.value.trim();
  if (!text || btnSend?.disabled) {
    return;
  }

  addMessage(text, "user");
  userInput.value = "";
  const voiceIdForRequest = getSelectedVoiceId();
  setBusy(true);
  setTyping(true);
  lipSyncStatus.textContent = "Waiting";

  try {
    const payload = await requestAssistant(text, voiceIdForRequest);
    setTyping(false);
    addMessage(payload.assistantText, "assistant");
    applyMetrics(payload.meta || {});
    const audio = playAssistantAudio(
      payload.audioPath,
      `${Date.now()}-${payload.meta?.voiceId ?? ""}`,
    );
    if (audio) {
      audio.addEventListener(
        "play",
        () => runVisemeTimeline(payload.visemes || []),
        { once: true },
      );
    } else {
      runVisemeTimeline(payload.visemes || []);
    }
  } catch (error) {
    setTyping(false);
    const msg = error instanceof Error ? error.message : String(error);
    addMessage(msg, "assistant", { error: true });
    resetMetrics();
    runVisemeTimeline([
      { startMs: 0, endMs: 180, viseme: "viseme_open", weight: 0.75 },
      { startMs: 181, endMs: 360, viseme: "viseme_tight", weight: 0.7 },
      { startMs: 361, endMs: 600, viseme: "viseme_closed", weight: 0.8 },
    ]);
    lipSyncStatus.textContent = "Error";
  } finally {
    setBusy(false);
  }
});

userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    chatForm.requestSubmit();
  }
});

btnHealth?.addEventListener("click", async () => {
  await fetchVoiceConfig();
  checkBackend();
});

btnClear?.addEventListener("click", () => {
  chatHistory.innerHTML = "";
  seedWelcome();
  resetMetrics();
  resetMouth();
  lipSyncStatus.textContent = "Ready";
});

btnSettings?.addEventListener("click", async () => {
  settingsPanel.classList.toggle("hidden");
  const expanded = !settingsPanel.classList.contains("hidden");
  btnSettings.setAttribute("aria-expanded", String(expanded));
  if (expanded) {
    syncApiInput();
    activateSettingsTab("llm");
    await loadSettingsFromBackend();
  }
});

btnSaveApi?.addEventListener("click", async () => {
  const raw = apiBaseInput.value.trim();
  window.localStorage.setItem(STORAGE_API, raw);
  API_BASE = raw.replace(/\/$/, "");
  syncApiInput();
  await fetchVoiceConfig();
  checkBackend();
});

btnResetApi?.addEventListener("click", async () => {
  window.localStorage.removeItem(STORAGE_API);
  API_BASE = resolveApiBase();
  syncApiInput();
  await fetchVoiceConfig();
  await checkBackend();
});

themeSelect?.addEventListener("change", () => {
  applyTheme(themeSelect.value);
});

localeSelect?.addEventListener("change", () => {
  window.localStorage.setItem(STORAGE_LOCALE, getLocale());
  applyChatChrome();
  populateVoiceSelect();
  chatHistory.innerHTML = "";
  seedWelcome();
  resetMetrics();
  checkBackend();
});

voiceSelect?.addEventListener("change", () => {
  const v = getSelectedVoiceId();
  if (v) {
    window.localStorage.setItem(voiceStorageKey(), v);
  }
  resetMouth();
  checkBackend();
});

speedSelect?.addEventListener("change", () => {
  window.localStorage.setItem(STORAGE_SPEAKING_SPEED, getSpeakingSpeed());
});

voiceFilterInput?.addEventListener("input", () => {
  window.localStorage.setItem(STORAGE_VOICE_FILTER, voiceFilterInput.value);
  window.clearTimeout(voiceFilterDebounceTimer);
  voiceFilterDebounceTimer = window.setTimeout(() => {
    populateVoiceSelect();
    checkBackend();
  }, 200);
});

voiceAgeFilterEl?.addEventListener("click", (e) => {
  const t = e.target;
  const btn =
    t instanceof Element ? t.closest("button[data-voice-age]") : null;
  if (!btn) {
    return;
  }
  const next = btn.getAttribute("data-voice-age");
  if (next !== "child" && next !== "young" && next !== "old") {
    return;
  }
  voiceAgeFilterBucket = next;
  window.localStorage.setItem(STORAGE_VOICE_AGE_FILTER, next);
  syncVoiceAgeFilterButtons();
  populateVoiceSelect();
  checkBackend();
});

faceAgeSegment?.addEventListener("click", (e) => {
  const t = e.target;
  const btn = t instanceof Element ? t.closest("button[data-face-age]") : null;
  if (!btn) {
    return;
  }
  const next = btn.getAttribute("data-face-age");
  if (next !== "child" && next !== "young" && next !== "old") {
    return;
  }
  faceAgeBucket = next;
  window.localStorage.setItem(STORAGE_FACE_AGE, next);
  syncFaceAgeButtons();
  syncAvatarFaceDisplay();
  resetMouth();
});

if (window.location.protocol === "file:" && fileProtocolBanner) {
  fileProtocolBanner.classList.remove("hidden");
}

syncApiInput();
bootstrap().then(() => {
  seedWelcome();
});
