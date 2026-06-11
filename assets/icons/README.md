# Persona AI icons

| File | Use |
|------|-----|
| `app-icon.svg` | Master vector (256 viewBox) — README logo, splash screen |
| `app-icon-1024.png` | Raster master for `tauri icon` (auto-exported from the SVG) |

## Regenerate desktop / title-bar icons

After editing `app-icon.svg`:

```powershell
.\scripts\prepare-desktop-icons.ps1
cd apps\desktop
npm run sidecar:build
npm run build
```

`npm run build` runs `prebuild` automatically (icons + cache clear). If Explorer still shows the old icon, restart Explorer or clear the Windows icon cache.

Use Python **3.10–3.12** for the sidecar build (`pydantic` wheels are unreliable on 3.14).
