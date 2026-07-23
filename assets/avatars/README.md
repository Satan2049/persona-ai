# Avatars

Runtime files are under `ui/avatars/` (what the app loads). Optional source copies may live under `assets/avatars/{gender}/` locally — large `.vrm` / `.glb` there are **gitignored** so they are not duplicated in the repo.

| Path | Role |
|------|------|
| `ui/avatars/catalog.json` | Registry: ids, gender defaults, file paths |
| `ui/avatars/female/Kira.vrm` | Default female (Kira) |
| `ui/avatars/male/Lucien.vrm` | Default male (Lucien) |
| `assets/avatars/catalog.json` | Same catalog (for docs / packaging helpers) |
| `apps/desktop/public/` | Synced from `ui/` by `scripts/sync-desktop-ui.ps1` (not committed) |

Formats: **`.vrm`** (preferred) or **`.glb`**.

## Add another avatar

1. Put the file in `ui/avatars/{gender}/` with a clear name — e.g. `ui/avatars/female/female1.glb`
2. Optionally keep a local copy under `assets/avatars/{gender}/` (ignored by git)
3. Register it in **both** `assets/avatars/catalog.json` and `ui/avatars/catalog.json`
4. Run `scripts/sync-desktop-ui.ps1` before desktop build/dev

Lip sync: Rhubarb shapes `A`–`H` / `X` → VRM expressions `aa` / `ih` / `ou` / `ee` / `oh` (or GLB morph aliases).
