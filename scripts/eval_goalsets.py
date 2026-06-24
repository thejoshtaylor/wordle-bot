# Matrix: top-1000 openers x 5 candidate goal sets, n=2.
#
# Goal sets (each is BOTH the pool the solver tracks AND the graded answer set,
# same convention as scripts/train_n.py):
#   wordle          - real NYT answers only (all-wordle-words.txt)
#   wordle+top3000  - real answers + top-3000 dict-rank words
#   wordle+top5000  - real answers + top-5000
#   wordle+top7000  - real answers + top-7000
#   whole           - the entire dictionary.txt (~14.8k)
#
# Openers = the 1000 most common dict-rank words. Cell = avg guesses to solve the
# whole goal set from that opener. Per-cell numbers are comparable WITHIN a column
# (same answers); across columns they also reflect how hard that answer set is.
#
#   python scripts/eval_goalsets.py            # writes scripts/goalset-matrix*.csv

import csv
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from train_n import A, ALLGREEN, feedback_codes, goal_rank, to_matrix  # noqa: E402

N = 2


def main():
    dr = [l.split(",")[0].strip().lower() for l in open(os.path.join(ROOT, "dict-rank.csv"))]
    answers = list(dict.fromkeys(
        w.strip().lower() for w in open(os.path.join(ROOT, "all-wordle-words.txt")).read().split()
        if len(w.strip()) == 5))
    whole = open(os.path.join(ROOT, "dictionary.txt")).read().split()

    def uni(*lists):
        return list(dict.fromkeys([w for L in lists for w in L]))

    goalsets = [
        ("wordle", answers),
        ("wordle+top3000", uni(answers, dr[:3000])),
        ("wordle+top5000", uni(answers, dr[:5000])),
        ("wordle+top7000", uni(answers, dr[:7000])),
        ("whole", whole),
    ]
    openers = dr[:1000]
    rank_map = goal_rank()
    BIG = len(rank_map) + 1

    results = {}      # (opener, setname) -> (avg, fails)
    summary = []
    for name, words in goalsets:
        words = list(dict.fromkeys(words))
        S = len(words)
        uidx = {w: i for i, w in enumerate(words)}
        print(f"\n[{name}] {S} words -- building patterns...", flush=True)
        W = to_matrix(words)
        counts0 = np.zeros((S, 26), dtype=np.int16)
        rws = np.arange(S)
        for j in range(5):
            np.add.at(counts0, (rws, W[:, j]), 1)
        t0 = time.time()
        P = np.empty((S, S), dtype=np.uint8)
        for i in range(S):
            P[i] = feedback_codes(W[i], W, counts0).astype(np.uint8)
        print(f"  P {S}x{S} built in {time.time()-t0:.1f}s", flush=True)

        rank = np.array([rank_map.get(w, BIG) for w in words])
        all_idx = np.arange(S)
        red_cache, common_cache = {}, {}

        def best_reduction(pool):
            key = pool.tobytes()
            hit = red_cache.get(key)
            if hit is not None:
                return hit
            sub = P[np.ix_(pool, pool)]
            best, bscore, brank = pool[0], None, None
            for r in range(len(pool)):
                c = np.bincount(sub[r], minlength=ALLGREEN + 1).astype(np.int64)
                score = int((c * c).sum())
                wi = pool[r]
                if bscore is None or score < bscore or (score == bscore and rank[wi] < brank):
                    best, bscore, brank = wi, score, rank[wi]
            red_cache[key] = best
            return best

        def most_common(pool):
            key = pool.tobytes()
            hit = common_cache.get(key)
            if hit is not None:
                return hit
            g = pool[int(np.argmin(rank[pool]))]
            common_cache[key] = g
            return g

        def solve(a, start_pat):
            code = int(start_pat[a])
            if code == ALLGREEN:
                return 1
            attempts = 1
            pool = all_idx[start_pat == code]
            while True:
                R = len(pool)
                if R == 0:
                    return 99
                g = most_common(pool) if R <= N else best_reduction(pool)
                attempts += 1
                if g == a:
                    return attempts
                code = int(P[g, a])
                pool = pool[P[g, pool] == code]
                if attempts > 25:
                    return 99

        t0 = time.time()
        for k, ow in enumerate(openers):
            sp = feedback_codes([ord(c) - A for c in ow], W, counts0)
            c = np.array([solve(a, sp) for a in range(S)])
            results[(ow, name)] = (float(c.mean()), int((c > 6).sum()))
            if (k + 1) % 100 == 0 or k + 1 == len(openers):
                el = time.time() - t0
                eta = el / (k + 1) * (len(openers) - k - 1)
                print(f"\r  openers [{k+1:4d}/{len(openers)}] {el:6.1f}s, {eta:6.1f}s left",
                      end="", flush=True)
        print()
        best = min(openers, key=lambda o: results[(o, name)][0])
        ba, bf = results[(best, name)]
        summary.append((name, S, best, ba, bf))
        print(f"  best opener for {name}: {best}  avg={ba:.4f}  fails={bf}")

    # Wide matrix CSV: row per opener, col per goal set (avg).
    out = os.path.join(ROOT, "scripts", "goalset-matrix.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["opener"] + [name for name, _ in goalsets])
        for ow in openers:
            w.writerow([ow] + [f"{results[(ow, name)][0]:.6f}" for name, _ in goalsets])
    print(f"\nWrote {out}")

    print("\n=== best opener per goal set (n=2) ===")
    print(f"  {'goal set':16s} {'size':>6s}  {'best opener':12s} {'avg':>7s} {'fails':>6s}")
    for name, S, best, ba, bf in summary:
        print(f"  {name:16s} {S:6d}  {best:12s} {ba:7.4f} {bf:6d}")

    # Also: how a few notable openers do across every goal set.
    notable = ["plant", "peart", "slate", "crate", "salet", "crane", "lares", "ranes", "raise"]
    print("\n=== notable openers across goal sets (avg) ===")
    print(f"  {'opener':7s}" + "".join(f"{name[:13]:>14s}" for name, _ in goalsets))
    for ow in notable:
        if (ow, goalsets[0][0]) in results:
            print(f"  {ow:7s}" + "".join(
                f"{results[(ow, name)][0]:14.4f}" for name, _ in goalsets))


if __name__ == "__main__":
    main()
