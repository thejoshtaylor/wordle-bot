# Plays the live NYT Wordle in real Chrome (persistent profile, non-headless) and
# returns the result. Uses the repo solver (wordle.find_words + main.get_best_word).
#
# Returns dict: {solved, attempts, guesses:[...], responses:[[g/y/b]*5,...],
#                puzzle_no, answer, date}.

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import wordle  # find_words
import main as solver  # get_best_word

URL = "https://www.nytimes.com/games/wordle/index.html"
STATE_TO_CH = {"correct": "g", "present": "y", "absent": "b"}

# JS that reads the 6x5 board tiles, scoped to the board so the how-to modal's
# example tiles don't leak in.
READ_BOARD_JS = """
() => {
  let board = document.querySelector('[class*="Board-module_board"]')
           || document.querySelector('[class*="Board"]');
  const root = board || document;
  const tiles = [...root.querySelectorAll('div[data-state]')].slice(0, 30);
  return tiles.map(t => t.getAttribute('data-state'));
}
"""


def _click_if_visible(page, sel, timeout=1000):
    try:
        el = page.locator(sel).first
        if el.is_visible(timeout=timeout):
            el.click(timeout=timeout)
            page.wait_for_timeout(300)
            return True
    except Exception:
        pass
    return False


def _open_game(page):
    # Optional GDPR/consent.
    for sel in ['button[data-testid="GDPR-accept"]', 'button:has-text("Accept all")',
                'button:has-text("Reject")']:
        if _click_if_visible(page, sel, 600):
            break
    # Splash -> Play.
    _click_if_visible(page, 'button[data-testid="Play"]', 4000)
    _click_if_visible(page, 'button:has-text("Play")', 1500)
    page.wait_for_timeout(600)
    # Close the How-To-Play / stats modal (X), with Escape as fallback.
    for sel in ['button[aria-label="Close"]', 'svg[data-testid="icon-close"]',
                'button[class*="closeIcon"]', '[class*="Modal"] button[aria-label="Close"]']:
        _click_if_visible(page, sel, 800)
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)


def _enable_hard_mode(page):
    # Must be done before the first guess (NYT locks the toggle once you've guessed).
    if not _click_if_visible(page, 'button[aria-label="Settings"]', 3000):
        raise RuntimeError("could not open Settings to enable Hard Mode")
    page.wait_for_timeout(400)
    sw = page.locator('button[role="switch"][aria-label="Hard Mode"]').first
    sw.wait_for(state="visible", timeout=3000)
    if sw.get_attribute("aria-checked") != "true":
        sw.click()
        page.wait_for_timeout(300)
    state = sw.get_attribute("aria-checked")
    page.keyboard.press("Escape")  # close settings
    page.wait_for_timeout(400)
    if state != "true":
        raise RuntimeError(f"Hard Mode not enabled (aria-checked={state})")


def _dialog_open(page):
    try:
        return page.locator('[role="dialog"]').first.is_visible(timeout=300)
    except Exception:
        return False


def _read_rows(page):
    states = page.evaluate(READ_BOARD_JS)
    rows = [states[i * 5:(i + 1) * 5] for i in range(6)]
    return rows


def _row_settled(row):
    # A submitted row has all 5 tiles in a scored state (no empty/tbd).
    return all(s in STATE_TO_CH for s in row)


def _row_filled(page, idx):
    # All 5 tiles of row idx have a letter committed (tbd or scored), none empty.
    row = _read_rows(page)[idx]
    return all(s != "empty" for s in row)


def _type_guess(page, idx, word, tries=3):
    # Type the word and confirm the row filled; modals/focus loss can drop keys.
    for _ in range(tries):
        if _dialog_open(page):
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
        for ch in word:
            page.keyboard.press(ch.lower())
            page.wait_for_timeout(60)
        page.wait_for_timeout(250)
        if _row_filled(page, idx):
            return
        # Clear whatever partially landed and retry.
        for _ in range(5):
            page.keyboard.press("Backspace")
            page.wait_for_timeout(40)
    raise RuntimeError(f"could not enter '{word}' into row {idx}: {_read_rows(page)[idx]}")


def _wait_row(page, idx, timeout=12.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        row = _read_rows(page)[idx]
        if _row_settled(row):
            return [STATE_TO_CH[s] for s in row]
        page.wait_for_timeout(200)
    raise TimeoutError(f"row {idx} never settled: {_read_rows(page)[idx]}")


def play(config, headless=False):
    from playwright.sync_api import sync_playwright

    profile = os.path.join(ROOT, config.get("chrome_profile_dir", "scripts/daily/chrome-profile"))
    os.makedirs(profile, exist_ok=True)

    start_word = config.get("start_word", "lares")

    result = {"solved": False, "attempts": 0, "guesses": [], "responses": [],
              "puzzle_no": None, "answer": None, "date": time.strftime("%Y-%m-%d")}

    incognito = config.get("incognito", False)
    with sync_playwright() as p:
        if incognito:
            # Ephemeral context: real Chrome, no persisted cookies/state (incognito-equivalent).
            browser = p.chromium.launch(
                channel="chrome", headless=headless,
                args=["--disable-blink-features=AutomationControlled", "--incognito"],
            )
            ctx = browser.new_context(viewport={"width": 1100, "height": 900})
        else:
            ctx = p.chromium.launch_persistent_context(
                profile,
                channel="chrome",
                headless=headless,
                viewport={"width": 1100, "height": 900},
                args=["--disable-blink-features=AutomationControlled"],
            )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(1500)
            _open_game(page)
            _enable_hard_mode(page)

            guess = start_word
            temp_dict = None
            for attempt in range(6):
                _type_guess(page, attempt, guess)
                page.keyboard.press("Enter")

                resp = _wait_row(page, attempt)
                result["guesses"].append(guess)
                result["responses"].append(resp)
                result["attempts"] = attempt + 1

                if all(r == "g" for r in resp):
                    result["solved"] = True
                    result["answer"] = guess
                    break

                temp_dict = wordle.find_words(guess, resp, temp_dict)
                if not temp_dict:
                    break
                guess = solver.get_best_word(temp_dict)
                page.wait_for_timeout(400)

            page.wait_for_timeout(800)
        finally:
            ctx.close()

    return result


if __name__ == "__main__":
    import json
    cfg = json.load(open(os.path.join(os.path.dirname(__file__), "config.json")))
    r = play(cfg)
    print(json.dumps(r, indent=2))
