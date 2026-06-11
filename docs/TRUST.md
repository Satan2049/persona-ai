# Trust and release verification

Download Persona AI only from official [GitHub Releases](https://github.com/Satan2049/persona-ai/releases).

Each release should include a **`SHA256.txt`** file listing cryptographic hashes of every binary and archive. Use it to confirm your download was not corrupted or tampered with in transit.

---

## 1. Verify SHA256 checksums

### Windows (PowerShell)

1. Download the release asset (for example `Persona AI_0.1.0_x64-setup.exe`) and `SHA256.txt`.
2. Open PowerShell in the download folder.
3. Compute the hash:

   ```powershell
   Get-FileHash -Algorithm SHA256 -Path ".\Persona AI_0.1.0_x64-setup.exe"
   ```

4. Open `SHA256.txt` and find the line for the same filename.
5. The `Hash` value from step 3 must **exactly match** the hash in `SHA256.txt` (case-insensitive).

### Linux / macOS

```bash
shasum -a 256 "Persona AI_0.1.0_x64-setup.exe"
# or
sha256sum "Persona AI_0.1.0_x64-setup.exe"
```

Compare the output with the corresponding line in `SHA256.txt`.

### Verify every asset

Repeat for each file you downloaded:

| Typical asset | Format |
|---------------|--------|
| NSIS installer | `.exe` |
| MSI installer | `.msi` |
| Portable zip | `.zip` |

If **any** hash mismatches, **do not run** the file. Delete it and re-download from the official release page.

---

## 2. Maintainer: generate checksums

From the repository root, after copying release files into `dist/release/`:

```powershell
.\scripts\generate-sha256.ps1 -ReleaseDir "dist\release"
```

Upload `SHA256.txt` alongside the release assets on GitHub.

---

## 3. Scan with VirusTotal (optional)

Windows installers and bundled executables may trigger heuristic warnings from antivirus tools because they are **not code-signed** or because they spawn a **Python sidecar** process. An independent scan can provide extra assurance.

1. Go to [VirusTotal](https://www.virustotal.com/).
2. Upload the **exact** file you downloaded (or submit its SHA256 hash).
3. Review the report. A small number of heuristic flags on unsigned niche software can be normal; widespread detections from many engines are a red flag.

### v0.1.0 — official VirusTotal reports

| Asset | SHA256 | Report |
|-------|--------|--------|
| MSI (`Persona AI_0.1.0_x64_en-US.msi`) | `a05ffacf2e24f92d6f351b56557b57a0aaf4ba1680b796f32bc040a2c7d0cd57` | [View on VirusTotal](https://www.virustotal.com/gui/file/a05ffacf2e24f92d6f351b56557b57a0aaf4ba1680b796f32bc040a2c7d0cd57) |
| NSIS setup (`Persona AI_0.1.0_x64-setup.exe`) | `01da3bb0a513c851a7a975a53c4dee3748b247ded5bac7518f00fd0469e18702` | [View on VirusTotal](https://www.virustotal.com/gui/file/01da3bb0a513c851a7a975a53c4dee3748b247ded5bac7518f00fd0469e18702) |

Both reports showed **no malicious detections** at the time of release.

---

## 4. What we do not bundle

Official releases **do not** include:

- LLM model weights (configure your own Ollama or API endpoint)
- Piper voice `.onnx` files (download separately; see [docs/piper-setup.md](piper-setup.md))
- API keys or `.env` secrets

The desktop app stores user configuration under `%APPDATA%\PersonaAI\` on Windows.

---

## 5. Report a security issue

See [SECURITY.md](../SECURITY.md) for responsible disclosure. **Do not** open public GitHub issues for unpatched vulnerabilities.
