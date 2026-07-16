(function () {
  "use strict";

  const STRINGS = {
    fa: {
      appTitle: "Persona AI",
      appSubtitle: "راهنمای روان‌شناختی",
      session: "نشست",
      theme: "تم",
      language: "زبان",
      voice: "صدا",
      speechSpeed: "سرعت گفتار",
      speedLow: "آرام",
      speedMedium: "متوسط",
      speedHigh: "تند",
      refreshStatus: "بروزرسانی وضعیت",
      clearChat: "پاک کردن گفتگو",
      clearChatTitle: "پاک کردن گفتگو",
      send: "ارسال",
      micStart: "صحبت با میکروفون — کلیک برای شروع",
      micStop: "توقف ضبط و ارسال",
      micListening: "در حال گوش دادن…",
      micTranscribing: "در حال تبدیل گفتار به متن…",
      voiceConversation: "گفتگوی صوتی",
      voiceChat: "گفتگوی صوتی",
      chatMode: "گفتگو",
      voiceTitle: "گفتگوی صوتی",
      voiceReadyState: "آماده شنیدن",
      voiceListening: "در حال گوش دادن…",
      voiceThinking: "در حال فکر کردن…",
      voiceSpeaking: "در حال صحبت…",
      voiceClose: "بستن",
      voiceStopSpeaking: "توقف صحبت",
      voiceAutoListen: "گوش دادن خودکار",
      voiceStart: "شروع گفتگو",
      voiceStop: "توقف گفتگو",
      gender: "جنسیت صدا",
      genderAll: "همه",
      genderFemale: "زنانه",
      genderMale: "مردانه",
      genderNeutral: "خنثی",
      errMicDenied: "دسترسی میکروفون رد شد — در تنظیمات Windows اجازه دهید.",
      errMicUnsupported: "ورودی صوتی در این مرورگر پشتیبانی نمی‌شود.",
      errMicEmpty: "متنی از ضبط شنیده نشد — دوباره تلاش کنید.",
      errMicTranscribe: "تبدیل گفتار به متن ناموفق بود.",
      avatar: "آواتار",
      avatarMale: "مرد",
      avatarFemale: "زن",
      chatTitle: "دستیار راهنمای روان‌شناختی",
      portraitAge: "سن چهره",
      ageChild: "کودک",
      ageYoung: "جوان",
      ageOld: "مسن",
      metricsTitle: "آخرین پاسخ",
      metricModel: "تأخیر مدل",
      metricTts: "تأخیر TTS",
      metricAudio: "مدت صدا",
      statusBackend: "بک‌اند",
      statusVoice: "صدا",
      statusLipSync: "لب‌خوان",
      lipReady: "آماده",
      lipAnimating: "در حال پخش",
      lipWaiting: "در انتظار",
      lipError: "خطا",
      pillOnline: "آنلاین",
      pillOffline: "آفلاین",
      pillStarting: "در حال راه‌اندازی",
      pillChecking: "در حال بررسی",
      badgeLive: "فعال",
      badgePartial: "ناقص",
      badgeOffline: "غیرفعال",
      connecting: "در حال اتصال…",
      checking: "در حال بررسی…",
      startingBackend: "در حال راه‌اندازی بک‌اند محلی…",
      connected: "متصل",
      modelOk: "سالم",
      modelUnreachable: "در دسترس نیست",
      voiceReady: "TTS آماده",
      voiceNoMatch: "(صدایی برای این زبان یافت نشد)",
      voiceNotConfigured: "TTS پیکربندی نشده — TTS_* یا MODEL_* را در .env تنظیم کنید",
      voiceIncomplete: "TTS ناقص است",
      apiPartial: "API آنلاین · TTS کامل نیست",
      apiTimeout: "بک‌اند محلی پاسخ نداد. مدل را اجرا کنید یا sidecar را rebuild کنید.",
      apiOffline: "بک‌اند در دسترس نیست. مدل و TTS را بررسی کنید.",
      sidecarTimeout:
        "راه‌اندازی بک‌اند بیش از ۳۰ ثانیه طول کشید. لاگ: %APPDATA%\\PersonaAI\\logs\\desktop.log — npm run sidecar:build",
      sidecarFailed: "بک‌اند دسکتاپ بالا نیامد. sidecar را rebuild کنید.",
      audioBlocked: "پخش صدا مسدود است — یک‌بار روی صفحه کلیک کنید.",
      typing: "دستیار در حال فکر کردن…",
      inputPlaceholder: "پیام را بنویسید… (Enter ارسال، Shift+Enter خط جدید)",
      welcome:
        "سلام. آماده‌ام تا با آرامش و به‌صورت مرحله‌به‌مرحله همراهت باشم.",
      roleYou: "شما",
      roleAssistant: "دستیار",
      roleError: "خطا",
      fileProtocol:
        "این صفحه را از طریق HTTP باز کنید (مثلاً http://127.0.0.1:8000) تا API کار کند.",
      winMinimize: "کوچک کردن",
      winMaximize: "بزرگ‌نمایی",
      winRestore: "بازگرداندن",
      winClose: "بستن",
      themeBlue: "آبی",
      themeBlack: "مشکی",
      themeWhite: "سفید",
      themeRed: "قرمز",
      themeGreen: "سبز",
      themeYellow: "زرد",
      themePurple: "بنفش",
      helpTitle: "راهنمای راه‌اندازی",
      helpSidecar:
        "بک‌اند دسکتاپ بالا نیامده. از ریشه پروژه npm run sidecar:build را اجرا کنید، سپس دوباره npm run desktop:dev.",
      helpLlm:
        "مدل گفتگو در دسترس نیست. Ollama را اجرا کنید یا MODEL_* را در apps/backend/.env (dev) یا %APPDATA%\\PersonaAI\\.env (نصب) تنظیم کنید.",
      helpLlmConfig:
        "کلید API واقعی لود نشده — sidecar هنوز local-key دارد. apps/backend/.env را آپدیت کن، sidecar:build بزن، یا مستقیم %APPDATA%\\PersonaAI\\.env را ویرایش کن.",
      helpTts:
        "TTS پیکربندی نشده. TTS_API_BASE، TTS_API_KEY و TTS_MODEL را در .env بگذارید (اگر TTS_* خالی باشد از MODEL_* استفاده می‌شود).",
      helpTtsConfig:
        "کلید TTS واقعی لود نشده. TTS_API_KEY یا MODEL_API_KEY را در .env فعال sidecar تنظیم کنید.",
      helpPartial:
        "API آنلاین است اما TTS کامل نیست — TTS_* را در .env بررسی کنید.",
      helpOk: "همه‌چیز آماده است. می‌توانید پیام بفرستید.",
      errNoVoice: "صدایی برای این زبان در لیست نیست — منوی «صدا» را بررسی کنید یا TTS_VOICE_FA/EN را در .env بگذارید.",
      errGeneric: "درخواست ناموفق بود. وضعیت را بروزرسانی کنید (↻).",
      errLlmBilling:
        "خطای API (403): پیام سرویس: حساب بدهکار. اگر موجودی داری، modelApiKeyHint در /health را با پنل GapGPT مقایسه کن.",
      errLlmAuth:
        "خطای API (403): کلید یا مدل رد شد — MODEL_API_KEY و MODEL_NAME در .env فعال sidecar را بررسی کن.",
      errLlmAuthMissing:
        "خطای API (403): کلید واقعی لود نشده (local-key). %APPDATA%\\PersonaAI\\.env یا apps/backend/.env را آپدیت کن و sidecar:build بزن.",
    },
    en: {
      appTitle: "Persona AI",
      appSubtitle: "Psychology guide",
      session: "Session",
      theme: "Theme",
      language: "Language",
      voice: "Voice",
      speechSpeed: "Speech speed",
      speedLow: "Low",
      speedMedium: "Medium",
      speedHigh: "High",
      refreshStatus: "Refresh status",
      clearChat: "Clear",
      clearChatTitle: "Clear conversation",
      send: "Send",
      micStart: "Talk with microphone — click to start",
      micStop: "Stop recording and send",
      micListening: "Listening…",
      micTranscribing: "Transcribing speech…",
      voiceConversation: "Voice conversation",
      voiceChat: "Voice chat",
      chatMode: "Chat mode",
      voiceTitle: "Voice conversation",
      voiceReadyState: "Ready to listen",
      voiceListening: "Listening…",
      voiceThinking: "Thinking…",
      voiceSpeaking: "Speaking…",
      voiceClose: "Close",
      voiceStopSpeaking: "Stop speaking",
      voiceAutoListen: "Listen automatically",
      voiceStart: "Start conversation",
      voiceStop: "Stop conversation",
      gender: "Voice gender",
      genderAll: "All",
      genderFemale: "Female",
      genderMale: "Male",
      genderNeutral: "Neutral",
      errMicDenied: "Microphone access denied — allow it in Windows settings.",
      errMicUnsupported: "Voice input is not supported in this browser.",
      errMicEmpty: "No speech detected — try again.",
      errMicTranscribe: "Speech-to-text failed.",
      avatar: "Avatar",
      avatarMale: "Male",
      avatarFemale: "Female",
      chatTitle: "Psychology guide assistant",
      portraitAge: "Portrait age",
      ageChild: "Child",
      ageYoung: "Young",
      ageOld: "Old",
      metricsTitle: "Last response",
      metricModel: "Model latency",
      metricTts: "TTS latency",
      metricAudio: "Audio length",
      statusBackend: "Backend",
      statusVoice: "Voice",
      statusLipSync: "Lip sync",
      lipReady: "Ready",
      lipAnimating: "Animating",
      lipWaiting: "Waiting",
      lipError: "Error",
      pillOnline: "Online",
      pillOffline: "Offline",
      pillStarting: "Starting",
      pillChecking: "Checking",
      badgeLive: "Live",
      badgePartial: "Partial",
      badgeOffline: "Offline",
      connecting: "Connecting…",
      checking: "Checking…",
      startingBackend: "Starting local backend…",
      connected: "Connected",
      modelOk: "OK",
      modelUnreachable: "Unreachable",
      voiceReady: "TTS ready",
      voiceNoMatch: "(No voice found for this language)",
      voiceNotConfigured: "TTS not configured — set TTS_* or MODEL_* in .env",
      voiceIncomplete: "TTS incomplete",
      apiPartial: "API online · TTS not fully configured",
      apiTimeout:
        "Local backend timed out. Start your model server or rebuild the sidecar (npm run sidecar:build).",
      apiOffline: "Backend unreachable. Check model and TTS setup.",
      sidecarTimeout:
        "Backend startup timed out (30s). Log: %APPDATA%\\PersonaAI\\logs\\desktop.log — npm run sidecar:build",
      sidecarFailed: "Desktop backend failed to start. Rebuild the sidecar.",
      audioBlocked: "Audio blocked — click the page once or allow autoplay.",
      typing: "Assistant is thinking…",
      inputPlaceholder: "Type your message… (Enter to send, Shift+Enter for newline)",
      welcome: "Hello. I am here to support you calmly, one step at a time.",
      roleYou: "You",
      roleAssistant: "Assistant",
      roleError: "Error",
      fileProtocol:
        "Open this page over HTTP (e.g. http://127.0.0.1:8000) so API calls work.",
      winMinimize: "Minimize",
      winMaximize: "Maximize",
      winRestore: "Restore",
      winClose: "Close",
      themeBlue: "Blue",
      themeBlack: "Black",
      themeWhite: "White",
      themeRed: "Red",
      themeGreen: "Green",
      themeYellow: "Yellow",
      themePurple: "Purple",
      helpTitle: "Setup guide",
      helpSidecar:
        "Desktop backend did not start. From the repo root run npm run sidecar:build, then npm run desktop:dev again.",
      helpLlm:
        "Chat model unreachable. Start Ollama or set MODEL_* in apps/backend/.env (dev) or %APPDATA%\\PersonaAI\\.env (installed).",
      helpLlmConfig:
        "Real API key not loaded — sidecar still has local-key. Update apps/backend/.env, rebuild sidecar, or edit %APPDATA%\\PersonaAI\\.env directly.",
      helpTts:
        "TTS is not configured. Set TTS_API_BASE, TTS_API_KEY, and TTS_MODEL in .env (falls back to MODEL_* when TTS_* is omitted).",
      helpTtsConfig:
        "Real TTS API key not loaded. Set TTS_API_KEY or MODEL_API_KEY in the active sidecar .env.",
      helpPartial:
        "API is up but TTS is incomplete — check TTS_* settings in .env.",
      helpOk: "Everything looks ready. You can send a message.",
      errNoVoice: "No voice listed for this language — check the Voice menu or set TTS_VOICE_FA/EN in .env.",
      errGeneric: "Request failed. Refresh status (↻) and try again.",
      errLlmBilling:
        "API error (403): provider says account is in debt. If your balance is fine, compare modelApiKeyHint on /health with your GapGPT dashboard.",
      errLlmAuth:
        "API error (403): key or model rejected — check MODEL_API_KEY and MODEL_NAME in the active sidecar .env.",
      errLlmAuthMissing:
        "API error (403): real API key not loaded (still local-key). Update %APPDATA%\\PersonaAI\\.env or apps/backend/.env and rebuild the sidecar.",
    },
  };

  const THEME_KEYS = {
    blue: "themeBlue",
    black: "themeBlack",
    white: "themeWhite",
    red: "themeRed",
    green: "themeGreen",
    yellow: "themeYellow",
    purple: "themePurple",
  };

  function currentLocale() {
    const sel = document.getElementById("localeSelect");
    return sel && sel.value === "en" ? "en" : "fa";
  }

  function t(key, locale) {
    const loc = locale || currentLocale();
    const bucket = STRINGS[loc] || STRINGS.en;
    return bucket[key] ?? STRINGS.en[key] ?? key;
  }

  function setText(id, key, locale) {
    const el = document.getElementById(id);
    if (el) {
      el.textContent = t(key, locale);
    }
  }

  function applyStaticUi(locale) {
    const loc = locale || currentLocale();
    document.documentElement.lang = loc === "fa" ? "fa" : "en";
    setText("desktopTitleSub", "appSubtitle", loc);
    setText("labelTheme", "theme", loc);
    setText("labelLanguage", "language", loc);
    setText("labelVoice", "voice", loc);
    setText("speedFieldLabel", "speechSpeed", loc);
    setText("btnClear", "clearChat", loc);
    setText("btnSend", "send", loc);
    setText("modeSwitchLabel", "voiceChat", loc);
    setText("voiceModeSwitchLabel", "chatMode", loc);
    setText("voiceLabelTheme", "theme", loc);
    setText("voiceLabelLanguage", "language", loc);
    setText("voiceLabelGender", "gender", loc);
    setText("labelGender", "gender", loc);
    setText("voiceLabelVoice", "voice", loc);
    setText("voiceSpeedFieldLabel", "speechSpeed", loc);
    setText("voiceFaceAgeLabel", "portraitAge", loc);
    setText("voiceTitle", "voiceTitle", loc);
    setText("btnCloseVoice", "voiceClose", loc);
    setText("btnVoiceInterrupt", "voiceStopSpeaking", loc);
    setText("voiceAutoListenLabel", "voiceAutoListen", loc);
    const btnMode = document.getElementById("btnModeSwitch");
    if (btnMode) {
      btnMode.title = t("voiceConversation", loc);
    }
    const btnVoiceBack = document.getElementById("btnVoiceModeSwitch");
    if (btnVoiceBack) {
      btnVoiceBack.title = t("chatMode", loc);
    }
    const btnMic = document.getElementById("btnMic");
    if (btnMic && btnMic.getAttribute("aria-pressed") !== "true") {
      btnMic.title = t("micStart", loc);
      btnMic.setAttribute("aria-label", t("micStart", loc));
    }
    setText("avatarTitle", "avatar", loc);
    setText("avatarModelLabel", "avatar", loc);
    setText("voiceFaceAgeLabel", "avatar", loc);
    setText("chatTitle", "chatTitle", loc);
    setText("faceAgeLabel", "portraitAge", loc);
    setText("metricsTitle", "metricsTitle", loc);
    setText("metricModelLabel", "metricModel", loc);
    setText("metricTtsLabel", "metricTts", loc);
    setText("metricAudioLabel", "metricAudio", loc);
    setText("statusBackendLabel", "statusBackend", loc);
    setText("statusVoiceLabel", "statusVoice", loc);
    setText("statusLipSyncLabel", "statusLipSync", loc);
    setText("helpTitle", "helpTitle", loc);

    const lipSync = document.getElementById("lipSyncStatus");
    if (lipSync) {
      lipSync.textContent = t("lipReady", loc);
    }
    const modelStat = document.getElementById("modelStatus");
    if (modelStat && modelStat.textContent.includes("…")) {
      modelStat.textContent = t("checking", loc);
    }

    const btnHealth = document.getElementById("btnHealth");
    if (btnHealth) {
      btnHealth.title = t("refreshStatus", loc);
      btnHealth.setAttribute("aria-label", t("refreshStatus", loc));
    }
    const btnClear = document.getElementById("btnClear");
    if (btnClear) {
      btnClear.title = t("clearChatTitle", loc);
    }

    const fileBanner = document.getElementById("fileProtocolBanner");
    if (fileBanner) {
      fileBanner.innerHTML = t("fileProtocol", loc).replace(
        "http://127.0.0.1:8000",
        "<code>http://127.0.0.1:8000</code>",
      );
    }

    const ageKeys = ["avatarMale", "avatarFemale"];
    const ageVals = ["male", "female"];
    document.querySelectorAll("#avatarGenderSegment [data-avatar-gender]").forEach((btn) => {
      const v = btn.getAttribute("data-avatar-gender");
      const idx = ageVals.indexOf(v);
      if (idx >= 0) {
        btn.textContent = t(ageKeys[idx], loc);
      }
    });

    const winMin = document.getElementById("btnWinMin");
    const winMax = document.getElementById("btnWinMax");
    const winClose = document.getElementById("btnWinClose");
    if (winMin) {
      winMin.title = t("winMinimize", loc);
      winMin.setAttribute("aria-label", t("winMinimize", loc));
    }
    if (winMax) {
      winMax.title = t("winMaximize", loc);
      winMax.setAttribute("aria-label", t("winMaximize", loc));
    }
    if (winClose) {
      winClose.title = t("winClose", loc);
      winClose.setAttribute("aria-label", t("winClose", loc));
    }

    return loc;
  }

  window.PersonaI18n = {
    t,
    currentLocale,
    applyStaticUi,
    themeLabel(themeId, locale) {
      return t(THEME_KEYS[themeId] || "themeBlue", locale);
    },
    THEME_IDS: Object.keys(THEME_KEYS),
  };
})();
