# Contributing

Thanks for helping keep this tool reliable.

## Local checks

```bash
python3 -m py_compile tiktok_streak_keeper.py
PYTHONPATH=. python3 -m unittest discover -s tests -v
python3 tiktok_streak_keeper.py --help
```

Do not commit `config.json`, Chrome profiles, or anything under `~/.tiktok_streak_keeper/`.

## Pull requests

- Keep the CLI stable unless the README is updated in the same change
- Prefer small, reviewable diffs
- Add a regression test when you change config parsing or status output
- Note user-facing changes in `CHANGELOG.md`

## Scope

This project talks to TikTok through a real desktop browser session. Please do not add unofficial API clients, credential harvesting, bulk-messaging features, or anything that sends to chats the operator did not list in `config.json`.
