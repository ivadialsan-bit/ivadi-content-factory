# Content Factory OS 4.0 — Offline-first control plane

Experimental MVP; built for Amsterdam Timeweb VPS (Ubuntu 26.04, Python 3.14, 889 MiB RAM). Standard-library only. Not a finished end-to-end publisher.

## What's implemented

- 8 distinct agent role descriptions and system prompts, stored in `agents/roles.json` and SQLite.
- 30-day editorial calendar seeded once (no fabricated results or paid ad requirements).
- SQLite task pipeline: `waiting_for_model → draft → approved → scheduled → published`, errors, notes, unique publication ids.
- Local web panel at `127.0.0.1:8765` for viewing the plan, agents, creating topics, manual JSON import and approval, 8 editable SVG 1080×1350 slide previews and a ZIP export of assets.
- Prompt export for use in a ChatGPT chat with *manual copy-back* (not automatic remote control).
- Optional Workers AI text generation (requires a valid token with Workers AI Read access; uses Cloudflare free quota when available). Auto-generation does NOT run until credentials exist and CF_AUTO_GENERATE=1 is set. At most one scheduled package is automatically generated per UTC day.
- Optional Telegram sendMessage for *approved, scheduled* content only; `CF_AUTOPOST=0` by default and credentials are not part of this repository. Uncertain sends are quarantined to avoid repeated publication.
- Other social networks are planned integrations and require their own permissions; Instagram, VK, Dzen are not silently auto-published.

## Setup

On the **new Amsterdam VPS**, with root and network access:

```bash
curl -fsSL https://raw.githubusercontent.com/ivadialsan-bit/ivadi-content-factory/main/server_v4/install.sh -o /root/install-contentfactory-v4.sh
bash /root/install-contentfactory-v4.sh
```

Validate:
```bash
systemctl status contentfactory-v4 --no-pager
curl -fsS http://127.0.0.1:8765/api/status
```

The panel is intentionally not public. Configure a securely authenticated SSH tunnel / Cloudflare Access before making it reachable from phone or browser. NEVER expose localhost panel directly to the public Internet.

## Safety

- No OpenAI balance needed to establish agents, prompts, calendar, UI, approval pipeline, SQLite.
- ChatGPT Plus does not itself provide a server-side unattended inference API.
- The SVG slide templates are layout previews, not AI-generated photographs or fully production-ready PNG carousels.
- No shell/SSH command execution by the model; no speculative posting before review.
- Do not place secrets in GitHub or chat. `/etc/contentfactory-v4.env` is owner-root/group-service, permission 0640.
- Old RU server is not automatically migrated and must remain intact until backed up.
- Free Workers AI daily neurons are limited. Be mindful of quality; model output requires review.