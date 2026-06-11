# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |
| < 0.1   | No        |

## Reporting a vulnerability

If you discover a security issue in Persona AI, please report it responsibly:

1. **Do not** open a public GitHub issue for exploitable vulnerabilities.
2. Email the maintainers with:
   - A clear description of the issue
   - Steps to reproduce
   - Impact assessment (if known)
   - Your environment (OS, app version, install method)
3. Allow reasonable time for a fix before public disclosure.

> **Contact:** Replace with your security email, e.g. `security@your-domain.example` or a GitHub private advisory on the repository **Security** tab.

We will acknowledge receipt within **5 business days** when possible and keep you informed of progress.

## Scope

In scope:

- Persona AI backend (`apps/backend/`)
- Desktop shell and sidecar (`apps/desktop/`)
- Bundled web UI (`ui/`)
- Official release artifacts published on GitHub Releases

Out of scope:

- Third-party services (Ollama, remote LLM APIs, Hugging Face downloads)
- Piper TTS binary and voice models obtained outside this repository
- Misconfiguration of `.env` or API keys on the user machine

## Safe usage reminders

- This project is a **research / demo assistant**. It does not replace professional mental-health care.
- Do not commit `apps/backend/.env` or API keys.
- Run downloads only from official releases and verify hashes per [docs/TRUST.md](docs/TRUST.md).
