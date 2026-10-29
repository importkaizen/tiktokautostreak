# TikTok Streak Keeper

[![CI](https://github.com/importkaizen/tiktokautostreak/actions/workflows/ci.yml/badge.svg)](https://github.com/importkaizen/tiktokautostreak/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-0B6E4F.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-3776AB.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-555.svg)](#requirements)

Local, scheduled check-ins for [TikTok Web Messages](https://www.tiktok.com/messages). You pick the chats, you pick the message, and the helper sends that same short check-in once a day from **your own logged-in desktop browser**.

It never opens the For You feed. It is not a TikTok product, API client, or cloud service.

```text
config.json  →  Chrome session on this machine  →  Messages inbox  →  your chats
```

## Features

- One-command setup: private venv, Playwright, and Chromium
- Interactive `--login` that stores cookies under `~/.tiktok_streak_keeper/`
- Exact sidebar-name matching, including emoji
- Daily schedule on macOS (LaunchAgent), Linux (crontab), and Windows (Task Scheduler)
- Random startup delay so runs are not stamped to the same second
- Idempotent daily state: already-sent chats are skipped unless you pass `--force`
- `--status` for config, session, schedule, and last-run health

## Requirements

| Item | Detail |
| --- | --- |
| Python | 3.9 or newer |
| OS | macOS, Windows, or Linux |
| Browser | Desktop Chrome if installed; otherwise Playwright Chromium |
| Account | A TikTok account you can sign into in a desktop browser |

The first run that needs a browser creates `~/.tiktok_streak_keeper/venv` and installs Playwright for you. You do not need to manage that environment yourself.

## Quick start

```bash
git clone https://github.com/importkaizen/tiktokautostreak.git
cd tiktokautostreak
python3 tiktok_streak_keeper.py --init
```

Edit `config.json` with the **exact display names** from the TikTok Messages sidebar:

```json
{
  "targets": [
    "Friend One",
    "Friend Two",
    "Group Chat Name"
  ],
  "message": "🔥",
  "jitter_seconds": [45, 900]
}
```

Log in once, confirm the tool can see your setup, then send a test:

```bash
python3 tiktok_streak_keeper.py --login
python3 tiktok_streak_keeper.py --status
python3 tiktok_streak_keeper.py --now
```

`--login` opens a real Chrome/Chromium window. Sign in, complete any CAPTCHA or 2FA, wait until the inbox is visible, then press Enter in the terminal.

## Daily schedule

Default example: 2:30 PM local time, plus the random delay from `jitter_seconds`:

```bash
python3 tiktok_streak_keeper.py --install-schedule --hour 14 --minute 30
python3 tiktok_streak_keeper.py --status
```

| Platform | What gets installed |
| --- | --- |
| macOS | LaunchAgent at `~/Library/LaunchAgents/com.user.tiktok.streakkeeper.plist` |
| Linux | A marked line in the user crontab |
| Windows | Task Scheduler job `TikTokStreakKeeper` |

Remove it with:

```bash
python3 tiktok_streak_keeper.py --uninstall-schedule
```

The machine must be awake and able to show a browser window at run time. This is not a headless cloud worker.

## Commands

| Flag | What it does |
| --- | --- |
| `--init` | Create `config.json` from `config.example.json` |
| `--login` | Save a TikTok web session on this machine |
| `--status` | Print config, session, schedule, and last-run state |
| `--now` | Send today, skip the random startup wait |
| `--force` | Send even if today's run already succeeded |
| `--install-schedule` | Install the daily job |
| `--uninstall-schedule` | Remove the daily job |
| `--hour` / `--minute` | Schedule time (24-hour clock) |
| `--config PATH` | Use a different config file |
| `--version` | Print the tool version |
| `--help` | Show CLI help |

Logs: `~/.tiktok_streak_keeper/streak.log`

## Configuration

`config.json` is local and gitignored. Only `config.example.json` ships in the repo.

| Key | Required | Description |
| --- | --- | --- |
| `targets` | yes | Chat display names, copied from the Messages sidebar |
| `message` | yes | Text or emoji to send |
| `jitter_seconds` | no | `[min, max]` delay before a scheduled launch. Default `[45, 900]` |
| `data_dir` | no | Override the data directory. Default `~/.tiktok_streak_keeper` |

Names must match the sidebar, including emoji and special characters.

## Privacy

- Chat names live in your local `config.json`
- Login cookies live in `~/.tiktok_streak_keeper/chrome_profile/`
- Runtime state and logs stay in `~/.tiktok_streak_keeper/`
- Nothing in this repository is a hosted backend

Do not commit `config.json` or copy the Chrome profile into git.

## Troubleshooting

| Symptom | What to try |
| --- | --- |
| `Not logged in` | Re-run `--login` and wait until the inbox is visible |
| Chat not found | Copy the sidebar name exactly, including emoji |
| CAPTCHA or 2FA | Complete it in the opened window, then `--login` again |
| Schedule did not fire | Confirm `--status` shows the job, and that the machine was awake |
| TikTok UI changed | Selectors are best-effort. Re-run `--login`; if sends still fail, the site likely moved |

## Disclaimer

This project is unofficial and **not affiliated with, endorsed by, or supported by TikTok**. Automating the site in a browser may conflict with TikTok's terms of service. Use it only on an account you own, keep the recipient list small, and expect the site to change or block automation at any time.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 tiktok_streak_keeper.py --help
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the expected workflow.

## License

MIT. Copyright (c) 2026 importkaizen. See [LICENSE](LICENSE).
