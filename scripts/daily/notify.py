# Emoji-grid formatting + iMessage sending (macOS, via osascript -> Messages.app).

import subprocess

EMOJI = {"g": "\U0001F7E9", "y": "\U0001F7E8", "b": "⬛"}  # 🟩 🟨 ⬛


def emoji_grid(responses):
    return "\n".join("".join(EMOJI.get(c, "⬛") for c in row) for row in responses)


def share_text(result):
    n = result.get("puzzle_no")
    num = f"{n:,}" if isinstance(n, int) else "?"
    tries = result["attempts"] if result["solved"] else "X"
    star = "*" if result.get("hard_mode", True) else ""  # we always play Hard Mode
    return f"Wordle {num} {tries}/6{star}\n\n{emoji_grid(result['responses'])}"


def send_imessage(chat_id, text):
    # Send `text` to a Messages chat by its id/GUID. Returns (ok, err).
    script = (
        'on run {chatId, msg}\n'
        '  tell application "Messages"\n'
        '    set targetChat to chat id chatId\n'
        '    send msg to targetChat\n'
        '  end tell\n'
        'end run'
    )
    proc = subprocess.run(
        ["osascript", "-e", script, chat_id, text],
        capture_output=True, text=True,
    )
    return proc.returncode == 0, proc.stderr.strip()


if __name__ == "__main__":
    demo = {"solved": True, "attempts": 4, "puzzle_no": 1234,
            "responses": [["b","b","y","b","b"],["b","y","b","g","b"],
                          ["g","g","b","g","g"],["g","g","g","g","g"]]}
    print(share_text(demo))
