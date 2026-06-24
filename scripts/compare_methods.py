# Compare the OLD solver (most-common remaining word every turn) against the NEW
# two-phase solver (reduce while >n remain, then most-common) on a single word,
# offline. Prints each trajectory and the guess count.
#
#   python scripts/compare_methods.py            # today's word: queer, start lares
#   python scripts/compare_methods.py crane
#   python scripts/compare_methods.py crane --start ranes

import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)  # main/wordle open data files by relative path

import wordle
import main as solver


def run(answer, start, pick):
    # pick(word_list) -> next guess. Returns (n_guesses, [guesses]).
    guess = start
    temp = list(solver.GOAL_WORDS)  # candidate answers within the goal set
    trail = []
    for attempt in range(1, 21):
        resp = wordle.check_guess(answer, guess)
        trail.append((guess, "".join(resp).replace(" ", "b")))
        if all(r == "g" for r in resp):
            return attempt, trail
        temp = wordle.find_words(guess, resp, temp)
        if not temp:
            return attempt, trail  # dead end
        guess = pick(temp)
    return 99, trail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("word", nargs="?", default="queer", help="answer to solve")
    ap.add_argument("--start", default="plant")
    args = ap.parse_args()
    answer = args.word.lower()

    for label, pick in (("OLD (most-common only)", solver.get_best_word),
                        ("NEW (two-phase, n=%d)" % solver.N_THRESHOLD, solver.pick_next_guess)):
        t0 = time.time()
        n, trail = run(answer, args.start, pick)
        dt = time.time() - t0
        print(f"\n{label}  ->  {n} guesses   ({dt:.1f}s)")
        for g, pat in trail:
            print(f"   {g}  {pat}")


if __name__ == "__main__":
    main()
