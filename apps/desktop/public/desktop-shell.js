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
  document.documentElement.classList.add("is-desktop");

  function tr(key) {
    if (window.PersonaI18n) {
      return window.PersonaI18n.t(key);
    }
    return key;
  }

  const titlebar = document.getElementById("desktopTitlebar");
  if (titlebar) {
    titlebar.classList.remove("hidden");
  }

  function tauriWindow() {
    const api = window.__TAURI__;
    if (!api || !api.window || typeof api.window.getCurrentWindow !== "function") {
      return null;
    }
    return api.window.getCurrentWindow();
  }

  function bindWindowChrome() {
    const win = tauriWindow();
    if (!win) {
      console.warn("Persona desktop: Tauri window API unavailable (withGlobalTauri?)");
      return;
    }

    document.getElementById("btnWinMin")?.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      win.minimize().catch(function () {});
    });

    const maxBtn = document.getElementById("btnWinMax");
    maxBtn?.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      win.toggleMaximize().catch(function () {});
    });

    document.getElementById("btnWinClose")?.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      win.close().catch(function () {});
    });

    const dragRegion = document.querySelector(".desktop-titlebar-drag");
    if (dragRegion && typeof win.startDragging === "function") {
      dragRegion.addEventListener("mousedown", (event) => {
        if (event.button !== 0) {
          return;
        }
        const target = event.target;
        if (target instanceof Element && target.closest("button,a,input,select,textarea")) {
          return;
        }
        event.preventDefault();
        win.startDragging().catch(function () {});
      });
    }

    document.addEventListener("keydown", async (event) => {
      if (event.key !== "F11") {
        return;
      }
      const tag = event.target && event.target.tagName;
      if (tag === "TEXTAREA" || tag === "INPUT") {
        return;
      }
      event.preventDefault();
      try {
        const full = await win.isFullscreen();
        await win.setFullscreen(!full);
      } catch (_e) {
        /* ignore */
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindWindowChrome);
  } else {
    bindWindowChrome();
  }

  let settled = false;
  let resolveReady;
  let rejectReady;
  const startupTimer = window.setTimeout(function () {
    finishErr(tr("sidecarTimeout"), "SIDECAR_TIMEOUT");
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
      if (ok === true) {
        pill.textContent = tr("pillOnline");
      } else if (ok === false) {
        pill.textContent = tr("pillOffline");
      } else {
        pill.textContent = tr("pillStarting");
      }
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
      badge.textContent = tr("badgeOffline");
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
    patchStatus(`${tr("connected")} · ${window.__PERSONA_API_BASE__}`, true);
  }

  function finishErr(message, code) {
    if (settled) {
      return;
    }
    settled = true;
    window.clearTimeout(startupTimer);
    const text = String(message);
    const err = new Error(text);
    if (code) {
      err.code = code;
    }
    rejectReady(err);
    patchStatus(text, false);
    if (window.__personaUpdateSetupHelp) {
      window.__personaUpdateSetupHelp("sidecar");
    }
  }

  window.__personaSetApiBase = finishOk;
  window.__personaStartupFailed = finishErr;

  function markStarting() {
    patchStatus(tr("startingBackend"), null);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", markStarting);
  } else {
    markStarting();
  }
})();
