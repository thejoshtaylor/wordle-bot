# Trains the "n" threshold for the two-phase solver.
#
# Two-phase strategy (hard mode):
#   - LEARNING phase  (remaining > n): guess the remaining word that, on average,
#     cuts the remaining set down the most (min expected remaining).
#   - GUESSING phase  (remaining <= n): guess the most common remaining word
#     (lowest dict-rank line index), i.e. main.get_best_word.
#   Hard mode => every guess is drawn from the still-consistent remaining words.
#
# Goal set : union of top-5000 dict-rank words + all wordle-to-rank words (5097),
#            same set used by scripts/rank_*.py. Answers and the remaining pool
#            both live in this set; the first guess (start word) is fixed.
#
# Sweeps a wide range of n, solving all 5097 goals for each, and writes a CSV so
# you can see which n minimises the average number of guesses.
#
#   python scripts/train_n.py                 # default start word "lares"
#   python scripts/train_n.py --start ranes
#
# Output: scripts/n-threshold-training.csv

import argparse
import csv
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = ord("a")
POW = np.array([1, 3, 9, 27, 81], dtype=np.int32)
ALLGREEN = int(2 * POW.sum())  # 242
PAT_CACHE = os.path.join(ROOT, "scripts", ".pattern_cache.npy")

# n values to test: dense where it matters, coarse out to "pure most-common".
N_VALUES = (list(range(0, 51)) +
            [55, 60, 70, 80, 100, 125, 150, 200, 300, 500, 1000, 5097])


def load_goals():
    dr = [l.split(",")[0].strip().lower() for l in open(os.path.join(ROOT, "dict-rank.csv"))]
    goals = list(dr[:5000])
    with open(os.path.join(ROOT, "wordle-to-rank.csv")) as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            if row:
                goals.append(row[0].strip().lower())
    return list(dict.fromkeys(goals))


def goal_rank():
    # line index in dict-rank.csv == "commonness" rank (lower = more common).
    rank = {}
    for i, l in enumerate(open(os.path.join(ROOT, "dict-rank.csv"))):
        w = l.split(",")[0].strip().lower()
        rank.setdefault(w, i)
    return rank


def to_matrix(words):
    return np.array([[ord(c) - A for c in w] for w in words], dtype=np.int8)


def feedback_codes(guess_letters, W, counts0):
    # Base-3 Wordle feedback code of `guess_letters` (len-5) vs every answer in W.
    g = np.asarray(guess_letters, dtype=np.int8)
    exact = W == g
    avail = counts0.copy()
    for j in range(5):
        m = exact[:, j]
        avail[m, g[j]] -= 1
    pat = np.zeros(W.shape, dtype=np.int32)
    pat[exact] = 2
    for j in range(5):
        gj = g[j]
        yellow = (~exact[:, j]) & (avail[:, gj] > 0)
        pat[yellow, j] = 1
        avail[yellow, gj] -= 1
    return (pat * POW).sum(1).astype(np.int16)


def build_pattern_matrix(W, counts0):
    G = len(W)
    if os.path.exists(PAT_CACHE):
        P = np.load(PAT_CACHE)
        if P.shape == (G, G):
            print(f"Loaded pattern matrix from {PAT_CACHE}")
            return P
    print(f"Building {G}x{G} pattern matrix...")
    P = np.empty((G, G), dtype=np.int16)
    start = time.time()
    for i in range(G):
        P[i] = feedback_codes(W[i], W, counts0)
        if (i + 1) % 500 == 0 or i + 1 == G:
            el = time.time() - start
            print(f"\r  [{i+1:5d}/{G}] {el:6.1f}s", end="", flush=True)
    print()
    np.save(PAT_CACHE, P)
    return P


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="lares", help="fixed opening word")
    ap.add_argument("--metric", default="expected", choices=["expected", "minimax"],
                    help="learning-phase objective: min expected remaining, or min worst-case")
    ap.add_argument("--starts", default="",
                    help="comma list of opening words to compare at the best n (and old method)")
    ap.add_argument("--scan-openers", default="", choices=["", "dict", "goals"],
                    help="rank EVERY opener (full dictionary or goal set) at --scan-n; skips the n sweep")
    ap.add_argument("--scan-n", type=int, default=2, help="fixed n used during --scan-openers")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    if not args.out:
        suffix = "" if args.metric == "expected" else "-" + args.metric
        args.out = os.path.join(ROOT, "scripts", f"n-threshold-training{suffix}.csv")

    goals = load_goals()
    G = len(goals)
    idx = {w: i for i, w in enumerate(goals)}
    print(f"Goal words: {G}")

    W = to_matrix(goals)
    counts0 = np.zeros((G, 26), dtype=np.int16)
    rows = np.arange(G)
    for j in range(5):
        np.add.at(counts0, (rows, W[:, j]), 1)

    P = build_pattern_matrix(W, counts0)

    rankmap = goal_rank()
    BIG = len(rankmap) + 1
    rank = np.array([rankmap.get(w, BIG) for w in goals])

    all_idx = np.arange(G)
    print(f"Reduction metric: {args.metric}")

    # Caches keyed by the pool's byte signature (pool is always sorted ascending).
    # Both decisions depend only on the pool (not on n or the start word), so the
    # caches are reused across every n and every start word in this run.
    red_cache = {}     # pool -> best-reduction guess index
    common_cache = {}  # pool -> most-common guess index

    def best_reduction(pool):
        key = pool.tobytes()
        hit = red_cache.get(key)
        if hit is not None:
            return hit
        sub = P[np.ix_(pool, pool)]           # R x R feedback codes (rows=guesses)
        best, best_score, best_rank = pool[0], None, None
        for r in range(len(pool)):
            c = np.bincount(sub[r], minlength=ALLGREEN + 1).astype(np.int64)
            if args.metric == "minimax":
                score = int(c.max())           # worst-case remaining
            else:
                score = int((c * c).sum())     # sum of squared bucket sizes (~expected)
            wi = pool[r]
            if (best_score is None or score < best_score or
                    (score == best_score and rank[wi] < best_rank)):
                best, best_score, best_rank = wi, score, rank[wi]
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

    def solve(answer, n, start_pat):
        attempts = 1
        code = int(start_pat[answer])
        if code == ALLGREEN:
            return 1
        pool = all_idx[start_pat == code]
        while True:
            R = len(pool)
            g = most_common(pool) if R <= n else best_reduction(pool)
            attempts += 1
            if g == answer:
                return attempts
            code = int(P[g, answer])
            pool = pool[P[g, pool] == code]
            if attempts > 25:               # safety; never expected to hit
                return attempts

    def run_all(n, start_pat):
        counts = np.empty(G, dtype=np.int32)
        for a in range(G):
            counts[a] = solve(a, n, start_pat)
        return counts

    def stats(counts):
        return dict(avg=float(counts.mean()), median=float(np.median(counts)),
                    solved6=int((counts <= 6).sum()), fails=int((counts > 6).sum()),
                    mx=int(counts.max()),
                    dist=[int((counts == k).sum()) for k in range(1, 7)],
                    g7=int((counts >= 7).sum()))

    # --- Mode: scan every opener at a fixed n, rank by avg guesses ---
    if args.scan_openers:
        if args.scan_openers == "dict":
            openers = open(os.path.join(ROOT, "dictionary.txt")).read().split()
        else:
            openers = goals
        n = args.scan_n
        print(f"Scanning {len(openers)} openers at n={n}...")
        scan = []
        t0 = time.time()
        for k, ow in enumerate(openers):
            sp = feedback_codes([ord(c) - A for c in ow], W, counts0)
            s = stats(run_all(n, sp))
            scan.append((ow, s["avg"], s["median"], s["fails"], s["mx"]))
            if (k + 1) % 250 == 0 or k + 1 == len(openers):
                el = time.time() - t0
                eta = el / (k + 1) * (len(openers) - k - 1)
                print(f"\r  [{k+1:5d}/{len(openers)}] {el:6.1f}s, {eta:6.1f}s left", end="", flush=True)
        print()
        scan.sort(key=lambda r: (r[1], r[3]))
        out = os.path.join(ROOT, "scripts", "opener-scan.csv")
        with open(out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["opener", "avg_guesses", "median_guesses", "fails", "max_guesses"])
            for ow, avg, med, fails, mx in scan:
                w.writerow([ow, f"{avg:.6f}", f"{med:.1f}", fails, mx])
        print(f"Wrote {len(scan)} rows -> {out}\nTop 25 openers (n={n}):")
        for ow, avg, med, fails, mx in scan[:25]:
            print(f"  {ow}  avg={avg:.4f}  fails={fails:3d}  max={mx}")
        return

    start_pat = feedback_codes([ord(c) - A for c in args.start], W, counts0)

    rows_out = []
    t0 = time.time()
    for ni, n in enumerate(N_VALUES):
        s = stats(run_all(n, start_pat))
        rows_out.append((n, s))
        print(f"\r[{ni+1:2d}/{len(N_VALUES)}] n={n:5d}  avg={s['avg']:.4f}  "
              f"median={s['median']:.1f}  solved6={100*s['solved6']/G:5.1f}%  "
              f"fails={s['fails']:4d}  ({time.time()-t0:5.1f}s)   ", flush=True)

    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["n", "avg_guesses", "median_guesses", "pct_solved_6", "fails",
                    "max_guesses", "g1", "g2", "g3", "g4", "g5", "g6", "g7plus"])
        for n, s in rows_out:
            w.writerow([n, f"{s['avg']:.6f}", f"{s['median']:.1f}",
                        f"{100*s['solved6']/G:.4f}", s["fails"], s["mx"], *s["dist"], s["g7"]])

    best_n, best_s = min(rows_out, key=lambda r: r[1]["avg"])
    print(f"\nWrote {len(rows_out)} rows -> {args.out}")
    print(f"Best n = {best_n}  (avg {best_s['avg']:.4f}, median {best_s['median']:.1f}, "
          f"{100*best_s['solved6']/G:.1f}% <=6, {best_s['fails']} fails)")

    # Optional: compare opening words at the best n (new) and at n=inf (old method).
    if args.starts:
        BIGN = 10 ** 9
        print(f"\nStart-word comparison (start, then new n={best_n} / old most-common):")
        print(f"  {'word':6s}  {'new avg':>7s} {'med':>3s} {'fails':>5s}    "
              f"{'old avg':>7s} {'med':>3s} {'fails':>5s}")
        rows_sw = []
        for sw in [w.strip().lower() for w in args.starts.split(",") if w.strip()]:
            sp = feedback_codes([ord(c) - A for c in sw], W, counts0)
            ns = stats(run_all(best_n, sp))
            os_ = stats(run_all(BIGN, sp))
            rows_sw.append((sw, ns, os_))
            print(f"  {sw:6s}  {ns['avg']:7.4f} {ns['median']:3.0f} {ns['fails']:5d}    "
                  f"{os_['avg']:7.4f} {os_['median']:3.0f} {os_['fails']:5d}")
        sw_out = args.out.replace(".csv", "-startwords.csv")
        with open(sw_out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["start_word", "new_avg", "new_median", "new_fails",
                        "old_avg", "old_median", "old_fails"])
            for sw, ns, os_ in rows_sw:
                w.writerow([sw, f"{ns['avg']:.6f}", f"{ns['median']:.1f}", ns["fails"],
                            f"{os_['avg']:.6f}", f"{os_['median']:.1f}", os_["fails"]])
        best_sw = min(rows_sw, key=lambda r: r[1]["avg"])
        print(f"Wrote {sw_out}")
        print(f"Best opener (new, n={best_n}): {best_sw[0]}  avg {best_sw[1]['avg']:.4f}")


if __name__ == "__main__":
    main()
