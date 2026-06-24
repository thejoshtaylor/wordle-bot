# Daily orchestrator: play the live NYT Wordle, then share the emoji grid to the
# configured iMessage group chats.
#
# Usage:
#   python scripts/daily/run_daily.py            # play live + send
#   python scripts/daily/run_daily.py --no-send  # play live, print only (test selectors)
#   python scripts/daily/run_daily.py --offline  # solve today's word from NYT JSON, no browser

import argparse
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

import wordle
import main as solver
sys.path.insert(0, HERE)
import notify  # scripts/daily/notify.py


def load_config():
    return json.load(open(os.path.join(HERE, "config.json")))


def fetch_puzzle(date=None):
    # NYT's public daily endpoint: {solution, days_since_launch, print_date, ...}
    date = date or time.strftime("%Y-%m-%d")
    url = f"https://www.nytimes.com/svc/wordle/v2/{date}.json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def solve_offline(answer, start_word):
    # Simulate the solver against a known answer (no browser).
    guess, temp_dict = start_word, None
    guesses, responses = [], []
    for _ in range(6):
        resp = ["g" if guess[i] == answer[i] else "" for i in range(5)]
        # full check_guess gives proper yellows:
        resp = [{"g": "g", "y": "y", " ": "b"}[c] for c in wordle.check_guess(answer, guess)]
        guesses.append(guess)
        responses.append(resp)
        if all(r == "g" for r in resp):
            return {"solved": True, "attempts": len(guesses), "guesses": guesses,
                    "responses": responses, "answer": answer}
        temp_dict = wordle.find_words(guess, resp, temp_dict)
        if not temp_dict:
            break
        guess = solver.get_best_word(temp_dict)
    return {"solved": False, "attempts": len(guesses), "guesses": guesses,
            "responses": responses, "answer": answer}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-send", action="store_true", help="play live but don't send")
    ap.add_argument("--offline", action="store_true", help="no browser; solve from NYT JSON")
    args = ap.parse_args()

    cfg = load_config()
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")

    # puzzle number / answer (best-effort)
    puzzle_no, answer = None, None
    try:
        pj = fetch_puzzle()
        puzzle_no = pj.get("days_since_launch")
        answer = pj.get("solution")
    except Exception as e:
        print(f"[{stamp}] puzzle fetch failed: {e}")

    if args.offline:
        if not answer:
            print("offline mode needs the NYT answer; fetch failed. Abort.")
            return 2
        result = solve_offline(answer, cfg.get("start_word", "lares"))
    else:
        import play_nyt
        result = play_nyt.play(cfg)

    result["puzzle_no"] = puzzle_no
    result.setdefault("answer", answer)

    text = notify.share_text(result)
    print(f"[{stamp}] solved={result['solved']} attempts={result['attempts']} answer={result.get('answer')}")
    print(text)

    if args.no_send:
        return 0

    if not result["solved"] and not cfg.get("send_on_failure", False):
        print("Not solved and send_on_failure=false -> not messaging groups.")
        # optional self-notify
        if cfg.get("error_notify"):
            notify.send_imessage(cfg["error_notify"], f"Wordle bot failed to solve {puzzle_no} on {stamp}")
        return 1

    ok_all = True
    for chat in cfg.get("chat_ids", []):
        if chat.startswith("PUT_GROUP"):
            print(f"skip placeholder chat id: {chat}")
            ok_all = False
            continue
        ok, err = notify.send_imessage(chat, text)
        print(f"send -> {chat}: {'ok' if ok else 'FAIL ' + err}")
        ok_all = ok_all and ok
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
