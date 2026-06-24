# Opener x n matrix on the 5097-word goal set (top-5000 dict-rank + wordle-to-rank).
# Pool == graded set == the goal set, same as scripts/train_n.py.
#
# Grids a set of openers x a range of n, reports avg guesses per cell, and the
# best (opener, n) combo. Openers default to the top of scripts/opener-scan.csv
# (the full-dictionary opener ranking at n=2) plus any passed via --extra.
#
#   python scripts/eval_matrix.py
#   python scripts/eval_matrix.py --top-openers 20 --extra crane,raise

import argparse
import csv
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from train_n import (A, ALLGREEN, PAT_CACHE, feedback_codes, goal_rank,  # noqa: E402
                     load_goals, to_matrix)

N_GRID = [0, 1, 2, 3, 4, 5, 6, 8, 10, 15, 20, 25]
SCAN_CSV = os.path.join(ROOT, "scripts", "opener-scan.csv")


def pick_openers(top, extra):
    names = []
    if os.path.exists(SCAN_CSV):
        with open(SCAN_CSV) as f:
            r = csv.reader(f)
            next(r)
            for row in r:
                if row:
                    names.append(row[0])
                if len(names) >= top:
                    break
    for e in extra.split(","):
        e = e.strip().lower()
        if e and e not in names:
            names.append(e)
    return names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-openers", type=int, default=15,
                    help="how many openers off the opener-scan ranking to grid")
    ap.add_argument("--extra", default="lares,ranes,crane,raise,slate,salet,trace,crate",
                    help="extra openers to include")
    args = ap.parse_args()

    goals = load_goals()
    G = len(goals)
    uidx = {w: i for i, w in enumerate(goals)}
    print(f"Goal set: {G}")

    W = to_matrix(goals)
    counts0 = np.zeros((G, 26), dtype=np.int16)
    rows = np.arange(G)
    for j in range(5):
        np.add.at(counts0, (rows, W[:, j]), 1)

    if os.path.exists(PAT_CACHE) and np.load(PAT_CACHE, mmap_mode="r").shape == (G, G):
        P = np.load(PAT_CACHE)
        print(f"Loaded pattern matrix {PAT_CACHE}")
    else:
        print(f"Building {G}x{G} pattern matrix...")
        P = np.empty((G, G), dtype=np.int16)
        for i in range(G):
            P[i] = feedback_codes(W[i], W, counts0)
        np.save(PAT_CACHE, P)

    rankmap = goal_rank()
    BIG = len(rankmap) + 1
    rank = np.array([rankmap.get(w, BIG) for w in goals])
    all_idx = np.arange(G)

    # Caches depend only on the running pool (not opener/n) -> shared everywhere.
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

    def solve(a, start_pat, n):
        code = int(start_pat[a])
        if code == ALLGREEN:
            return 1
        attempts = 1
        pool = all_idx[start_pat == code]
        while True:
            R = len(pool)
            g = most_common(pool) if R <= n else best_reduction(pool)
            attempts += 1
            if g == a:
                return attempts
            code = int(P[g, a])
            pool = pool[P[g, pool] == code]
            if attempts > 25:
                return attempts

    def score(start_pat, n):
        c = np.array([solve(a, start_pat, n) for a in range(G)])
        return float(c.mean()), int((c > 6).sum())

    openers = pick_openers(args.top_openers, args.extra)
    print(f"Matrix: {len(openers)} openers x {len(N_GRID)} n values\n")
    print("opener  " + "".join(f"{('n='+str(n)):>8s}" for n in N_GRID) + "   best")

    grid = {}
    pats = {ow: feedback_codes([ord(c) - A for c in ow], W, counts0) for ow in openers}
    t0 = time.time()
    rows_out = []
    for ow in openers:
        sp = pats[ow]
        line = f"{ow:6s}  "
        best_cell = None
        for n in N_GRID:
            avg, fails = score(sp, n)
            grid[(ow, n)] = (avg, fails)
            line += f"{avg:8.4f}"
            if best_cell is None or avg < best_cell[1]:
                best_cell = (n, avg, fails)
        line += f"   n={best_cell[0]} {best_cell[1]:.4f}"
        print(line)
        rows_out.append(ow)
    print(f"\n({time.time()-t0:.1f}s)")

    out = os.path.join(ROOT, "scripts", "matrix-opener-n.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["opener"] + [f"n={n}" for n in N_GRID] + ["best_n", "best_avg", "best_fails"])
        for ow in rows_out:
            best_n = min(N_GRID, key=lambda n: grid[(ow, n)][0])
            ba, bf = grid[(ow, best_n)]
            w.writerow([ow] + [f"{grid[(ow, n)][0]:.6f}" for n in N_GRID] + [best_n, f"{ba:.6f}", bf])

    bow, bn = min(grid, key=lambda k: grid[k][0])
    bavg, bfails = grid[(bow, bn)]
    print(f"Wrote {out}")
    print(f"BEST CELL: opener={bow}  n={bn}  avg={bavg:.4f}  fails={bfails}")


if __name__ == "__main__":
    main()
