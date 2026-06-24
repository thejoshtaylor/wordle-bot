# Which candidate-answer POOL should the solver track within?
#
# Always GRADED on the real NYT answer list (all-wordle-words.txt) -- the true
# distribution of what Wordle asks. The solver's POOL (the set it filters/reduces
# and draws hard-mode guesses from) is the knob. An answer that falls outside the
# pool becomes unreachable -> counted as a failure, so this directly trades pool
# coverage against pool noise.
#
# Fixed opener + n while comparing pools; tune those afterwards (eval_matrix.py).
#
#   python scripts/eval_pools.py --start slate --n 2

import argparse
import csv
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from train_n import (A, ALLGREEN, feedback_codes, goal_rank, to_matrix)  # noqa: E402


def dict_rank_words():
    return [l.split(",")[0].strip().lower() for l in open(os.path.join(ROOT, "dict-rank.csv"))]


def real_answers():
    ws = open(os.path.join(ROOT, "all-wordle-words.txt")).read().split()
    return list(dict.fromkeys(w.strip().lower() for w in ws if len(w.strip()) == 5))


def wordle_to_rank_words():
    out = []
    with open(os.path.join(ROOT, "wordle-to-rank.csv")) as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            if row:
                out.append(row[0].strip().lower())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="slate")
    ap.add_argument("--n", type=int, default=2)
    args = ap.parse_args()

    dr = dict_rank_words()
    answers = real_answers()
    wtr = wordle_to_rank_words()

    # Candidate pools to compare (name -> word list).
    def topk(k):
        return dr[:k]
    pools = {
        "real-only(1799)": answers,
        "top-1500": topk(1500),
        "top-2000": topk(2000),
        "top-3000": topk(3000),
        "top-5000": topk(5000),
        "top-7000": topk(7000),
        "cur-5097(top5k+wtr)": list(dict.fromkeys(topk(5000) + wtr)),
        "real+top-3000": list(dict.fromkeys(answers + topk(3000))),
        "real+top-5000": list(dict.fromkeys(answers + topk(5000))),
    }

    # Universe = everything we might index in P (every pool word + every answer).
    universe = list(dict.fromkeys(
        [w for pl in pools.values() for w in pl] + answers))
    uidx = {w: i for i, w in enumerate(universe)}
    U = len(universe)
    print(f"Universe: {U} words   Answers graded: {len(answers)}")

    W = to_matrix(universe)
    counts0 = np.zeros((U, 26), dtype=np.int16)
    rows = np.arange(U)
    for j in range(5):
        np.add.at(counts0, (rows, W[:, j]), 1)

    print(f"Building {U}x{U} pattern matrix...")
    P = np.empty((U, U), dtype=np.int16)
    t0 = time.time()
    for i in range(U):
        P[i] = feedback_codes(W[i], W, counts0)
    print(f"  done in {time.time()-t0:.1f}s")

    rankmap = goal_rank()
    BIG = len(rankmap) + 1
    rank = np.array([rankmap.get(w, BIG) for w in universe])

    ans_idx = np.array([uidx[w] for w in answers])
    start_pat = feedback_codes([ord(c) - A for c in args.start], W, counts0)
    n = args.n

    def evaluate(pool_words):
        pool_idx = np.array(sorted(uidx[w] for w in pool_words))
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

        def solve(a):
            code = int(start_pat[a])
            if code == ALLGREEN:
                return 1
            attempts = 1
            pool = pool_idx[start_pat[pool_idx] == code]
            while True:
                R = len(pool)
                if R == 0:
                    return 99  # answer not in/reachable within pool -> fail
                g = most_common(pool) if R <= n else best_reduction(pool)
                attempts += 1
                if g == a:
                    return attempts
                code = int(P[g, a])
                pool = pool[P[g, pool] == code]
                if attempts > 25:
                    return 99

        counts = np.array([solve(int(a)) for a in ans_idx])
        return counts

    print(f"\nOpener={args.start}  n={n}  (graded on {len(answers)} real answers)\n")
    print(f"  {'pool':22s} {'size':>5s}  {'avg':>6s} {'med':>3s} {'fail6':>5s} "
          f"{'unreach':>7s} {'%<=6':>5s}")
    out_rows = []
    for name, pl in pools.items():
        pl = list(dict.fromkeys(pl))
        c = evaluate(pl)
        avg = float(c.mean())
        med = float(np.median(c))
        fails = int((c > 6).sum())
        unreach = int((c == 99).sum())
        s6 = 100.0 * (c <= 6).sum() / len(c)
        out_rows.append((name, len(pl), avg, med, fails, unreach, s6))
        print(f"  {name:22s} {len(pl):5d}  {avg:6.3f} {med:3.0f} {fails:5d} "
              f"{unreach:7d} {s6:5.1f}")

    out = os.path.join(ROOT, "scripts", "pool-comparison.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pool", "size", "avg_guesses", "median", "fails_gt6",
                    "unreachable", "pct_solved_6"])
        for row in out_rows:
            w.writerow([row[0], row[1], f"{row[2]:.6f}", f"{row[3]:.1f}",
                        row[4], row[5], f"{row[6]:.4f}"])
    best = min(out_rows, key=lambda r: r[2])
    print(f"\nWrote {out}")
    print(f"Best pool: {best[0]}  avg {best[2]:.3f}, {best[6]:.1f}% <=6")


if __name__ == "__main__":
    main()
