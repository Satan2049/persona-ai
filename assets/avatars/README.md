# Avatars

| Path | Role |
|------|------|
| `female/source/*.glb` | Source female GLB |
| `male/source/*.glb` | Source male GLB |
| `ui/avatars/female/avatar.glb` | Served female avatar |
| `ui/avatars/male/avatar.glb` | Served male avatar |

Textures are **embedded** in the GLB — no separate `textures/` folder is required.

Lip sync uses [Rhubarb](https://github.com/DanielSWolf/rhubarb-lip-sync) mouth shapes `A`–`H` / `X` mapped to Oculus/RPM visemes (`viseme_aa`, `viseme_E`, …) and ARKit mouth morphs.

## Replace a gender

1. Put the file at `assets/avatars/{gender}/source/YourAvatar.glb`
2. Copy to `ui/avatars/{gender}/avatar.glb`
3. Run `scripts/sync-desktop-ui.ps1` (or the Linux/macOS equivalent copy into `apps/desktop/public`)
