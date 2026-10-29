# TikTok Streak Keeper

A small local helper that opens [TikTok Web Messages](https://www.tiktok.com/messages), sends the same short check-in to chats you choose, and can run once a day.

It uses **your own logged-in browser session** on your computer. It does not load the For You feed.

## Requirements

- Python 3.9+
- macOS, Windows, or Linux
- A TikTok account you can log into in a desktop browser

The first run creates a private virtual environment and installs Playwright + Chromium for you.

## Quick start

```bash
git clone https://github.com/importkaizen/tiktokautostreak.git
cd tiktok-streak-keeper
python3 tiktok_streak_keeper.py --init
```

Edit `config.json` and put the **exact display names** from your TikTok Messages sidebar:

```json
{
  "targets": [
    "Friend One",
    "Friend Two",
    "Group Chat Name"
  ],
  "message": "🔥"
}
```

Then log in once and send a test:

```bash
python3 tiktok_streak_keeper.py --login
python3 tiktok_streak_keeper.py --now
```

`--login` opens a real Chrome/Chromium window. Sign in, wait until your inbox is visible, then press Enter in the terminal. The session is stored under `~/.tiktok_streak_keeper/` (not in this repo).

## Daily schedule

Run at 2:30 PM local time (plus a random delay of up to 15 minutes, so it does not fire at the same second every day):

```bash
python3 tiktok_streak_keeper.py --install-schedule --hour 14 --minute 30
```

- **macOS:** LaunchAgent (`~/Library/LaunchAgents/`)
- **Linux:** user crontab
- **Windows:** Task Scheduler

Remove it with:

```bash
python3 tiktok_streak_keeper.py --uninstall-schedule
```

## Commands

| Flag | What it does |
| --- | --- |
| `--init` | Create `config.json` from the example |
| `--login` | Save a TikTok web session |
| `--now` | Send today, skip the random startup wait |
| `--force` | Send even if today's run already succeeded |
| `--install-schedule` | Install the daily job |
| `--uninstall-schedule` | Remove the daily job |
| `--hour` / `--minute` | Schedule time (24-hour clock) |
| `--config PATH` | Use a different config file |

Logs: `~/.tiktok_streak_keeper/streak.log`

## Privacy

Do **not** commit `config.json`. Chat names stay on your machine. Login cookies live in `~/.tiktok_streak_keeper/chrome_profile/`.

This public repo only ships `config.example.json` with placeholders.

## Notes

- Names must match the sidebar, including emoji and special characters.
- TikTok may show a CAPTCHA or ask you to log in again. Re-run `--login` if that happens.
- Automating TikTok in a browser may conflict with TikTok's terms of service. Use this only on your own account, keep the recipient list small, and accept that the site can change or block it at any time.

## License

MIT. See [LICENSE](LICENSE).
