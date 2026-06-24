# Re-run the wordle.xlsx all-vs-all ranking with a restricted goal set.
#
# Guess words : every word in wordle.xlsx column A (~14.8k).
# Goal words  : intersection of wordle-to-rank.csv words and the top-5000 of
#               dict-rank.csv (~1.7k).
# Remaining   : counted within the goal set (an answer is one of the goals).
#
# For each guess, plays it against every goal, computes Wordle feedback (with
# correct duplicate-letter handling, matching train.py::checkGuessAndGetRemainingWords),
# and records Low/High/Avg of the number of goal words left consistent with the
# feedback. Output sorted by Avg ascending (lowest = best), same columns as wordle.xlsx.

import csv
import re
import time
import zipfile

import numpy as np

A = ord("a")
ALLGREEN = 2 * (1 + 3 + 9 + 27 + 81)  # base-3 code when every position is green
POW = np.array([1, 3, 9, 27, 81], dtype=np.int32)


def load_guess_words(path="wordle.xlsx"):
    # Column A of the sheet == the 5-letter words in sharedStrings (headers aside).
    z = zipfile.ZipFile(path)
    ss = re.findall(r"<t[^>]*>(.*?)</t>", z.read("xl/sharedStrings.xml").decode("utf-8", "ignore"))
    return [s.lower() for s in ss if len(s) == 5 and s.isalpha()]


def load_goal_words():
    # Union of the top-5000 dict-rank words and all wordle-to-rank.csv words.
    dr = [l.split(",")[0].strip().lower() for l in open("dict-rank.csv")]
    goals = list(dr[:5000])
    with open("wordle-to-rank.csv") as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            if row:
                goals.append(row[0].strip().lower())
    return list(dict.fromkeys(goals))  # dedupe, preserve order


def to_matrix(words):
    return np.array([[ord(c) - A for c in w] for w in words], dtype=np.int8)


def main():
    guesses = load_guess_words()
    goals = load_goal_words()
    G = len(goals)
    print(f"Guess words: {len(guesses)}")
    print(f"Goal words:  {G}")

    # The "remaining" pool == the goal set (an answer is one of the goals).
    W = to_matrix(goals)  # G x 5  (goal / pool letters)

    # Per-goal letter counts (G x 26) for yellow detection; presence for filtering.
    counts0 = np.zeros((G, 26), dtype=np.int16)
    rows = np.arange(G)
    for j in range(5):
        np.add.at(counts0, (rows, W[:, j]), 1)
    present = counts0 > 0  # G x 26  letter-in-word presence (the pool)

    results = []
    start = time.time()
    for i, gw in enumerate(guesses):
        g = np.array([ord(c) - A for c in gw], dtype=np.int8)  # 5

        # --- Wordle feedback pattern for guess g vs every goal (proper consume) ---
        exact = W == g  # G x 5  greens
        avail = counts0.copy()
        for j in range(5):
            m = exact[:, j]
            avail[m, g[j]] -= 1  # greens consume a letter
        pat = np.zeros((G, 5), dtype=np.int32)
        pat[exact] = 2
        for j in range(5):
            gj = g[j]
            yellow = (~exact[:, j]) & (avail[:, gj] > 0)
            pat[yellow, j] = 1
            avail[yellow, gj] -= 1
        code = (pat * POW).sum(1)  # G  base-3 feedback code per goal

        # --- remaining(g, w) = # pool words passing checkGuessAndGetRemainingWords'
        #     set-based filter for that feedback. The filter is a pure function of the
        #     pattern, so compute it once per distinct pattern present. ---
        uniq = np.unique(code)
        count_for = {}
        for c in uniq.tolist():
            if c == ALLGREEN:
                count_for[c] = 0  # exact solve -> 0 (matches original)
                continue
            trits = [(c // p) % 3 for p in (1, 3, 9, 27, 81)]
            green_letters = set()
            must_have = set()  # yellow letters
            mask = np.ones(G, dtype=bool)
            for j, t in enumerate(trits):
                L = int(g[j])
                if t == 2:
                    green_letters.add(L)
                    mask &= W[:, j] == L
                elif t == 1:
                    must_have.add(L)
                    mask &= W[:, j] != L
            for L in must_have:
                mask &= present[:, L]
            grey_letters = {int(g[j]) for j, t in enumerate(trits) if t == 0}
            for L in grey_letters - green_letters - must_have:
                mask &= ~present[:, L]
            count_for[c] = int(mask.sum())

        rem = np.array([count_for[int(c)] for c in code], dtype=np.int64)
        nz = rem[rem > 0]
        low = int(nz.min()) if nz.size else 0
        high = int(rem.max())
        avg = float(rem.mean())
        results.append((gw, low, high, avg))

        if (i + 1) % 1000 == 0 or i + 1 == len(guesses):
            el = time.time() - start
            eta = el / (i + 1) * (len(guesses) - i - 1)
            print(f"\r[{i+1:5d}/{len(guesses)}] {el:6.1f}s elapsed, {eta:6.1f}s left", end="", flush=True)
    print()

    results.sort(key=lambda r: r[3])  # by Avg ascending
    out = "dict-rank-top5000-ranking.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Word", "Low", "High", "Avg"])
        for word, low, high, avg in results:
            w.writerow([word, low, high, f"{avg:.9f}"])
    print(f"Wrote {len(results)} rows -> {out}")
    print("Top 10:")
    for word, low, high, avg in results[:10]:
        print(f"  {word}  low={low:4d} high={high:4d} avg={avg:8.3f}")


if __name__ == "__main__":
    main()
