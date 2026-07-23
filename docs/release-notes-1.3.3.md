# Persona AI 1.3.3 — release notes

**Tag:** `v1.3.3` · **Date:** 2026-07-23

Download from [GitHub Releases](https://github.com/Satan2049/persona-ai/releases/tag/v1.3.3). Verify checksums with [TRUST.md](TRUST.md) and the `SHA256*.txt` files attached to the release.

---

## Highlights

- **Named VRM avatars** — `Kira` (female) and `Lucien` (male) via `ui/avatars/catalog.json`; facing-camera and larger stage in chat + voice UI
- **Purple brand default** — app icon / theme aligned with the Lucien portrait mark
- **Safer contact policy** — removed `RESEARCHER_NUMBER`; escalation uses social emergency only
- **Quieter desktop** — Windows no longer flashes a console when `ffmpeg` / Rhubarb run for STT / lip-sync
- **Fresh media** — screenshots and preview GIF under `assets/media/`
- **CI releases** — Linux (AppImage / deb) and macOS (DMG) workflows upload artifacts + SHA256 on `v*` tags

---

## Assets

| Platform | File (typical) | Notes |
|----------|----------------|--------|
| Windows | `Persona AI_1.3.3_x64-setup.exe` | NSIS installer (maintainer upload) |
| Linux | AppImage + `.deb` | Uploaded by `desktop-linux.yml` |
| macOS | `Persona AI_1.3.3_aarch64.dmg` | Uploaded by `desktop-macos.yml` (Apple Silicon runner) |
| Checksums | `SHA256.txt` / `SHA256-linux.txt` / `SHA256-macos.txt` | See [TRUST.md](TRUST.md) |

---

## VirusTotal (Windows NSIS)

Scan of the official NSIS installer — **no malicious detections** at publish time:

| Asset | SHA256 | Report |
|-------|--------|--------|
| NSIS setup (`Persona AI_1.3.3_x64-setup.exe`) | `f0546756725c726f97d3202a44aa1aebf85125b3a28ac09c50e7bcb3afc6441a` | [VirusTotal (clean)](https://www.virustotal.com/gui/file/f0546756725c726f97d3202a44aa1aebf85125b3a28ac09c50e7bcb3afc6441a?nocache=1) |

---

## Upgrade notes

1. Replace any previous desktop build; clear `%APPDATA%\PersonaAI\.env` only if you still have a stale `RESEARCHER_NUMBER` line (optional — ignored by the app).
2. Rebuild the Windows sidecar (`npm run sidecar:build`) before `npm run desktop:build` so `app.win_process` is bundled.
3. Confirm `/health` reports TTS / STT / Rhubarb as expected after first launch.

---

## Full changelog

See [CHANGELOG.md](../CHANGELOG.md) entry **[1.3.3]**.
