# Wordle Solver
# Joshua Taylor 2024

# Import the necessary libraries
import os
import csv
import random
import time
from multiprocessing import Process, Pipe
from rich.progress import Progress
from rich import print
import wordle

# Get the best word from the dictionary
def get_best_word(word_list):
    # The csv is sorted by most common words, so return the first match found
    csv_file = csv.reader(open("dict-rank.csv", "r"))
    for row in csv_file:
        if row[0] in word_list:
            return row[0]

    # Fallback: return the first word in the list
    return word_list[0]

# Automatically solve the wordle
def solve_word(word, starting_word="ranes", printOut=True):
    # Initialize the variables
    attempts = 0
    solved = False
    tempDict = None

    test_word = starting_word

    err = "Out of tries"

    # Start the game
    while attempts < 16 and not solved:
        # Guess our current word
        response = wordle.check_guess(word, test_word)
        
        if printOut:
            print(f'[{attempts + 1}] {wordle.colored_word(test_word, response)}')

        # Check if we solved it
        if all([r == 'g' for r in response]):
            solved = True
            break

        # Find the word that we can learn the most from
        tempDict = wordle.find_words(test_word, response, tempDict)

        if len(tempDict) == 0:
            err = "no matching words"
            break

        # Pick the "most common" word
        test_word = get_best_word(tempDict)

        # Update the attempts
        attempts += 1

    # Done.
    if printOut:
        print()

    # Check if we solved it
    if not solved:
        if printOut:
            print(f"Failed to solve the game :( [{err}]")
    else:
        if printOut:
            print(f"Solved in {attempts + 1} attempts! [{test_word}]")

    return solved, attempts + 1

# Help solve the daily wordle
def help_me_solve():
    wordToTry = "ranes"
    tempDict = None
    for i in range(6):
        # Tell the user to enter a word
        print(f"Enter word: {wordToTry}")
        print("Enter the response from wordle (g for green, y for yellow, b for black/gray):")
        results = wordle.get_valid_wordle_response(wordToTry)
        print(f"Results: {wordle.colored_word(wordToTry, results)}")

        if all([r == 'g' for r in results]):
            print(f"Solved in {i + 1} attempts!")
            print()
            break

        # Find the best word to try next
        tempDict = wordle.find_words(wordToTry, results, tempDict)
        wordToTry = get_best_word(tempDict)


# Run many solves
def many_solve(num_to_solve, starting_word="ranes", printOut=True):

    # Stat variables
    successes = 0
    total = 0
    totalAttempts = 0
    maxAttempts = 0
    minAttempts = 1000
    under6 = 0
    under6Attempts = 0

    # Get the words to solve
    words = wordle.dictionary.copy()
    random.shuffle(words)
    words = words[:num_to_solve]

    # Clear the screen
    if printOut:
        os.system("cls" if os.name == "nt" else "clear")
        print("Many Solve")
        print()
        print("Solving... [  0.0%]", end="", flush=True)

    last_percent = 0

    # Solve the words
    for i, word in enumerate(words):
        success, attempts = solve_word(word, starting_word=starting_word, printOut=False)

        # Keep track of stats
        if success:
            successes += 1
            if attempts <= 6:
                under6 += 1
                under6Attempts += attempts
        total += 1
        totalAttempts += attempts
        if attempts > maxAttempts:
            maxAttempts = attempts
        if attempts < minAttempts:
            minAttempts = attempts

        # Progress
        percent = round((i + 1) / num_to_solve, 3)

        if percent > last_percent:
            last_percent = percent
            if printOut:
                print(f"\rSolving... [{(i + 1) / num_to_solve:6.1%}]", end="", flush=True)
            else:
                yield (i + 1) / num_to_solve

    # Print the stats
    if printOut:
        print()
        print()
        print(f"Successful: {successes}/{total} ({successes / total:6.1%})")
        print(f"Attempts: avg - {totalAttempts / total:.1f}, max - {maxAttempts}, min - {minAttempts}")
        print(f"Under 6 Tries: {under6}/{total} ({under6 / total:6.1%})")
        print(f"Under 6 - Attempts: avg - {under6Attempts / total:.1f}")
        print()

    if not printOut:
        yield under6 / total, under6Attempts / total

    return under6 / total, under6Attempts / total


# Full function to run the many solver and report progress over a pipe
def pool_many_solver(num_to_solve, starting_word, pipe):
    for ret_val in many_solve(num_to_solve, starting_word=starting_word, printOut=False):
        pipe.send(ret_val)
        

# Run many solves with different starting words
def auto_solve(num_to_start, printOut=True):

    # Stat dictionary
    word_results = {}

    # Get the starting words
    starting_words = wordle.dictionary.copy()
    random.shuffle(starting_words)
    starting_words = starting_words[:num_to_start]

    # Clear the screen
    if printOut:
        os.system("cls" if os.name == "nt" else "clear")
        print("Auto Solve")
        print()

    # Get number of cores
    num_cores = min(int(os.cpu_count() / 2), num_to_start)

    # Start a process pool
    processes = []
    words_index = 0
    num_to_solve = len(wordle.dictionary)

    total_to_solve = num_to_start * num_to_solve
    total_done = 0

    with Progress() as progress:
        total_progress = progress.add_task("[green]Solving...", total=total_to_solve)
        # Start the processes
        for i in range(num_cores):
            caller, worker = Pipe()
            p = Process(target=pool_many_solver, args=(num_to_solve, starting_words[words_index], worker))
            p.start()
            task_id = progress.add_task(f" - {starting_words[words_index]}", total=1)
            processes.append({"proc": p, "word": starting_words[words_index], "caller": caller, "progress": task_id})
            words_index += 1

        # Continue adding processes until we have all the starting words in queue
        while words_index < num_to_start:
            for i, p in enumerate(processes):
                try:
                    if p["caller"].poll():
                        c = p["caller"].recv()
                        if type(c) is tuple:
                            success_rate, avg_attempts = c
                            word_results[p["word"]] = (success_rate, avg_attempts)
                            c = 1
                        progress.update(processes[i]["progress"], completed=c)
                        total_done = (words_index - len(processes)) * num_to_solve + sum(t.completed for t in progress.tasks if t.id != total_progress) * num_to_solve
                        progress.update(total_progress, completed=total_done)
                except:
                    pass

                if p["proc"] is not None and not p["proc"].is_alive():
                    # Clean up
                    p["proc"].close()
                    progress.remove_task(p["progress"])

                    # Start new process with new starting word
                    new_caller, worker = Pipe()
                    proc = Process(target=pool_many_solver, args=(num_to_solve, starting_words[words_index], worker))
                    proc.start()
                    task_id = progress.add_task(f" - {starting_words[words_index]}", total=1)
                    processes[i] = {"proc": proc, "word": starting_words[words_index], "caller": new_caller, "progress": task_id}
                    words_index += 1

        # Wait for all the processes to finish
        while any([p["proc"] is not None for p in processes]):
            for i, p in enumerate(processes):
                try:
                    if p["caller"].poll():
                        c = p["caller"].recv()
                        if type(c) is tuple:
                            success_rate, avg_attempts = c
                            word_results[p["word"]] = (success_rate, avg_attempts)
                            c = 1
                        progress.update(processes[i]["progress"], completed=c)
                        total_done = (words_index - len(processes)) * num_to_solve + sum(t.completed for t in progress.tasks if t.id != total_progress) * num_to_solve
                        progress.update(total_progress, completed=total_done)
                except:
                    pass

                if p["proc"] is not None and not p["proc"].is_alive():
                    # Clean up
                    p["proc"].close()
                    p["proc"] = None

        progress.console.log("Auto Solve complete")
        
        progress.refresh()

    # Print the stats
    if printOut:
        print()
        bestStartingWord = max(word_results, key=lambda x: word_results[x][0])
        print(f"Best Starting Word: [green]{bestStartingWord}[/green] ({word_results[bestStartingWord][0]:.1%})")
        lowestAttemptsWord = min(word_results, key=lambda x: word_results[x][1])
        print(f"Lowest Attempts Word: [green]{lowestAttemptsWord}[/green] ({word_results[lowestAttemptsWord][1]:.1f})")
        print()

    return word_results

#
# Main function
#
def main():
    index = 0

    # Start the game
    while True:
        # Print a menu for auto vs manual solve
        # 1. Auto
        # 2. Manual
        # 3. Quit

        # Print menu
        print()
        print("-" + "-" * 30 + "-")
        print("|" + "Wordle Solver".center(30) + "|")
        print("-" + "-" * 30 + "-")
        print()
        print("1. Play Game")
        print("2. Help Me Solve - Solve Wordle Faster!")
        print("3. Solve - Challenge Computer")
        print("4. Many Solve - Solve Lots of Words")
        print("5. Auto Solve - Many Solve with Different Starting Words")
        print("6. Quit")
        print()
        choice = input("> ")
        print()

        # Check the choice
        if choice == "1":
            print("Manual Input, 6 attempts")

            word = wordle.get_word_of_the_day(index)
            index += 1

            # Manual
            for i in range(6):
                # Get input from user
                guess = wordle.get_valid_word()

                result = wordle.check_guess(word, guess)
                print(f'[{i + 1}] {wordle.colored_word(guess, result)}')
                print()

                # if they're done
                if all([r == 'g' for r in result]):
                    print(f"Solved in {i + 1} attempts!")
                    break

            # if we failed
            if not all([r == 'g' for r in result]):
                print(f"Failed to solve the game :(")
                print(f"The word was: {word}")
        elif choice == "2":
            # Run the algorithm to solve the game
            help_me_solve()
            print()
            input("[enter] ")
        elif choice == "3":
            # Challenge Computer
            print("Word to Guess")
            word = wordle.get_valid_word()
            print()
            # Run the algorithm to solve the game
            solve_word(word)
            print()
            input("[enter] ")
        elif choice == "4":
            # Guess a bunch
            print("Many Solve")
            print()
            print("Number of words to solve or (a) for all")
            num_to_solve = None
            while num_to_solve is None:
                num_to_solve = input("> ").strip().lower()
                if num_to_solve == "a":
                    num_to_solve = len(wordle.dictionary)
                else:
                    try:
                        num_to_solve = int(num_to_solve)
                    except:
                        num_to_solve = None
                        print("Invalid number. Try again.")

                    # Make sure the number is in bounds
                    if num_to_solve < 1:
                        num_to_solve = None
                        print("Invalid number. Try again.")
                    if num_to_solve > len(wordle.dictionary):
                        num_to_solve = len(wordle.dictionary)

            many_solve(num_to_solve)
            input("[enter] ")

        elif choice == "5":
            # Auto Solve
            print("Auto Solve")
            print()
            print("Number of starting words to try or (a) for all")
            num_to_start = None
            while num_to_start is None:
                num_to_start = input("> ").strip().lower()
                if num_to_start == "a":
                    num_to_start = len(wordle.dictionary)
                else:
                    try:
                        num_to_start = int(num_to_start)
                    except:
                        num_to_start = None
                        print("Invalid number. Try again.")

                    # Make sure the number is in bounds
                    if num_to_start < 1:
                        num_to_start = None
                        print("Invalid number. Try again.")
                    if num_to_start > len(wordle.dictionary):
                        num_to_start = len(wordle.dictionary)

            # Do the math
            results = auto_solve(num_to_start)

            saveToFile = input("save to file (y/n) ").lower()
            if saveToFile == "y":
                print("Saving to file")
                fileName = f"auto-solve-{time.strftime('%Y-%m-%d-%H-%M-%S')}.csv"
                with open(fileName, "w") as f:
                    f.write("Starting Word,Success Rate,Average Attempts\n")
                    for word in results:
                        f.write(f"{word},{results[word][0]},{results[word][1]}\n")
                print(f"Saved to {fileName}")

        elif choice == "6":
            # Quit
            break
        else:
            print("Invalid choice")


if __name__ == "__main__":
    main()
