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
def getBestWord(tempDict):
    # Get rankings for every word in the given list
    csv_file = csv.reader(open("dict-rank.csv", "r"))

    # The csv is sorted by the most common words, so we can just return the first one we find
    for row in csv_file:
        if row[0] in tempDict:
            return row[0]

    # If we can't find the word, just return the first one in the given dictionary
    return tempDict[0]

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
        test_word = getBestWord(tempDict)

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

# Run many solves
def manySolve(numToSolve, starting_word="ranes", printOut=True):

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
    words = words[:numToSolve]

    # Clear the screen
    if printOut:
        os.system("cls" if os.name == "nt" else "clear")
        print("Many Solve")
        print()
        print("Solving... [  0.0%]", end="", flush=True)

    lastPercent = 0

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
        percent = round((i + 1) / numToSolve, 3)

        if percent > lastPercent:
            lastPercent = percent
            if printOut:
                print(f"\rSolving... [{(i + 1) / numToSolve:6.1%}]", end="", flush=True)
            else:
                yield (i + 1) / numToSolve

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
def poolManySolver(numToSolve, startingWord, pipe):
    for retVal in manySolve(numToSolve, starting_word=startingWord, printOut=False):
        pipe.send(retVal)
        

# Run many solves with different starting words
def autoSolve(numToStart, printOut=True):

    # Stat dictionary
    wordResults = {}

    # Get the starting words
    startingWords = wordle.dictionary.copy()
    random.shuffle(startingWords)
    startingWords = startingWords[:numToStart]

    # Clear the screen
    if printOut:
        os.system("cls" if os.name == "nt" else "clear")
        print("Auto Solve")
        print()
        
    # Get number of cores
    numCores = min(int(os.cpu_count() / 2), numToStart)

    # Start a process pool
    processes = []
    wordsIndex = 0
    numToSolve = len(wordle.dictionary)

    totalToSolve = numToStart * numToSolve
    totalDone = 0
        
    with Progress() as progress:
        totalProgress = progress.add_task("[green]Solving...", total=totalToSolve)
        # Start the processes
        for i in range(numCores):
            caller, worker = Pipe()
            p = Process(target=poolManySolver, args=(numToSolve, startingWords[wordsIndex], worker))
            p.start()
            id = progress.add_task(f" - {startingWords[wordsIndex]}", total=1)
            processes.append({"proc": p, "word": startingWords[wordsIndex], "caller": caller, "progress": id})
            wordsIndex += 1

        # Continue adding processes until we have all the starting words in queue
        while wordsIndex < numToStart:
            for i, p in enumerate(processes):
                try:
                    if p["caller"].poll():
                        c = p["caller"].recv()
                        if type(c) is tuple:
                            successRate, avgAttempts = c
                            wordResults[p["word"]] = (successRate, avgAttempts)
                            c = 1
                        progress.update(processes[i]["progress"], completed=c)
                        totalDone = (wordsIndex - len(processes)) * numToSolve + sum(t.completed for t in progress.tasks if t.id != totalProgress) * numToSolve
                        progress.update(totalProgress, completed=totalDone)
                except:
                    pass

                if p["proc"] is not None and not p["proc"].is_alive():
                    # Clean up
                    p["proc"].close()
                    progress.remove_task(p["progress"])

                    # Start new process with new starting word
                    newCaller, worker = Pipe()
                    proc = Process(target=poolManySolver, args=(numToSolve, startingWords[wordsIndex], worker))
                    proc.start()
                    id = progress.add_task(f" - {startingWords[wordsIndex]}", total=1)
                    processes[i] = {"proc": proc, "word": startingWords[wordsIndex], "caller": newCaller, "progress": id}
                    wordsIndex += 1

        # Wait for all the processes to finish
        while any([p["proc"] is not None for p in processes]):
            for i, p in enumerate(processes):
                try:
                    if p["caller"].poll():
                        c = p["caller"].recv()
                        if type(c) is tuple:
                            successRate, avgAttempts = c
                            wordResults[p["word"]] = (successRate, avgAttempts)
                            c = 1
                        progress.update(processes[i]["progress"], completed=c)
                        totalDone = (wordsIndex - len(processes)) * numToSolve + sum(t.completed for t in progress.tasks if t.id != totalProgress) * numToSolve
                        progress.update(totalProgress, completed=totalDone)
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
        bestStartingWord = max(wordResults, key=lambda x: wordResults[x][0])
        print(f"Best Starting Word: [green]{bestStartingWord}[/green] ({wordResults[bestStartingWord][0]:.1%})")
        lowestAttemptsWord = min(wordResults, key=lambda x: wordResults[x][1])
        print(f"Lowest Attempts Word: [green]{lowestAttemptsWord}[/green] ({wordResults[lowestAttemptsWord][1]:.1f})")
        print()

    return wordResults

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
        print("2. Solve - Challenge Computer")
        print("3. Many Solve - Solve Lots of Words")
        print("4. Auto Solve - Many Solve with Different Starting Words")
        print("5. Quit")
        print()
        choice = input("> ")
        print()

        # Check the choice
        if choice == "1":
            print("Manual Input, 6 attempts")

            word = wordle.get_word_of_the_day(index)
            index = index + 1
            
            # Manual
            for i in range(6):
                # Get input from user
                guess = wordle.get_valid_word()

                result = wordle.check_guess(word, guess)
                # result = try_word(word, index).get("result")
                print(f'[{i + 1}] {wordle.colored_word(guess, result)}')
                
                print()

                # if they're done
                if all([r == 'g' for r in result]):
                    print(f"Solved in {i + 1} attempts!")
                    break
            
            # if we failed
            if not all([r == 'g' for r in result]):
                print(f"Failed to solve the game :(")
                print(f"The word was {word} {result}")
                
            index = index + 1
        elif choice == "2":
            # Challenge Computer
            print("Word to Guess")
            word = wordle.get_valid_word()
            print()
            # Run the algorithm to solve the game
            solve_word(word)
            print()
            input("[enter] ")
        elif choice == "3":
            # Guess a bunch
            print("Many Solve")
            print()
            print("Number of words to solve or (a) for all")
            numToSolve = None
            while numToSolve is None:
                numToSolve = input("> ").strip().lower()
                if numToSolve == "a":
                    numToSolve = len(wordle.dictionary)
                else:
                    try:
                        numToSolve = int(numToSolve)
                    except:
                        numToSolve = None
                        print("Invalid number. Try again.")

                    # Make sure the number is in bounds
                    if numToSolve < 1:
                        numToSolve = None
                        print("Invalid number. Try again.")
                    if numToSolve > len(wordle.dictionary):
                        numToSolve = len(wordle.dictionary)

            manySolve(numToSolve)
            input("[enter] ")

        elif choice == "4":
            # Auto Solve
            print("Auto Solve")
            print()
            print("Number of starting words to try or (a) for all")
            numToStart = None
            while numToStart is None:
                numToStart = input("> ").strip().lower()
                if numToStart == "a":
                    numToStart = len(wordle.dictionary)
                else:
                    try:
                        numToStart = int(numToStart)
                    except:
                        numToStart = None
                        print("Invalid number. Try again.")

                    # Make sure the number is in bounds
                    if numToStart < 1:
                        numToStart = None
                        print("Invalid number. Try again.")
                    if numToStart > len(wordle.dictionary):
                        numToStart = len(wordle.dictionary)

            # Do the math
            results = autoSolve(numToStart)

            saveToFile = input("save to file (y/n) ").lower()
            if saveToFile == "y":
                print("Saving to file")
                fileName = f"auto-solve-{time.strftime('%Y-%m-%d-%H-%M-%S')}.csv"
                with open(fileName, "w") as f:
                    f.write("Starting Word,Success Rate,Average Attempts\n")
                    for word in results:
                        f.write(f"{word},{results[word][0]},{results[word][1]}\n")
                print(f"Saved to {fileName}")

        elif choice == "5":
            # Quit
            break
        else:
            print("Invalid choice")


if __name__ == "__main__":
    main()
