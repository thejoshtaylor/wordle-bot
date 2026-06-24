# Emoji-grid formatting + iMessage sending (macOS, via osascript -> Messages.app).

import subprocess
import time

EMOJI = {"g": "\U0001F7E9", "y": "\U0001F7E8", "b": "⬛"}  # 🟩 🟨 ⬛


def emoji_grid(responses):
    return "\n".join("".join(EMOJI.get(c, "⬛") for c in row) for row in responses)


def share_text(result):
    n = result.get("puzzle_no")
    num = f"{n:,}" if isinstance(n, int) else "?"
    tries = result["attempts"] if result["solved"] else "X"
    star = "*" if result.get("hard_mode", True) else ""  # we always play Hard Mode
    return f"Wordle {num} {tries}/6{star}\n\n{emoji_grid(result['responses'])}"


def send_imessage(chat_id, text, retries=3):
    # Send `text` to a Messages chat by its id/GUID. Returns (ok, err).
    # ponytail: launch Messages + `with timeout` + retry — `chat id` lookup
    # is flaky and hangs (-1712) when the app isn't already responsive (e.g.
    # launchd firing at 9am on a freshly-woken machine).
    script = (
        'on run {chatId, msg}\n'
        '  tell application "Messages"\n'
        '    launch\n'
        '    with timeout of 30 seconds\n'
        '      send msg to chat id chatId\n'
        '    end timeout\n'
        '  end tell\n'
        'end run'
    )
    err = ""
    for attempt in range(retries):
        proc = subprocess.run(
            ["osascript", "-e", script, chat_id, text],
            capture_output=True, text=True,
        )
        if proc.returncode == 0:
            return True, ""
        err = proc.stderr.strip()
        if attempt < retries - 1:
            time.sleep(5)
    return False, err


if __name__ == "__main__":
    demo = {"solved": True, "attempts": 4, "puzzle_no": 1234,
            "responses": [["b","b","y","b","b"],["b","y","b","g","b"],
                          ["g","g","b","g","g"],["g","g","g","g","g"]]}
    print(share_text(demo))
