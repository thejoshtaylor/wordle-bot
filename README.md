# Wordle Bot

A Python-based Wordle solver that can play the game automatically, assist you in solving the [NYT Wordle](https://www.nytimes.com/games/wordle/index.html), and benchmark different starting word strategies.

---

## Setup

### 1. Create a virtual environment

```bash
python -m venv venv
```

### 2. Activate it

**Windows:**
```bash
venv\Scripts\activate
```

**macOS / Linux:**
```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note (Windows):** The `keyboard` library requires the terminal to be run as **Administrator** for key-capture to work in the *Help Me Solve* mode.

### 4. Run

```bash
python main.py
```

---

## Menu Options

### 1. Play Game
Guess the hidden word manually — just like the real Wordle. You get 6 attempts. The bot generates a consistent "word of the day" based on the current date so results are reproducible.

- Type a valid 5-letter word and press Enter.
- Press Enter on a blank line to auto-fill with the word of the day (for testing).
- After each guess the letters are highlighted: **green** = correct position, **yellow** = wrong position, **gray** = not in word.

### 2. Help Me Solve
Assists you while playing the real NYT Wordle. The bot suggests what word to try next; you enter that word into Wordle and then tell the bot the result.

- The bot starts with `ranes` and suggests follow-up words.
- After entering the suggested word into Wordle, type the color response using:
  - `g` — green (correct letter, correct position)
  - `y` — yellow (correct letter, wrong position)
  - `b` — black/gray (letter not in the word)
- Press **Backspace** to correct a character, **Enter** to confirm.
- Repeat for up to 6 rounds.

### 3. Solve (Challenge the Computer)
You pick any valid 5-letter word and watch the bot solve it automatically. Useful for testing the algorithm or seeing how it handles tricky words.

- Enter the target word at the prompt.
- The bot will guess and print each attempt with color-coded feedback until it solves it.

### 4. Many Solve (Benchmark)
Runs the solver against a random sample of words from the dictionary and reports statistics. Use this to measure overall performance.

- Enter a number of words to test, or `a` to test the entire dictionary (~13k words).
- Reports: success rate, average/min/max attempts, and how many were solved within 6 tries.

### 5. Auto Solve (Find the Best Starting Word)
Tests multiple different starting words to find which one leads to the best overall solve rate and fewest attempts. Runs in parallel using all available CPU cores.

- Enter the number of candidate starting words to try, or `a` for all.
- Optionally saves results to a timestamped CSV file.
- Reports the best starting word by success rate and by fewest average attempts.

### 6. Quit
Exits the program.

---

## How the Algorithm Works

### Dictionary
The bot uses a list of 12,972 valid 5-letter English words (`dictionary.txt`), the same set accepted by Wordle.

### Guessing Strategy (two-phase, hard mode)
1. **Start** with a fixed opening word (`plant` by default — the best opener found by `scripts/eval_goalsets.py`).
2. **Check** the response: each letter is marked green, yellow, or gray.
3. **Filter** the candidate answers with `find_words()`, tracked within the
   **goal set** (the 5097-word answer pool, not the full dictionary):
   - Green letters lock a letter to its exact position.
   - Yellow letters require a letter to appear somewhere else.
   - Gray letters eliminate a letter from consideration entirely (with correct duplicate handling).
4. **Select** the next guess with `pick_next_guess()` (hard mode — guesses are
   drawn from the remaining candidates):
   - **Learning phase** (remaining `> n`): `best_reduction_word()` picks the word
     that, on average, shrinks the candidate set the most.
   - **Guessing phase** (remaining `<= n`): `get_best_word()` picks the most
     common remaining word (`dict-rank.csv`).
   - `n = 2` (`N_THRESHOLD`) was tuned by `scripts/train_n.py`; pure reduction wins.
5. **Repeat** until solved.

### Why two phases
Always guessing the most common word (the old strategy) wastes turns once many
candidates remain. Reducing first, then switching to frequency only when the set
is tiny, drops the average from ~4.28 to ~3.90 guesses over the goal set. See
`scripts/*-training.csv` and `scripts/*-matrix.csv` for the tuning data.

### Parallelism
The *Auto Solve* mode uses Python's `multiprocessing` module to run multiple starting-word evaluations concurrently (up to `cpu_count / 2` parallel workers), with a live progress display powered by Rich.

---

## File Structure

```
wordle-bot/
├── main.py          # Entry point — menu, two-phase solver, benchmark modes
├── wordle.py        # Core helpers — word checking, filtering, colored output
├── train.py         # Legacy training/optimization experiments (mostly archived)
├── process.py       # Utility: convert results.pkl → results.csv
├── dictionary.txt   # 12,972 valid 5-letter Wordle words
├── dict-rank.csv    # Word frequency rankings used for next-guess selection
├── results.pkl      # Pre-computed optimization data (not required for normal use)
├── requirements.txt # Python dependencies
├── scripts/
│   ├── train_n.py        # Sweep the n threshold over the goal set -> CSV
│   ├── eval_pools.py     # Compare candidate answer pools (graded on real answers)
│   ├── eval_matrix.py    # Opener x n matrix on the goal set
│   ├── eval_goalsets.py  # Opener x goal-set matrix
│   ├── compare_methods.py # Old vs new solver on a single word
│   └── *.csv             # Tuning results
└── LICENSE          # MIT License
```

---

## Dependencies

| Package   | Purpose                                      |
|-----------|----------------------------------------------|
| `rich`    | Colored terminal output and progress bars    |
| `keyboard`| Raw keypress capture for the Help Me Solve mode |

---

## License

MIT License — see [LICENSE](LICENSE).
