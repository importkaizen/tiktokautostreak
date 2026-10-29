#!/usr/bin/env python3
"""
TikTok Streak Keeper
====================
Sends the same daily check-in message to chats you list in config.json,
using TikTok Web Messages (no For You feed).

  python3 tiktok_streak_keeper.py --init
  python3 tiktok_streak_keeper.py --login
  python3 tiktok_streak_keeper.py --now
  python3 tiktok_streak_keeper.py --status
  python3 tiktok_streak_keeper.py --install-schedule --hour 14 --minute 30
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import plistlib
import random
import subprocess
import sys
import time
import venv
from pathlib import Path
from typing import Any, Dict, List

__version__ = "1.0.0"

SCRIPT_DIR = Path(__file__).resolve().parent
EXAMPLE_CONFIG = SCRIPT_DIR / "config.example.json"
DEFAULT_DATA_DIR = Path.home() / ".tiktok_streak_keeper"
MESSAGES_URL = "https://www.tiktok.com/messages"
PLACEHOLDER_TARGETS = {
    "exact display name from tiktok messages",
    "another friend or group chat",
    "friend one",
    "friend two",
    "group chat name",
}

LAUNCHD_LABEL = "com.user.tiktok.streakkeeper"
LAUNCHD_PLIST = Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"
CRON_MARKER = "# tiktok-streak-keeper"
WINDOWS_TASK_NAME = "TikTokStreakKeeper"

# Filled in after config is loaded
DATA_DIR = DEFAULT_DATA_DIR
VENV_DIR = DATA_DIR / "venv"
PROFILE_DIR = DATA_DIR / "chrome_profile"
STATE_FILE = DATA_DIR / "streak_state.json"
LOG_FILE = DATA_DIR / "streak.log"


def apply_data_dir(path: Path) -> None:
    global DATA_DIR, VENV_DIR, PROFILE_DIR, STATE_FILE, LOG_FILE
    DATA_DIR = path
    VENV_DIR = DATA_DIR / "venv"
    PROFILE_DIR = DATA_DIR / "chrome_profile"
    STATE_FILE = DATA_DIR / "streak_state.json"
    LOG_FILE = DATA_DIR / "streak.log"


def log(msg: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def venv_python_path() -> Path:
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def venv_pip_path() -> Path:
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "pip.exe"
    return VENV_DIR / "bin" / "pip"


def ensure_playwright_venv() -> None:
    try:
        import playwright  # noqa: F401
        return
    except ImportError:
        pass

    python_bin = venv_python_path()
    pip_bin = venv_pip_path()

    if not python_bin.exists():
        log(f"Creating virtual environment at {VENV_DIR}...")
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        venv.create(str(VENV_DIR), with_pip=True)

    check = subprocess.run(
        [str(python_bin), "-c", "import playwright"],
        capture_output=True,
    )
    if check.returncode != 0:
        log("Installing Playwright (one-time setup)...")
        subprocess.run([str(pip_bin), "install", "--upgrade", "pip", "playwright"], check=True)
        log("Downloading Playwright Chromium...")
        subprocess.run([str(python_bin), "-m", "playwright", "install", "chromium"], check=True)

    os.execv(str(python_bin), [str(python_bin), str(Path(__file__).resolve()), *sys.argv[1:]])


def notify(title: str, message: str) -> None:
    if sys.platform != "darwin":
        return
    safe_title = title.replace('"', '\\"')
    safe_message = message.replace('"', '\\"')
    script = f'display notification "{safe_message}" with title "{safe_title}"'
    try:
        subprocess.run(["osascript", "-e", script], check=False, capture_output=True)
    except Exception:
        pass


def default_config_path() -> Path:
    local = SCRIPT_DIR / "config.json"
    if local.exists():
        return local
    home = DEFAULT_DATA_DIR / "config.json"
    if home.exists():
        return home
    return local


def init_config(dest: Path) -> int:
    if dest.exists():
        log(f"Config already exists: {dest}")
        return 0
    if not EXAMPLE_CONFIG.exists():
        log(f"Missing example config: {EXAMPLE_CONFIG}")
        return 1
    dest.write_text(EXAMPLE_CONFIG.read_text(encoding="utf-8"), encoding="utf-8")
    log(f"Created {dest}")
    log("Edit that file with the exact chat names from your TikTok Messages sidebar.")
    return 0


def load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        log(f"No config found at {path}")
        log("Run: python3 tiktok_streak_keeper.py --init")
        raise SystemExit(1)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        log(f"Invalid JSON in {path}: {exc}")
        raise SystemExit(1)

    targets = [str(t).strip() for t in data.get("targets", []) if str(t).strip()]
    message = str(data.get("message", "")).strip()
    if not targets:
        log("config.json has no targets. Add at least one chat display name.")
        raise SystemExit(1)
    if not message:
        log("config.json is missing a non-empty \"message\".")
        raise SystemExit(1)

    placeholders = [t for t in targets if t.lower() in PLACEHOLDER_TARGETS]
    if placeholders:
        log(f"{path} still has example placeholder names: {placeholders}")
        log("Put the exact TikTok Messages sidebar names in the \"targets\" list.")
        raise SystemExit(1)

    data_dir = data.get("data_dir")
    apply_data_dir(Path(data_dir).expanduser() if data_dir else DEFAULT_DATA_DIR)

    jitter = data.get("jitter_seconds", [45, 900])
    if not (isinstance(jitter, list) and len(jitter) == 2):
        jitter = [45, 900]

    return {
        "targets": targets,
        "message": message,
        "jitter_seconds": (int(jitter[0]), int(jitter[1])),
    }


def load_today_state() -> Dict[str, bool]:
    today = datetime.date.today().isoformat()
    if not STATE_FILE.exists():
        return {}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if data.get("date") == today:
            return data.get("completed", {})
    except Exception:
        pass
    return {}


def save_today_state(completed: Dict[str, bool]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "date": datetime.date.today().isoformat(),
        "completed": completed,
        "updated_at": datetime.datetime.now().isoformat(),
    }
    STATE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def open_browser_context(playwright):
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    browser_args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--window-size=1100,820",
    ]
    try:
        return playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=False,
            args=browser_args,
            viewport={"width": 1100, "height": 820},
        )
    except Exception:
        return playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            args=browser_args,
            viewport={"width": 1100, "height": 820},
        )


def run_interactive_login() -> None:
    ensure_playwright_venv()
    from playwright.sync_api import sync_playwright

    log("Starting interactive login session...")
    with sync_playwright() as p:
        context = open_browser_context(p)
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(MESSAGES_URL, wait_until="domcontentloaded")

        print("\n" + "=" * 68)
        print("1. Log into TikTok in the opened browser window.")
        print("2. Finish any CAPTCHA or 2FA until your Messages inbox is visible.")
        print("3. Copy the exact sidebar names into config.json if you have not yet.")
        print("4. Return here and press ENTER to save the session.")
        print("=" * 68 + "\n")
        input("Press ENTER once your TikTok Messages inbox is visible... ")
        context.close()
    log(f"Login session saved to {PROFILE_DIR}")


def send_message_to_chat(page, target_name: str, message_text: str) -> bool:
    log(f"Looking for chat: '{target_name}'...")
    time.sleep(random.uniform(2.0, 3.5))

    chat_locator = page.locator('[data-e2e="chat-list-item"]').filter(has_text=target_name)
    if chat_locator.count() == 0:
        chat_locator = page.get_by_text(target_name, exact=False)

    if chat_locator.count() == 0:
        log(f"WARNING: Could not find '{target_name}' in the Messages sidebar.")
        return False

    chat_locator.first.scroll_into_view_if_needed()
    time.sleep(random.uniform(0.6, 1.4))
    chat_locator.first.click()
    time.sleep(random.uniform(1.8, 3.0))

    input_selectors = [
        '[data-e2e="message-input-area"] [contenteditable="true"]',
        'div[contenteditable="true"][role="textbox"]',
        'div[contenteditable="true"]',
        'textarea[placeholder*="Send a message" i]',
    ]

    composer = None
    for sel in input_selectors:
        loc = page.locator(sel)
        if loc.count() > 0 and loc.first.is_visible():
            composer = loc.first
            break

    if composer is None:
        log(f"WARNING: Could not find message input box for '{target_name}'.")
        return False

    composer.click()
    time.sleep(random.uniform(0.5, 1.1))

    for ch in message_text:
        page.keyboard.type(ch, delay=random.randint(65, 145))
    time.sleep(random.uniform(0.4, 0.9))
    page.keyboard.press("Enter")

    time.sleep(random.uniform(2.2, 3.8))
    log(f"Sent '{message_text}' to '{target_name}'.")
    return True


def run_daily_streaks(config: Dict[str, Any], skip_jitter: bool = False, force: bool = False) -> int:
    ensure_playwright_venv()
    from playwright.sync_api import sync_playwright

    targets: List[str] = config["targets"]
    message: str = config["message"]
    jitter_lo, jitter_hi = config["jitter_seconds"]

    completed = {} if force else load_today_state()
    pending = [t for t in targets if not completed.get(t)]

    if not pending:
        log(f"All {len(targets)} chat(s) already received today's message. Skipping.")
        return 0

    if not skip_jitter:
        wait_seconds = random.randint(max(0, jitter_lo), max(jitter_lo, jitter_hi))
        log(f"Waiting {wait_seconds}s before launching the browser...")
        time.sleep(wait_seconds)

    log(f"Launching browser for {len(pending)} pending chat(s).")
    with sync_playwright() as p:
        context = open_browser_context(p)
        page = context.pages[0] if context.pages else context.new_page()

        try:
            page.goto(MESSAGES_URL, wait_until="domcontentloaded", timeout=45000)
            time.sleep(random.uniform(4.5, 6.5))

            if "/login" in page.url.lower():
                log("Not logged in. Run with --login first.")
                notify("TikTok Streak Keeper", "Login required. Run with --login.")
                context.close()
                return 2

            random.shuffle(pending)

            for target in pending:
                ok = send_message_to_chat(page, target, message)
                if ok:
                    completed[target] = True
                    save_today_state(completed)
                time.sleep(random.uniform(1.5, 3.2))

        finally:
            context.close()

    still_missing = [t for t in targets if not completed.get(t)]
    if still_missing:
        log(f"Finished with incomplete chats: {still_missing}")
        notify("TikTok Streak Warning", f"Could not message: {', '.join(still_missing)}")
        return 3

    log(f"Sent today's message to all {len(targets)} chat(s).")
    notify("TikTok Streaks Maintained", f"Sent messages to {len(targets)} chat(s).")
    return 0


def scheduled_command() -> List[str]:
    return [str(venv_python_path() if venv_python_path().exists() else Path(sys.executable)), str(Path(__file__).resolve())]


def install_launchd_schedule(hour: int, minute: int) -> None:
    python_bin, script_path = scheduled_command()
    plist_content = {
        "Label": LAUNCHD_LABEL,
        "ProgramArguments": [python_bin, script_path],
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "RunAtLoad": False,
        "StandardOutPath": str(DATA_DIR / "launchd.out.log"),
        "StandardErrorPath": str(DATA_DIR / "launchd.err.log"),
        "EnvironmentVariables": {
            "PATH": os.environ.get("PATH", "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"),
        },
    }
    LAUNCHD_PLIST.parent.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(LAUNCHD_PLIST, "wb") as f:
        plistlib.dump(plist_content, f)
    subprocess.run(["launchctl", "unload", str(LAUNCHD_PLIST)], check=False, capture_output=True)
    res = subprocess.run(["launchctl", "load", str(LAUNCHD_PLIST)], check=False, capture_output=True, text=True)
    if res.returncode == 0:
        log(f"Installed macOS LaunchAgent at {LAUNCHD_PLIST}")
    else:
        log(f"Saved plist to {LAUNCHD_PLIST}, but launchctl returned: {res.stderr.strip()}")


def uninstall_launchd_schedule() -> None:
    if LAUNCHD_PLIST.exists():
        subprocess.run(["launchctl", "unload", str(LAUNCHD_PLIST)], check=False, capture_output=True)
        LAUNCHD_PLIST.unlink()
        log(f"Removed LaunchAgent {LAUNCHD_PLIST}")
    else:
        log("No LaunchAgent plist found to remove.")


def crontab_line(hour: int, minute: int) -> str:
    python_bin, script_path = scheduled_command()
    return f"{minute} {hour} * * * {python_bin} {script_path} {CRON_MARKER}"


def current_crontab() -> str:
    res = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if res.returncode != 0:
        return ""
    return res.stdout


def install_cron_schedule(hour: int, minute: int) -> None:
    existing = current_crontab()
    lines = [ln for ln in existing.splitlines() if CRON_MARKER not in ln]
    lines.append(crontab_line(hour, minute))
    text = "\n".join(lines).rstrip() + "\n"
    subprocess.run(["crontab", "-"], input=text, text=True, check=True)
    log(f"Installed user crontab entry for {hour:02d}:{minute:02d}.")


def uninstall_cron_schedule() -> None:
    existing = current_crontab()
    kept = [ln for ln in existing.splitlines() if CRON_MARKER not in ln]
    if kept == existing.splitlines():
        log("No crontab entry found to remove.")
        return
    text = ("\n".join(kept).rstrip() + "\n") if kept else ""
    subprocess.run(["crontab", "-"], input=text, text=True, check=True)
    log("Removed crontab entry.")


def install_windows_schedule(hour: int, minute: int) -> None:
    python_bin, script_path = scheduled_command()
    time_str = f"{hour:02d}:{minute:02d}"
    cmd = [
        "schtasks",
        "/Create",
        "/F",
        "/TN",
        WINDOWS_TASK_NAME,
        "/SC",
        "DAILY",
        "/ST",
        time_str,
        "/TR",
        f'"{python_bin}" "{script_path}"',
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        log(f"Installed Windows Task Scheduler job '{WINDOWS_TASK_NAME}' at {time_str}.")
    else:
        log(f"Could not install scheduled task: {res.stderr.strip() or res.stdout.strip()}")


def uninstall_windows_schedule() -> None:
    res = subprocess.run(
        ["schtasks", "/Delete", "/F", "/TN", WINDOWS_TASK_NAME],
        capture_output=True,
        text=True,
    )
    if res.returncode == 0:
        log(f"Removed Windows task '{WINDOWS_TASK_NAME}'.")
    else:
        log("No Windows scheduled task found to remove.")


def install_schedule(hour: int, minute: int) -> int:
    ensure_playwright_venv()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if sys.platform == "darwin":
        install_launchd_schedule(hour, minute)
    elif sys.platform == "win32":
        install_windows_schedule(hour, minute)
    else:
        install_cron_schedule(hour, minute)
    log(f"Scheduled daily run at {hour:02d}:{minute:02d} (plus optional random delay from config).")
    notify("TikTok Streak Keeper", f"Scheduled daily at {hour:02d}:{minute:02d}")
    return 0


def uninstall_schedule() -> int:
    if sys.platform == "darwin":
        uninstall_launchd_schedule()
    elif sys.platform == "win32":
        uninstall_windows_schedule()
    else:
        uninstall_cron_schedule()
    return 0


def _exists_label(path: Path) -> str:
    return "yes" if path.exists() else "no"


def schedule_status() -> str:
    if sys.platform == "darwin":
        if not LAUNCHD_PLIST.exists():
            return "not installed"
        try:
            with open(LAUNCHD_PLIST, "rb") as f:
                data = plistlib.load(f)
            interval = data.get("StartCalendarInterval") or {}
            hour = interval.get("Hour")
            minute = interval.get("Minute")
            if hour is not None and minute is not None:
                return f"LaunchAgent at {int(hour):02d}:{int(minute):02d}"
        except Exception:
            pass
        return f"LaunchAgent ({LAUNCHD_PLIST})"
    if sys.platform == "win32":
        res = subprocess.run(
            ["schtasks", "/Query", "/TN", WINDOWS_TASK_NAME],
            capture_output=True,
            text=True,
        )
        return "Task Scheduler job installed" if res.returncode == 0 else "not installed"
    existing = current_crontab()
    for line in existing.splitlines():
        if CRON_MARKER in line:
            return f"crontab: {line.replace(CRON_MARKER, '').strip()}"
    return "not installed"


def print_status(config_path: Path) -> int:
    print(f"TikTok Streak Keeper {__version__}")
    print(f"{'Config':<12} {config_path} ({'found' if config_path.exists() else 'missing'})")

    targets: List[str] = []
    if config_path.exists():
        try:
            cfg = load_config(config_path)
            targets = cfg["targets"]
            print(f"{'Chats':<12} {len(targets)} configured")
            print(f"{'Message':<12} {cfg['message']}")
            lo, hi = cfg["jitter_seconds"]
            print(f"{'Jitter':<12} {lo}-{hi}s")
        except SystemExit:
            print(f"{'Config':<12} present, but invalid — run --init or fix JSON")
    else:
        apply_data_dir(DEFAULT_DATA_DIR)
        print(f"{'Chats':<12} none (run --init)")

    print(f"{'Data dir':<12} {DATA_DIR}")
    print(f"{'Session':<12} {_exists_label(PROFILE_DIR)}")
    print(f"{'Playwright':<12} {_exists_label(venv_python_path())}")
    print(f"{'Schedule':<12} {schedule_status()}")

    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            completed = state.get("completed") or {}
            done = sum(1 for ok in completed.values() if ok)
            total = len(targets) if targets else len(completed)
            print(f"{'Last run':<12} {state.get('date', 'unknown')} ({done}/{total} chats)")
            print(f"{'Updated':<12} {state.get('updated_at', 'unknown')}")
        except Exception:
            print(f"{'Last run':<12} unreadable ({STATE_FILE})")
    else:
        print(f"{'Last run':<12} none")

    print(f"{'Log':<12} {LOG_FILE}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="tiktok_streak_keeper.py",
        description="Send a daily TikTok Messages check-in to chats you list in config.json.",
        epilog="Not affiliated with TikTok. Session cookies stay on this machine.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"TikTok Streak Keeper {__version__}")
    parser.add_argument("--init", action="store_true", help="Create config.json from the example file")
    parser.add_argument("--login", action="store_true", help="Open a browser to log in and save the session")
    parser.add_argument("--now", action="store_true", help="Run immediately without the random startup wait")
    parser.add_argument("--force", action="store_true", help="Send even if today's run already succeeded")
    parser.add_argument("--status", action="store_true", help="Print config, session, schedule, and last-run state")
    parser.add_argument("--install-schedule", action="store_true", help="Install the daily scheduled job")
    parser.add_argument("--uninstall-schedule", action="store_true", help="Remove the daily scheduled job")
    parser.add_argument("--hour", type=int, default=14, help="Hour (0-23) for the daily schedule")
    parser.add_argument("--minute", type=int, default=30, help="Minute (0-59) for the daily schedule")
    parser.add_argument("--config", type=Path, default=None, help="Path to config.json")
    args = parser.parse_args()

    if args.init:
        dest = args.config if args.config else SCRIPT_DIR / "config.json"
        return init_config(dest)

    if args.uninstall_schedule:
        apply_data_dir(DEFAULT_DATA_DIR)
        return uninstall_schedule()

    config_path = args.config if args.config else default_config_path()

    if args.status:
        return print_status(config_path)

    if args.login:
        if config_path.exists():
            load_config(config_path)
        else:
            apply_data_dir(DEFAULT_DATA_DIR)
        run_interactive_login()
        return 0

    if args.install_schedule:
        if not (0 <= args.hour <= 23 and 0 <= args.minute <= 59):
            log("Hour must be 0-23 and minute must be 0-59.")
            return 1
        if config_path.exists():
            load_config(config_path)
        else:
            apply_data_dir(DEFAULT_DATA_DIR)
        return install_schedule(args.hour, args.minute)

    config = load_config(config_path)
    return run_daily_streaks(config, skip_jitter=args.now, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
