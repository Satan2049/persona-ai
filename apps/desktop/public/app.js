const chatForm = document.getElementById("chatForm");
const userInput = document.getElementById("userInput");
const chatHistory = document.getElementById("chatHistory");
const chatScroll = document.getElementById("chatScroll");
const avatarViewport = document.getElementById("avatarViewport");
const avatarGenderSegment = document.getElementById("avatarGenderSegment");
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
const btnMic = document.getElementById("btnMic");
const btnHealth = document.getElementById("btnHealth");
const btnClear = document.getElementById("btnClear");
const metricModel = document.getElementById("metricModel");
const metricTts = document.getElementById("metricTts");
const metricAudio = document.getElementById("metricAudio");
const themeSelect = document.getElementById("themeSelect");
const localeSelect = document.getElementById("localeSelect");
const genderSelect = document.getElementById("genderSelect");
const voiceSelect = document.getElementById("voiceSelect");
const speedSelect = document.getElementById("speedSelect");
const speedFieldLabel = document.getElementById("speedFieldLabel");
const voiceThemeSelect = document.getElementById("voiceThemeSelect");
const voiceLocaleSelect = document.getElementById("voiceLocaleSelect");
const voiceGenderSelect = document.getElementById("voiceGenderSelect");
const voiceVoiceSelect = document.getElementById("voiceVoiceSelect");
const voiceSpeedSelect = document.getElementById("voiceSpeedSelect");
const voiceAvatarGenderSelect = document.getElementById("voiceAvatarGenderSelect");
const chatAvatarStage = document.getElementById("chatAvatarStage");
const btnModeSwitch = document.getElementById("btnModeSwitch");
const btnVoiceModeSwitch = document.getElementById("btnVoiceModeSwitch");
const btnCloseVoice = document.getElementById("btnCloseVoice");
const btnVoiceMain = document.getElementById("btnVoiceMain");
const btnVoiceInterrupt = document.getElementById("btnVoiceInterrupt");

const STORAGE_API = "smartAvatarApiBase";
const STORAGE_THEME = "smartAvatarTheme";
const STORAGE_LOCALE = "smartAvatarLocale";
const STORAGE_VOICE_FA = "smartAvatarVoiceFa";
const STORAGE_VOICE_EN = "smartAvatarVoiceEn";
const STORAGE_SPEAKING_SPEED = "smartAvatarSpeakingSpeed";
const STORAGE_VOICE_GENDER = "smartAvatarVoiceGender";
const STORAGE_MODEL_GENDER = "smartAvatarModelGender";
const STORAGE_VOICE_AUTO_LISTEN = "smartAvatarVoiceAutoListen";

const setupHelp = document.getElementById("setupHelp");
const setupHelpBody = document.getElementById("setupHelpBody");

const THEMES = [
  { id: "blue" },
  { id: "black" },
  { id: "white" },
  { id: "red" },
  { id: "green" },
  { id: "yellow" },
  { id: "purple" },
];

function t(key) {
  if (window.PersonaI18n) {
    return window.PersonaI18n.t(key, getLocale());
  }
  return key;
}

const mouthTimers = [];
let lipSyncRafId = null;
let allVoices = [];
let faceAgeBucket = "young";
let avatarModelGender = "female";

const sessionId = crypto.randomUUID();

function refreshSessionLine() {
  if (sessionLine) {
    sessionLine.textContent = `${t("session")} ${sessionId.slice(0, 8)}…`;
  }
}
refreshSessionLine();

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

async function fetchWithTimeout(url, options = {}, timeoutMs = FETCH_TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
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

function getLocale() {
  const v = localeSelect?.value;
  return v === "en" ? "en" : "fa";
}

function getGenderFilter() {
  const v = genderSelect?.value || voiceGenderSelect?.value || "all";
  if (v === "female" || v === "male") {
    return v;
  }
  return "all";
}

function genderLabelShort(gender) {
  if (gender === "female") {
    return t("genderFemale");
  }
  if (gender === "male") {
    return t("genderMale");
  }
  return "";
}

function syncVoiceControls() {
  if (voiceThemeSelect) {
    voiceThemeSelect.innerHTML = themeSelect?.innerHTML || "";
    voiceThemeSelect.value = themeSelect?.value || "blue";
  }
  if (voiceLocaleSelect) {
    voiceLocaleSelect.value = getLocale();
  }
  if (voiceGenderSelect && genderSelect) {
    voiceGenderSelect.value = genderSelect.value || "all";
  }
  if (voiceVoiceSelect) {
    voiceVoiceSelect.innerHTML = voiceSelect?.innerHTML || "";
    voiceVoiceSelect.value = voiceSelect?.value || "";
    voiceVoiceSelect.disabled = Boolean(voiceSelect?.disabled);
  }
  if (voiceSpeedSelect) {
    voiceSpeedSelect.value = speedSelect?.value || "medium";
  }
  if (voiceAvatarGenderSelect) {
    voiceAvatarGenderSelect.value = avatarModelGender;
  }
  syncGenderSelectLabels();
  syncSpeedSelectLabels();
}

function syncGenderSelectLabels() {
  const selects = [genderSelect, voiceGenderSelect].filter(Boolean);
  for (const sel of selects) {
    const optAll = sel.querySelector("option[value='all']");
    const optF = sel.querySelector("option[value='female']");
    const optM = sel.querySelector("option[value='male']");
    if (optAll) optAll.textContent = t("genderAll");
    if (optF) optF.textContent = t("genderFemale");
    if (optM) optM.textContent = t("genderMale");
  }
}

function syncSpeedSelectLabels() {
  const selects = [speedSelect, voiceSpeedSelect].filter(Boolean);
  for (const sel of selects) {
    const optLow = sel.querySelector("option[value='low']");
    const optMed = sel.querySelector("option[value='medium']");
    const optHi = sel.querySelector("option[value='high']");
    if (optLow) optLow.textContent = t("speedLow");
    if (optMed) optMed.textContent = t("speedMedium");
    if (optHi) optHi.textContent = t("speedHigh");
  }
  if (voiceAvatarGenderSelect) {
    const m = voiceAvatarGenderSelect.querySelector("option[value='male']");
    const f = voiceAvatarGenderSelect.querySelector("option[value='female']");
    if (m) m.textContent = t("avatarMale");
    if (f) f.textContent = t("avatarFemale");
  }
  syncAvatarGenderButtons();
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
  const loc = getLocale();
  themeSelect.innerHTML = "";
  THEMES.forEach((th) => {
    const opt = document.createElement("option");
    opt.value = th.id;
    opt.textContent = window.PersonaI18n
      ? window.PersonaI18n.themeLabel(th.id, loc)
      : th.id;
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
  if (voiceThemeSelect) {
    voiceThemeSelect.value = id;
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
  if (window.PersonaI18n) {
    window.PersonaI18n.applyStaticUi(loc);
  }
  initThemeSelect();
  if (chatScroll) {
    chatScroll.classList.toggle("chat-rtl", loc === "fa");
  }
  if (typingLabel) {
    typingLabel.textContent = t("typing");
  }
  if (userInput) {
    userInput.placeholder = t("inputPlaceholder");
  }
  if (lipSyncStatus && window.voiceSession?.phase !== "speaking") {
    lipSyncStatus.textContent = lipSyncLabel("ready");
  }
  if (speedSelect) {
    syncSpeedSelectLabels();
  }
  syncVoiceControls();
  refreshSessionLine();
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

function initGenderSelect() {
  const raw = window.localStorage.getItem(STORAGE_VOICE_GENDER);
  const ok = raw === "female" || raw === "male" || raw === "all";
  const value = ok ? raw : "all";
  if (genderSelect) {
    genderSelect.value = value;
  }
  if (voiceGenderSelect) {
    voiceGenderSelect.value = value;
  }
}

function getSpeakingSpeed() {
  const v = speedSelect?.value;
  if (v === "low" || v === "high") {
    return v;
  }
  return "medium";
}

function voicesForLocale(_locale) {
  const gender = getGenderFilter();
  return allVoices.filter((v) => {
    if (gender === "all") {
      return true;
    }
    return String(v.gender || "female") === gender;
  });
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

function syncAvatarGenderButtons() {
  if (!avatarGenderSegment) {
    return;
  }
  avatarGenderSegment.querySelectorAll(".seg-btn").forEach((btn) => {
    const ok = btn.getAttribute("data-avatar-gender") === avatarModelGender;
    btn.classList.toggle("is-selected", ok);
    if (btn.getAttribute("data-avatar-gender") === "male") {
      btn.textContent = t("avatarMale");
    } else if (btn.getAttribute("data-avatar-gender") === "female") {
      btn.textContent = t("avatarFemale");
    }
  });
}

function setAvatarModelGender(gender) {
  const next = gender === "female" ? "female" : "male";
  avatarModelGender = next;
  window.localStorage.setItem(STORAGE_MODEL_GENDER, next);
  syncAvatarGenderButtons();
  if (voiceAvatarGenderSelect) {
    voiceAvatarGenderSelect.value = next;
  }
  window.PersonaAvatar?.setGender?.(next);
}

function initAvatarModelGender() {
  const raw = window.localStorage.getItem(STORAGE_MODEL_GENDER);
  avatarModelGender = raw === "female" ? "female" : "male";
  syncAvatarGenderButtons();
  if (voiceAvatarGenderSelect) {
    voiceAvatarGenderSelect.value = avatarModelGender;
  }
}

function initVoiceAndFaceChrome() {
  initAvatarModelGender();
}

function syncFaceFromSelectedVoice() {
  const vid = getSelectedVoiceId();
  const vmeta = allVoices.find((x) => x.id === vid);
  if (!vmeta) {
    return;
  }
  faceAgeBucket = normalizedVoiceAge(vmeta);
}

function populateVoiceSelect() {
  if (!voiceSelect) {
    return;
  }
  let list = voicesForLocale(getLocale());
  if (list.length === 0 && getGenderFilter() !== "all") {
    list = allVoices.slice();
  }
  const stored = window.localStorage.getItem(voiceStorageKey());
  const prev = voiceSelect.value;
  voiceSelect.innerHTML = "";
  if (list.length === 0) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = t("voiceNoMatch");
    voiceSelect.appendChild(opt);
    voiceSelect.disabled = true;
    voiceSelect.setAttribute("data-empty-voices", "1");
    syncVoiceControls();
    return;
  }
  voiceSelect.disabled = false;
  voiceSelect.removeAttribute("data-empty-voices");
  list.forEach((v) => {
    const opt = document.createElement("option");
    opt.value = v.id;
    const g = genderLabelShort(v.gender);
    opt.textContent = g ? `${v.label || v.id} · ${g}` : v.label || v.id;
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
  syncFaceFromSelectedVoice();
  syncVoiceControls();
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

function lipSyncLabel(key) {
  const map = {
    ready: "lipReady",
    animating: "lipAnimating",
    waiting: "lipWaiting",
    error: "lipError",
  };
  return t(map[key] || "lipReady");
}

let lastHealth = null;

function updateSetupHelp(kind, health) {
  if (!setupHelp || !setupHelpBody) {
    return;
  }
  const data = health || lastHealth;
  if (data?.llmConfigSuspicious && kind !== "sidecar") {
    kind = "llm_config";
  } else if (data?.ttsConfigSuspicious && kind !== "sidecar" && kind !== "llm_config") {
    kind = "tts_config";
  }
  const keyMap = {
    ok: "helpOk",
    sidecar: "helpSidecar",
    llm: "helpLlm",
    llm_config: "helpLlmConfig",
    tts: "helpTts",
    tts_config: "helpTtsConfig",
    partial: "helpPartial",
  };
  const textKey = keyMap[kind] || "helpPartial";
  let text = t(textKey);
  const ttsInfo = data?.tts;
  if (ttsInfo && (kind === "tts" || kind === "tts_config" || kind === "partial")) {
    if (ttsInfo.apiBase) {
      text += `\n${ttsInfo.apiBase}`;
    }
    if (ttsInfo.model) {
      text += `\n${ttsInfo.model}`;
    }
    if (data.ttsApiKeyHint) {
      text += `\n${data.ttsApiKeyHint}`;
    }
  }
  if (data && (kind === "llm_config" || kind === "llm")) {
    if (data.modelBase) {
      text += `\n${data.modelBase}`;
    }
    if (data.modelApiKeyHint) {
      text += `\n${data.modelApiKeyHint}`;
    }
    if (data.envSource) {
      text += `\n${data.envSource}`;
    }
  }
  setupHelpBody.textContent = text;
  setupHelp.classList.toggle("hidden", kind === "ok");
}

window.__personaUpdateSetupHelp = updateSetupHelp;

function setHealthPill(ok, labelKey) {
  if (!healthPill) {
    return;
  }
  healthPill.textContent = labelKey ? t(labelKey) : "…";
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
  if (role === "user") {
    return t("roleYou");
  }
  if (role === "error") {
    return t("roleError");
  }
  return t("roleAssistant");
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
  addMessage(t("welcome"), "assistant");
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
  if (btnMic) {
    btnMic.disabled = busy && !micRecording;
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
  avatarGenderSegment?.querySelectorAll(".seg-btn").forEach((b) => {
    b.disabled = busy;
  });
}

function applyVisemeFrame(frame) {
  const weight = Number(frame.weight || 0.7);
  const visemeRaw = String(frame.viseme || "viseme_closed");
  const visemeKey = visemeRaw.replace(/^viseme_/, "");
  window.PersonaAvatar?.applyViseme?.(visemeKey, weight);
}

function resetMouth() {
  window.PersonaAvatar?.resetMouth?.();
}

function stopLipSyncDriver() {
  if (lipSyncRafId != null) {
    cancelAnimationFrame(lipSyncRafId);
    lipSyncRafId = null;
  }
}

function clearLipSyncTimers() {
  stopLipSyncDriver();
  while (mouthTimers.length) {
    clearTimeout(mouthTimers.pop());
  }
}

function scaleVisemesToDuration(visemes, targetMs) {
  if (!Array.isArray(visemes) || visemes.length === 0 || !targetMs || targetMs <= 0) {
    return visemes || [];
  }
  const lastEnd = Number(visemes[visemes.length - 1].endMs || 0);
  if (!lastEnd || Math.abs(lastEnd - targetMs) < 50) {
    return visemes;
  }
  const scale = targetMs / lastEnd;
  return visemes.map((frame) => ({
    ...frame,
    startMs: Math.round(Number(frame.startMs || 0) * scale),
    endMs: Math.round(Number(frame.endMs || 0) * scale),
  }));
}

function findVisemeAtTime(visemes, ms) {
  for (const frame of visemes) {
    const start = Number(frame.startMs || 0);
    const end = Number(frame.endMs || start + 60);
    if (ms >= start && ms < end) {
      return frame;
    }
  }
  if (visemes.length && ms >= Number(visemes[visemes.length - 1].endMs || 0)) {
    return { viseme: "X", weight: 0.7 };
  }
  return visemes[0];
}

function lipSyncTargetMs(audio, fallbackMs) {
  if (audio && Number.isFinite(audio.duration) && audio.duration > 0) {
    return Math.round(audio.duration * 1000);
  }
  return Number(fallbackMs || 0);
}

function startLipSyncDriver(timeline, audio) {
  stopLipSyncDriver();
  if (!timeline.length) {
    return;
  }

  const tick = () => {
    if (!audio || audio.ended) {
      lipSyncRafId = null;
      return;
    }
    applyVisemeFrame(findVisemeAtTime(timeline, audio.currentTime * 1000));
    lipSyncRafId = requestAnimationFrame(tick);
  };

  if (audio) {
    const onTimeUpdate = () => {
      if (!audio.paused && !audio.ended) {
        applyVisemeFrame(findVisemeAtTime(timeline, audio.currentTime * 1000));
      }
    };
    audio.addEventListener("timeupdate", onTimeUpdate);
    audio.addEventListener("playing", () => {
      if (lipSyncRafId == null && !audio.ended) {
        lipSyncRafId = requestAnimationFrame(tick);
      }
    });
    audio.addEventListener(
      "ended",
      () => {
        audio.removeEventListener("timeupdate", onTimeUpdate);
        stopLipSyncDriver();
        resetMouth();
        if (lipSyncStatus) {
          lipSyncStatus.textContent = lipSyncLabel("ready");
        }
      },
      { once: true },
    );
    lipSyncRafId = requestAnimationFrame(tick);
    return;
  }

  let lastEnd = 0;
  timeline.forEach((frame) => {
    const start = Number(frame.startMs || 0);
    const end = Number(frame.endMs || start + 80);
    lastEnd = Math.max(lastEnd, end);
    mouthTimers.push(setTimeout(() => applyVisemeFrame(frame), start));
  });
  mouthTimers.push(
    setTimeout(() => {
      resetMouth();
      if (lipSyncStatus) {
        lipSyncStatus.textContent = lipSyncLabel("ready");
      }
    }, lastEnd + 30),
  );
}

function runVisemeTimeline(visemes, audio, durationFallbackMs) {
  clearLipSyncTimers();
  const raw = Array.isArray(visemes) ? visemes : [];
  if (raw.length === 0) {
    resetMouth();
    if (lipSyncStatus) {
      lipSyncStatus.textContent = lipSyncLabel("ready");
    }
    return;
  }

  if (lipSyncStatus) {
    lipSyncStatus.textContent = lipSyncLabel("animating");
  }

  const targetMs = lipSyncTargetMs(audio, durationFallbackMs || raw[raw.length - 1]?.endMs);
  const timeline = scaleVisemesToDuration(raw, targetMs);
  startLipSyncDriver(timeline, audio || null);
}

let currentAssistantAudio = null;

function playAssistantWithLipSync(payload, onEnded) {
  const visemes = payload.visemes || [];
  const durationMs = payload.meta?.durationMs;
  const cacheBust = `${Date.now()}-${payload.meta?.voiceId ?? ""}`;
  const url = getAudioUrl(payload.audioPath, cacheBust);
  if (!url) {
    runVisemeTimeline(visemes, null, durationMs);
    if (onEnded) {
      window.setTimeout(onEnded, durationMs || 0);
    }
    return null;
  }

  const audio = new Audio(url);
  currentAssistantAudio = audio;
  let lipSyncStarted = false;
  const beginLipSync = () => {
    if (lipSyncStarted) {
      return;
    }
    lipSyncStarted = true;
    runVisemeTimeline(visemes, audio, durationMs);
  };

  audio.addEventListener("play", beginLipSync, { once: true });
  audio.addEventListener("playing", beginLipSync, { once: true });
  audio.addEventListener("ended", () => {
    if (currentAssistantAudio === audio) {
      currentAssistantAudio = null;
    }
    onEnded?.();
  }, { once: true });
  audio.play().then(beginLipSync).catch(() => {
    if (backendStatus) {
      backendStatus.textContent = t("audioBlocked");
    }
    runVisemeTimeline(visemes, null, durationMs);
    window.setTimeout(() => onEnded?.(), Math.max(300, Number(durationMs) || 600));
  });
  return audio;
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
    if (backendStatus) {
      backendStatus.textContent = t("audioBlocked");
    }
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

function humanizeChatError(message) {
  const msg = String(message || "");
  if (/403/.test(msg)) {
    if (lastHealth?.llmConfigSuspicious) {
      return t("errLlmAuthMissing");
    }
    if (/debtor/i.test(msg)) {
      return t("errLlmBilling");
    }
    return t("errLlmAuth");
  }
  return msg || t("errGeneric");
}


async function checkBackend() {
  if (voiceStatus) {
    voiceStatus.textContent = "…";
  }
  setHealthPill(false, "pillChecking");
  if (backendStatus) {
    backendStatus.textContent = t("checking");
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
    lastHealth = data;
    const modelLabel = data.modelName ? String(data.modelName) : "model";
    modelStatus.textContent = `${t("modelOk")} · ${modelLabel}`;
    const ttsOk = Boolean(data.ttsConfigured);
    const tts = data.tts || {};
    const nVoices = typeof tts.voiceCount === "number" ? tts.voiceCount : 0;
    if (voiceStatus) {
      if (ttsOk) {
        const vid = getSelectedVoiceId();
        const vmeta = allVoices.find((x) => x.id === vid);
        voiceStatus.textContent = vmeta ? vmeta.label : t("voiceReady");
      } else if (nVoices === 0) {
        voiceStatus.textContent = t("voiceNotConfigured");
      } else {
        voiceStatus.textContent = t("voiceIncomplete");
      }
    }
    backendStatus.textContent = ttsOk
      ? `${t("connected")} · ${API_BASE || window.location.origin}`
      : t("apiPartial");
    setHealthPill(true, "pillOnline");
    if (modeBadge) {
      modeBadge.textContent = ttsOk ? t("badgeLive") : t("badgePartial");
    }
    if (ttsOk) {
      updateSetupHelp("ok", data);
    } else if (data.llmConfigSuspicious) {
      updateSetupHelp("llm_config", data);
    } else if (data.ttsConfigSuspicious) {
      updateSetupHelp("tts_config", data);
    } else if (nVoices === 0) {
      updateSetupHelp("tts", data);
    } else {
      updateSetupHelp("partial", data);
    }
    updateMicAvailability();
  } catch (error) {
    modelStatus.textContent = t("modelUnreachable");
    if (voiceStatus) {
      voiceStatus.textContent = "—";
    }
    const timedOut = error instanceof Error && error.name === "AbortError";
    backendStatus.textContent = timedOut ? t("apiTimeout") : t("apiOffline");
    setHealthPill(false, "pillOffline");
    if (modeBadge) {
      modeBadge.textContent = t("badgeOffline");
    }
    updateSetupHelp(
      isTauriDesktopShell() && !window.__PERSONA_API_BASE__ ? "sidecar" : "llm",
    );
    updateMicAvailability();
  }
}

async function requestAssistant(userText, voiceIdOverride, signal) {
  const voiceId =
    voiceIdOverride !== undefined ? voiceIdOverride : getSelectedVoiceId();
  const response = await fetch(apiUrl("/chat/respond"), {
    method: "POST",
    signal,
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
    throw new Error(detail || t("errGeneric"));
  }

  return data;
}

function waitForPersonaAvatar(timeoutMs = 8000) {
  if (window.PersonaAvatar) {
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    const started = Date.now();
    const timer = window.setInterval(() => {
      if (window.PersonaAvatar || Date.now() - started > timeoutMs) {
        window.clearInterval(timer);
        resolve();
      }
    }, 30);
  });
}

async function bootstrap() {
  initThemeSelect();
  initLocaleSelect();
  initSpeedSelect();
  initGenderSelect();
  initVoiceAndFaceChrome();
  applyChatChrome();

  await waitForPersonaAvatar();

  // Desktop: wait for sidecar BEFORE loading VRM — large binaries fail on Tauri asset://
  // and must be fetched from the backend HTTP origin instead.
  if (isTauriDesktopShell()) {
    if (backendStatus) {
      backendStatus.textContent = t("startingBackend");
    }
    setHealthPill(false, "pillStarting");
    try {
      await desktopBackendReady;
      API_BASE = resolveApiBase();
    } catch (error) {
      const code = error instanceof Error ? error.code : null;
      if (backendStatus) {
        backendStatus.textContent =
          code === "SIDECAR_TIMEOUT" ? t("sidecarTimeout") : t("sidecarFailed");
      }
      setHealthPill(false, "pillOffline");
      if (modeBadge) {
        modeBadge.textContent = t("badgeOffline");
      }
      updateSetupHelp("sidecar");
      return;
    }
  } else if (backendStatus) {
    backendStatus.textContent = t("connecting");
  }

  if (avatarViewport && window.PersonaAvatar) {
    window.PersonaAvatar.mount(avatarViewport);
    try {
      await window.PersonaAvatar.setGender(avatarModelGender);
    } catch (err) {
      console.error("Avatar mount/setGender failed", err);
    }
  }

  await fetchVoiceConfig();
  await checkBackend();
  updateMicAvailability();
}

let micRecording = false;
let micStream = null;
let micAudioContext = null;
let micWavSource = null;
let micWavProcessor = null;
let micWavChunks = [];
const MIC_SAMPLE_RATE = 16000;
let speechRecognition = null;
let browserTranscript = "";
let micMode = null;

function speechRecognitionSupported() {
  return Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
}

function sttBackendReady() {
  return Boolean(lastHealth?.sttConfigured);
}

function micInputReady() {
  return sttBackendReady() || speechRecognitionSupported();
}

function setMicRecordingUi(active) {
  if (btnMic) {
    btnMic.classList.toggle("recording", active);
    btnMic.setAttribute("aria-pressed", active ? "true" : "false");
    btnMic.title = t(active ? "micStop" : "micStart");
    btnMic.setAttribute("aria-label", t(active ? "micStop" : "micStart"));
  }
  if (btnVoiceMain) {
    btnVoiceMain.classList.toggle("is-recording", active);
    btnVoiceMain.setAttribute("aria-label", t(active ? "micStop" : "voiceStart"));
    btnVoiceMain.title = t(active ? "micStop" : "voiceStart");
  }
}

function updateMicAvailability() {
  if (!btnMic) {
    return;
  }
  const ready = micInputReady();
  btnMic.disabled = !ready || (btnSend?.disabled && !micRecording);
  btnMic.title = ready ? t(micRecording ? "micStop" : "micStart") : t("errMicUnsupported");
}

async function cleanupMicStream() {
  if (micWavProcessor) {
    try {
      micWavProcessor.disconnect();
    } catch (_e) {
      /* ignore */
    }
    micWavProcessor.onaudioprocess = null;
  }
  if (micWavSource) {
    try {
      micWavSource.disconnect();
    } catch (_e) {
      /* ignore */
    }
  }
  if (micAudioContext && micAudioContext.state !== "closed") {
    try {
      await micAudioContext.close();
    } catch (_e) {
      /* ignore */
    }
  }
  micWavProcessor = null;
  micWavSource = null;
  micAudioContext = null;
  micWavChunks = [];
  if (micStream) {
    micStream.getTracks().forEach((track) => track.stop());
  }
  micStream = null;
}

function mergeFloat32Chunks(chunks) {
  const total = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const merged = new Float32Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    merged.set(chunk, offset);
    offset += chunk.length;
  }
  return merged;
}

function encodeWavBlob(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const writeString = (offset, text) => {
    for (let i = 0; i < text.length; i += 1) {
      view.setUint8(offset + i, text.charCodeAt(i));
    }
  };
  writeString(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, samples.length * 2, true);
  let offset = 44;
  for (let i = 0; i < samples.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
    offset += 2;
  }
  return new Blob([buffer], { type: "audio/wav" });
}

function finalizeWavRecording() {
  const rate = micAudioContext?.sampleRate || MIC_SAMPLE_RATE;
  const samples = mergeFloat32Chunks(micWavChunks);
  if (!samples.length) {
    return null;
  }
  return encodeWavBlob(samples, rate);
}

function stopBrowserListening() {
  if (speechRecognition) {
    try {
      speechRecognition.stop();
    } catch (_e) {
      /* ignore */
    }
    speechRecognition = null;
  }
  return browserTranscript.trim();
}

function startBrowserListening() {
  const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Ctor) {
    throw new Error(t("errMicUnsupported"));
  }
  browserTranscript = "";
  const rec = new Ctor();
  rec.continuous = true;
  rec.interimResults = true;
  rec.lang = getLocale() === "fa" ? "fa-IR" : "en-US";
  rec.onresult = (event) => {
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      if (event.results[i].isFinal) {
        browserTranscript += event.results[i][0].transcript;
      }
    }
  };
  rec.onerror = (event) => {
    if (event.error === "not-allowed") {
      addMessage(t("errMicDenied"), "assistant", { error: true });
    }
  };
  rec.start();
  speechRecognition = rec;
}

async function transcribeRecordingBlob(blob) {
  const form = new FormData();
  const isWav = blob.type.includes("wav") || blob.type === "audio/wave";
  form.append("file", blob, isWav ? "speech.wav" : "speech.webm");
  form.append("locale", getLocale());
  const response = await fetchWithTimeout(apiUrl("/chat/transcribe"), {
    method: "POST",
    body: form,
  }, 60000);
  if (!response.ok) {
    let detail = await response.text();
    try {
      const parsed = JSON.parse(detail);
      if (parsed && typeof parsed.detail === "string") {
        detail = parsed.detail;
      }
    } catch (_e) {
      /* keep raw */
    }
    throw new Error(detail || `Transcribe HTTP ${response.status}`);
  }
  const data = await parseJsonSafe(response);
  return String(data?.text || "").trim();
}

async function startMicInput() {
  if (!micInputReady() || micRecording || btnSend?.disabled) {
    return;
  }
  if (sttBackendReady()) {
    micMode = "recorder";
    micWavChunks = [];
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    micAudioContext = new AudioContext({ sampleRate: MIC_SAMPLE_RATE });
    micWavSource = micAudioContext.createMediaStreamSource(micStream);
    micWavProcessor = micAudioContext.createScriptProcessor(4096, 1, 1);
    micWavProcessor.onaudioprocess = (event) => {
      if (!micRecording) {
        return;
      }
      micWavChunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
    };
    micWavSource.connect(micWavProcessor);
    micWavProcessor.connect(micAudioContext.destination);
  } else {
    micMode = "browser";
    startBrowserListening();
  }
  micRecording = true;
  setMicRecordingUi(true);
  updateMicAvailability();
}

async function stopMicInput() {
  if (!micRecording) {
    return;
  }
  micRecording = false;
  setMicRecordingUi(false);
  updateMicAvailability();

  let text = "";
  try {
    if (micMode === "recorder") {
      const wavBlob = finalizeWavRecording();
      await cleanupMicStream();
      if (!wavBlob || wavBlob.size <= 44) {
        addMessage(t("errMicEmpty"), "assistant", { error: true });
        return;
      }
      if (userInput) {
        userInput.placeholder = t("micTranscribing");
      }
      text = await transcribeRecordingBlob(wavBlob);
    } else {
      text = stopBrowserListening();
      micMode = null;
    }
  } catch (error) {
    await cleanupMicStream();
    stopBrowserListening();
    micMode = null;
    setBusy(false);
    applyChatChrome();
    const msg = error instanceof Error ? error.message : String(error);
    if (/not-allowed|Permission/i.test(msg)) {
      addMessage(t("errMicDenied"), "assistant", { error: true });
    } else {
      addMessage(t("errMicTranscribe"), "assistant", { error: true });
    }
    return;
  }

  applyChatChrome();
  if (!text) {
    if (window.voiceSession?.active) {
      window.voiceSession.state("voiceReadyState");
      window.voiceSession.caption(t("errMicEmpty"));
    } else {
      addMessage(t("errMicEmpty"), "assistant", { error: true });
    }
    return;
  }
  if (window.voiceSession?.active) {
    await window.voiceSession.handleTranscript(text);
    return;
  }
  await sendUserMessage(text);
}

async function toggleMicInput() {
  if (micRecording) {
    await stopMicInput();
    return;
  }
  try {
    await startMicInput();
  } catch (error) {
    micRecording = false;
    setMicRecordingUi(false);
    await cleanupMicStream();
    updateMicAvailability();
    const msg = error instanceof Error ? error.message : String(error);
    if (/not-allowed|Permission/i.test(msg)) {
      addMessage(t("errMicDenied"), "assistant", { error: true });
    } else {
      addMessage(t("errMicUnsupported"), "assistant", { error: true });
    }
  }
}

async function sendUserMessage(text, options = {}) {
  const trimmed = (text || "").trim();
  if (!trimmed) {
    return;
  }

  const fromVoice = Boolean(options.fromVoice || window.voiceSession?.active);
  addMessage(trimmed, "user");
  if (userInput) {
    userInput.value = "";
  }
  const voiceIdForRequest = getSelectedVoiceId();
  if (!voiceIdForRequest) {
    addMessage(t("errNoVoice"), "assistant", { error: true });
    updateSetupHelp("tts");
    setBusy(false);
    if (fromVoice) {
      window.voiceSession?.state("voiceReadyState");
      window.voiceSession?.caption(t("errNoVoice"));
    }
    return;
  }
  setBusy(true);
  setTyping(true);
  if (lipSyncStatus) {
    lipSyncStatus.textContent = lipSyncLabel("waiting");
  }
  if (fromVoice) {
    window.voiceSession?.state("voiceThinking");
  }

  try {
    const payload = await requestAssistant(trimmed, voiceIdForRequest, options.signal);
    setTyping(false);
    addMessage(payload.assistantText, "assistant");
    if (fromVoice) {
      window.voiceSession?.state("voiceSpeaking");
    }
    applyMetrics(payload.meta || {});
    const onEnded =
      options.onAudioEnded ||
      (fromVoice ? () => window.voiceSession?.onAssistantAudioEnded() : null);
    const audio = playAssistantWithLipSync(payload, onEnded);
    if (fromVoice) {
      window.voiceSession?.startSyncedCaption(payload.assistantText, audio);
    }
  } catch (error) {
    setTyping(false);
    if (error?.name === "AbortError") {
      if (fromVoice) {
        window.voiceSession?.state("voiceReadyState");
      }
      return;
    }
    const msg = error instanceof Error ? error.message : String(error);
    addMessage(humanizeChatError(msg), "assistant", { error: true });
    if (fromVoice) {
      window.voiceSession?.caption(humanizeChatError(msg));
      window.voiceSession?.state("voiceReadyState");
    }
    resetMetrics();
    runVisemeTimeline(
      [
        { startMs: 0, endMs: 180, viseme: "D", weight: 0.9 },
        { startMs: 181, endMs: 360, viseme: "B", weight: 0.8 },
        { startMs: 361, endMs: 600, viseme: "X", weight: 0.8 },
      ],
      null,
      600,
    );
    if (lipSyncStatus) {
      lipSyncStatus.textContent = lipSyncLabel("error");
    }
  } finally {
    setBusy(false);
    updateMicAvailability();
  }
}

class VoiceSession {
  constructor() {
    this.active = false;
    this.phase = "idle";
    this.autoListen = window.localStorage.getItem(STORAGE_VOICE_AUTO_LISTEN) !== "false";
    this.abortController = null;
    this.listenTimer = null;
    this.turnId = 0;
    this.overlay = document.getElementById("voiceSanctuary");
    this.captionEl = document.getElementById("voiceCaption");
    this.stateEl = document.getElementById("voiceState");
    this.autoListenEl = document.getElementById("voiceAutoListen");
    this._captionRaf = null;
    this._captionAudio = null;
    this._captionFull = "";
    this._captionStartedAt = 0;
    if (this.autoListenEl) {
      this.autoListenEl.checked = this.autoListen;
    }
  }

  caption(text) {
    if (this.captionEl) {
      this.captionEl.textContent = text || "";
    }
  }

  /** Reveal assistant text in sync with audio playback (not all at once). */
  startSyncedCaption(fullText, audio) {
    this.stopSyncedCaption();
    const text = String(fullText || "").trim();
    if (!text) {
      this.caption("");
      return;
    }
    this._captionFull = text;
    this._captionAudio = audio || null;
    this.caption("");

    const tick = () => {
      if (!this.active) {
        this.stopSyncedCaption();
        return;
      }
      const audioEl = this._captionAudio;
      let ratio = 0;
      if (audioEl && Number.isFinite(audioEl.duration) && audioEl.duration > 0) {
        ratio = Math.min(1, Math.max(0, audioEl.currentTime / audioEl.duration));
      } else if (this._captionStartedAt) {
        // fallback ~14 chars/sec if audio duration unknown
        const elapsed = (Date.now() - this._captionStartedAt) / 1000;
        ratio = Math.min(1, elapsed / Math.max(1.2, text.length / 14));
      }
      const count = Math.max(1, Math.ceil(text.length * ratio));
      this.caption(text.slice(0, count));
      if (ratio < 1 && !(audioEl && audioEl.ended)) {
        this._captionRaf = requestAnimationFrame(tick);
      } else {
        this.caption(text);
        this._captionRaf = null;
      }
    };
    this._captionStartedAt = Date.now();
    this._captionRaf = requestAnimationFrame(tick);
  }

  stopSyncedCaption() {
    if (this._captionRaf != null) {
      cancelAnimationFrame(this._captionRaf);
      this._captionRaf = null;
    }
    this._captionAudio = null;
    this._captionFull = "";
    this._captionStartedAt = 0;
  }

  state(key) {
    if (this.stateEl) {
      this.stateEl.textContent = t(key);
    }
    if (key === "voiceListening") {
      this.phase = "listening";
    } else if (key === "voiceThinking") {
      this.phase = "thinking";
    } else if (key === "voiceSpeaking") {
      this.phase = "speaking";
    } else {
      this.phase = "idle";
    }
  }

  moveAvatarTo(stage) {
    const vp = avatarViewport;
    if (!stage || !vp) {
      return;
    }
    if (!stage.contains(vp)) {
      stage.appendChild(vp);
      window.PersonaAvatar?.onHostMoved?.();
    }
  }

  open() {
    this.active = true;
    this.turnId += 1;
    document.body.dataset.view = "voice";
    this.overlay?.classList.remove("hidden");
    syncVoiceControls();
    this.moveAvatarTo(document.getElementById("voiceAvatarStage"));
    this.caption("");
    this.state("voiceReadyState");
    btnVoiceMain?.focus();
  }

  close() {
    this.active = false;
    this.turnId += 1;
    clearTimeout(this.listenTimer);
    this.listenTimer = null;
    this.stopSyncedCaption();
    this.interrupt({ silent: true });
    if (micRecording) {
      micRecording = false;
      setMicRecordingUi(false);
      cleanupMicStream();
      stopBrowserListening();
      micMode = null;
    }
    this.moveAvatarTo(chatAvatarStage || document.querySelector(".avatar-stage"));
    this.overlay?.classList.add("hidden");
    document.body.dataset.view = "chat";
    this.state("voiceReadyState");
    this.caption("");
  }

  interrupt(options = {}) {
    this.turnId += 1;
    clearTimeout(this.listenTimer);
    this.listenTimer = null;
    this.stopSyncedCaption();
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
    if (currentAssistantAudio) {
      try {
        currentAssistantAudio.pause();
        currentAssistantAudio.currentTime = 0;
      } catch (_e) {
        /* ignore */
      }
      currentAssistantAudio = null;
    }
    clearLipSyncTimers();
    resetMouth();
    if (!options.silent && this.active) {
      this.state("voiceReadyState");
    }
  }

  async toggleMain() {
    if (!this.active) {
      this.open();
      return;
    }
    if (this.phase === "speaking") {
      this.interrupt();
      return;
    }
    if (micRecording || this.phase === "listening") {
      await stopMicInput();
      return;
    }
    if (this.phase === "thinking") {
      this.interrupt();
      return;
    }
    await this.listen();
  }

  async listen() {
    if (!this.active || micRecording) {
      return;
    }
    this.interrupt({ silent: true });
    this.state("voiceListening");
    this.caption("");
    try {
      await startMicInput();
    } catch (error) {
      this.state("voiceReadyState");
      const msg = error instanceof Error ? error.message : String(error);
      this.caption(/not-allowed|Permission/i.test(msg) ? t("errMicDenied") : t("errMicUnsupported"));
    }
  }

  async handleTranscript(text) {
    if (!this.active) {
      await sendUserMessage(text);
      return;
    }
    const trimmed = String(text || "").trim();
    if (!trimmed) {
      this.state("voiceReadyState");
      this.caption(t("errMicEmpty"));
      return;
    }
    // Do not show user transcript on the voice stage — only assistant speech.
    this.caption("");
    this.state("voiceThinking");
    const turn = ++this.turnId;
    this.abortController = new AbortController();
    const signal = this.abortController.signal;
    try {
      await sendUserMessage(trimmed, {
        signal,
        fromVoice: true,
        onAudioEnded: () => {
          if (this.turnId !== turn) {
            return;
          }
          this.onAssistantAudioEnded();
        },
      });
    } finally {
      if (this.abortController?.signal === signal) {
        this.abortController = null;
      }
    }
  }

  onAssistantAudioEnded() {
    if (!this.active) {
      return;
    }
    if (this._captionFull) {
      this.caption(this._captionFull);
    }
    this.stopSyncedCaption();
    this.state("voiceReadyState");
    if (!this.autoListen) {
      return;
    }
    const turn = this.turnId;
    clearTimeout(this.listenTimer);
    this.listenTimer = window.setTimeout(() => {
      if (this.active && this.turnId === turn && this.autoListen) {
        this.listen();
      }
    }, 400);
  }
}

window.voiceSession = new VoiceSession();

btnModeSwitch?.addEventListener("click", () => window.voiceSession.open());
btnVoiceModeSwitch?.addEventListener("click", () => window.voiceSession.close());
btnCloseVoice?.addEventListener("click", () => window.voiceSession.close());
btnVoiceInterrupt?.addEventListener("click", () => window.voiceSession.interrupt());
btnVoiceMain?.addEventListener("click", () => window.voiceSession.toggleMain());

document.getElementById("voiceAutoListen")?.addEventListener("change", (event) => {
  window.voiceSession.autoListen = event.target.checked;
  window.localStorage.setItem(STORAGE_VOICE_AUTO_LISTEN, String(event.target.checked));
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && window.voiceSession?.active) {
    event.preventDefault();
    window.voiceSession.close();
  }
});

voiceThemeSelect?.addEventListener("change", () => applyTheme(voiceThemeSelect.value));
voiceLocaleSelect?.addEventListener("change", () => {
  if (localeSelect) {
    localeSelect.value = voiceLocaleSelect.value;
    localeSelect.dispatchEvent(new Event("change"));
  }
});
voiceGenderSelect?.addEventListener("change", () => {
  if (genderSelect) {
    genderSelect.value = voiceGenderSelect.value;
    genderSelect.dispatchEvent(new Event("change"));
  }
});
voiceVoiceSelect?.addEventListener("change", () => {
  if (voiceSelect) {
    voiceSelect.value = voiceVoiceSelect.value;
    voiceSelect.dispatchEvent(new Event("change"));
  }
});
voiceSpeedSelect?.addEventListener("change", () => {
  if (speedSelect) {
    speedSelect.value = voiceSpeedSelect.value;
    speedSelect.dispatchEvent(new Event("change"));
  }
});
voiceAvatarGenderSelect?.addEventListener("change", () => {
  setAvatarModelGender(voiceAvatarGenderSelect.value);
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await sendUserMessage(userInput?.value || "");
});

btnMic?.addEventListener("click", () => {
  toggleMicInput();
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
  if (lipSyncStatus) {
    lipSyncStatus.textContent = lipSyncLabel("ready");
  }
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
  if (window.voiceSession?.active) {
    window.voiceSession.state(
      window.voiceSession.phase === "listening"
        ? "voiceListening"
        : window.voiceSession.phase === "thinking"
          ? "voiceThinking"
          : window.voiceSession.phase === "speaking"
            ? "voiceSpeaking"
            : "voiceReadyState",
    );
  }
});

genderSelect?.addEventListener("change", () => {
  const g = getGenderFilter();
  window.localStorage.setItem(STORAGE_VOICE_GENDER, g);
  if (voiceGenderSelect) {
    voiceGenderSelect.value = g;
  }
  populateVoiceSelect();
});

voiceSelect?.addEventListener("change", () => {
  const v = getSelectedVoiceId();
  if (v) {
    window.localStorage.setItem(voiceStorageKey(), v);
  }
  syncFaceFromSelectedVoice();
  resetMouth();
  syncVoiceControls();
  checkBackend();
});

speedSelect?.addEventListener("change", () => {
  window.localStorage.setItem(STORAGE_SPEAKING_SPEED, getSpeakingSpeed());
  syncVoiceControls();
});

avatarGenderSegment?.addEventListener("click", (e) => {
  const target = e.target;
  const btn = target instanceof Element ? target.closest("button[data-avatar-gender]") : null;
  if (!btn) {
    return;
  }
  const next = btn.getAttribute("data-avatar-gender");
  if (next !== "male" && next !== "female") {
    return;
  }
  setAvatarModelGender(next);
});

if (window.location.protocol === "file:" && fileProtocolBanner) {
  fileProtocolBanner.classList.remove("hidden");
}

bootstrap().then(() => {
  seedWelcome();
  // First encounter: open voice conversation
  window.voiceSession?.open();
});
