# Daily Wordle auto-player

Plays the live [NYT Wordle](https://www.nytimes.com/games/wordle/) every morning in
real Chrome (Hard Mode, incognito), then shares the emoji grid to your iMessage group
chats. Opens with `lares` (top of the union word-ranking) and solves with the repo's
own solver (`wordle.find_words` + `main.get_best_word`).

## Files

| File | Purpose |
|------|---------|
| `run_daily.py` | Orchestrator: fetch puzzle # → play live → build grid → send |
| `play_nyt.py` | Drives Chrome on the NYT page, enables Hard Mode, reads tiles |
| `notify.py` | Emoji grid + `osascript` → Messages send |
| `list_chats.py` | Prints your iMessage chats + GUIDs |
| `config.example.json` | Template — copy to `config.json` (gitignored) |
| `run.sh` | launchd wrapper (venv + logging) |
| `com.josh.wordle-daily.plist` | launchd schedule (09:00 daily) |

`config.json`, `chrome-profile/`, and `logs/` are gitignored — they hold your chat
GUIDs and cookies. Never commit them.

## Setup

From the repo root:

```bash
# 1. venv + deps (Playwright uses your installed Google Chrome, no extra download)
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. config
cp scripts/daily/config.example.json scripts/daily/config.json
```

### 3. Get your group-chat GUIDs

Grant **Full Disk Access** to your terminal (System Settings → Privacy & Security →
Full Disk Access), then:

```bash
python scripts/daily/list_chats.py
```

Copy the two `any;+;chat…` GUIDs into `config.json` → `chat_ids`.

### 4. Approve Messages automation (once)

launchd can't answer the GUI permission prompt, so trigger it once manually:

```bash
python scripts/daily/run_daily.py        # real send — pops the Automation dialog; Allow it
```

### 5. Schedule it (launchd, 9am daily)

```bash
cp scripts/daily/com.josh.wordle-daily.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.josh.wordle-daily.plist
```

To stop: `launchctl unload ~/Library/LaunchAgents/com.josh.wordle-daily.plist`

> The Mac must be **logged in** at 9am (Chrome needs the GUI session). If it's asleep,
> launchd runs the job on the next wake.

## Running manually

```bash
python scripts/daily/run_daily.py            # play live + SEND to groups
python scripts/daily/run_daily.py --no-send  # play live, print only
python scripts/daily/run_daily.py --offline  # no browser; solve from NYT's answer JSON

launchctl start com.josh.wordle-daily        # trigger the scheduled job now
tail -f scripts/daily/logs/daily.log         # watch output
```

## Config knobs (`config.json`)

| Key | Default | Meaning |
|-----|---------|---------|
| `start_word` | `lares` | Opening guess |
| `incognito` | `true` | Fresh Chrome context each run (always a clean board) |
| `chat_ids` | — | iMessage group GUIDs to send to |
| `send_on_failure` | `false` | If unsolved (X/6), message the groups anyway |
| `error_notify` | `""` | Optional handle to ping on failure |

Hard Mode is always enabled (and the share text always gets the `*`).
