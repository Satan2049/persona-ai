(function () {
  "use strict";

  const isTauri =
    window.__PERSONA_DESKTOP__ === true ||
    typeof window.__TAURI_INTERNALS__ !== "undefined" ||
    typeof window.__TAURI__ !== "undefined" ||
    window.location.protocol === "tauri:" ||
    /tauri\.localhost$/i.test(window.location.hostname);

  if (!isTauri) {
    return;
  }

  window.__PERSONA_DESKTOP__ = true;

  let settled = false;
  let resolveReady;
  let rejectReady;
  const startupTimer = window.setTimeout(function () {
    finishErr(
      "Backend startup timed out (30s). Check %APPDATA%\\PersonaAI\\logs\\desktop.log — rebuild: npm run sidecar:build",
    );
  }, 30000);

  window.__personaDesktopReady = new Promise(function (resolve, reject) {
    resolveReady = resolve;
    rejectReady = reject;
  });

  function patchStatus(text, ok) {
    const status = document.getElementById("backendStatus");
    if (status) {
      status.textContent = text;
    }
    const pill = document.getElementById("healthPill");
    if (pill) {
      pill.textContent = ok ? "Online" : ok === false ? "Offline" : "Starting";
      pill.classList.remove("pill-ok", "pill-warn", "pill-muted");
      if (ok === true) {
        pill.classList.add("pill-ok");
      } else if (ok === false) {
        pill.classList.add("pill-warn");
      } else {
        pill.classList.add("pill-muted");
      }
    }
    const badge = document.getElementById("modeBadge");
    if (badge && ok === false) {
      badge.textContent = "Offline";
    }
  }

  function finishOk(base) {
    if (settled) {
      return;
    }
    settled = true;
    window.clearTimeout(startupTimer);
    window.__PERSONA_API_BASE__ = String(base).replace(/\/$/, "");
    try {
      window.localStorage.removeItem("smartAvatarApiBase");
    } catch (_e) {
      /* ignore */
    }
    resolveReady(window.__PERSONA_API_BASE__);
    patchStatus("Connected · " + window.__PERSONA_API_BASE__, true);
  }

  function finishErr(message) {
    if (settled) {
      return;
    }
    settled = true;
    window.clearTimeout(startupTimer);
    const text = String(message);
    rejectReady(new Error(text));
    patchStatus(text, false);
  }

  window.__personaSetApiBase = finishOk;
  window.__personaStartupFailed = finishErr;

  function markStarting() {
    patchStatus("Starting local backend…", null);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", markStarting);
  } else {
    markStarting();
  }
})();
