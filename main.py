# Wordle Solver
# Joshua Taylor 2024

# Import the necessary libraries
import os
import csv
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
def solve_word(word, starting_word = "ranes", printOut=True):
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
        print("2. Challenge Computer")
        print("3. Auto Solve")
        print("4. Quit")
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
            print("Auto Solve")
            print()
            print("Number of words to solve (a) for all")
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

            os.system("cls" if os.name == "nt" else "clear")

            successes = 0
            total = 0
            totalAttempts = 0
            maxAttempts = 0
            minAttempts = 1000
            under6 = 0

            print("Auto Solve")
            print()
            print("Solving... [  0.0%]", end="", flush=True)
            for i in range(numToSolve):
                success, attempts = solve_word(wordle.get_word_of_the_day(i), printOut=False)
                
                if success:
                    successes += 1
                    if attempts <= 6:
                        under6 += 1
                total += 1
                totalAttempts += attempts
                if attempts > maxAttempts:
                    maxAttempts = attempts
                if attempts < minAttempts:
                    minAttempts = attempts

                print(f"\rSolving... [{(i + 1) / numToSolve:6.1%}]", end="", flush=True)

            print()
            print()
            print(f"Successful: {successes}/{total} ({successes / total:6.1%})")
            print(f"Under 6 Tries: {under6}/{total} ({under6 / total:6.1%})")
            print(f"Attempts: avg - {totalAttempts / total:.1f}, max - {maxAttempts}, min - {minAttempts}")
            print()
            input("[enter] ")
        elif choice == "4":
            # Quit
            break
        else:
            print("Invalid choice")


if __name__ == "__main__":
    main()
