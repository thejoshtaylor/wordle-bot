# Re-run the wordle.xlsx ranking using the ORIGINAL train.py algorithm verbatim
# (train.checkGuessAndGetRemainingWords), only swapping what the goal words are.
#
# Guess words : every word in wordle.xlsx column A (~14.8k).
# Goal words  : union of the top-5000 dict-rank.csv words and all wordle-to-rank.csv
#               words (~5.1k). Also used as the filter pool, exactly as the original
#               used one dictionary for both guess-eval and remaining-count.
#
# Per guess: Low/High/Avg of remaining pool words, same as findHighestReductionWord.

import csv
import re
import sys
import time
import zipfile

import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import train  # original algorithm


def load_guess_words(path="wordle.xlsx"):
    z = zipfile.ZipFile(path)
    ss = re.findall(r"<t[^>]*>(.*?)</t>", z.read("xl/sharedStrings.xml").decode("utf-8", "ignore"))
    return [s.lower() for s in ss if len(s) == 5 and s.isalpha()]


def load_goal_words():
    dr = [l.split(",")[0].strip().lower() for l in open("dict-rank.csv")]
    goals = list(dr[:5000])
    with open("wordle-to-rank.csv") as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            if row:
                goals.append(row[0].strip().lower())
    return list(dict.fromkeys(goals))


def run(guesses, goals, out_path):
    pool = goals  # remaining counted within the goal set
    start_size = len(pool)
    results = {}
    start = time.time()

    for i, trial in enumerate(guesses):
        avg = 0.0
        low = start_size
        high = 0
        for word in goals:
            n = train.checkGuessAndGetRemainingWords(pool, trial, word)
            if n < low and n != 0:
                low = n
            if n > high:
                high = n
            avg += float(n)
        avg /= float(len(goals))
        results[trial] = (low, high, avg)

        done = i + 1
        if done % 50 == 0 or done == len(guesses):
            el = time.time() - start
            eta = el / done * (len(guesses) - done)
            print(f"\r[{done:5d}/{len(guesses)}] {el:7.1f}s elapsed, {eta/60:6.1f}m left", end="", flush=True)
    print()

    ordered = sorted(results.items(), key=lambda kv: kv[1][2])
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Word", "Low", "High", "Avg"])
        for word, (low, high, avg) in ordered:
            w.writerow([word, low, high, f"{avg:.9f}"])
    print(f"Wrote {len(ordered)} rows -> {out_path}")
    for word, (low, high, avg) in ordered[:10]:
        print(f"  {word}  low={low:4d} high={high:4d} avg={avg:8.3f}")


if __name__ == "__main__":
    guesses = load_guess_words()
    goals = load_goal_words()
    print(f"Guess words: {len(guesses)}")
    print(f"Goal words:  {len(goals)}")

    if len(sys.argv) > 1 and sys.argv[1] == "--bench":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        t0 = time.time()
        for trial in guesses[:n]:
            for word in goals:
                train.checkGuessAndGetRemainingWords(goals, trial, word)
        dt = time.time() - t0
        per = dt / n
        print(f"\n{n} guesses in {dt:.1f}s -> {per*1000:.1f}ms/guess")
        print(f"Full run ETA: {per*len(guesses)/60:.1f} min ({per*len(guesses)/3600:.2f} h)")
    else:
        run(guesses, goals, "dict-rank-top5000-ranking.csv")
