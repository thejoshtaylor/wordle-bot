# This script is going to log into the NY Times World game and solve the game in the fewest moves possible.
# There is a dictionary provided of all valid words in the game.
# The link for the game is: https://www.nytimes.com/wordle/index.html
# This will all be done in the background without opening a browser.
# At the end, the script will output the grid of failed attempts and the final solution.
# Posible inputs: 5 letter words
# The game has 6 attempts to solve the game
#
# Steps for the script:
# 1. Log into the game
# 2. Make sure that the game is ready to be played
# 3. Try to solve the game in the fewest attempts possible

# Importing the necessary libraries
import requests
import json
import time
import random
import itertools
import os

# Read in the dictionary.txt
with open("dictionary.txt", "r") as f:
    dictionary = f.read().splitlines()

values = {
    "possibleLetters": 5.0,
    "testedLetters": -2.828125,
    "usedLetters": 0.859375,
    "flatUsedLetters": 2.75,
    "rightLetters": -0.125,
    "flatRightLetters": 2.5,
    "wrongLetters": -1.0,
    "possibleWords": 6.75,
    "numberOfGuesses": 0.09375,
}


# Try a word
def try_word(word, index=0):
    # Make a get request and parse the response
    r = requests.post(
        f"http://127.0.0.1:5000/guess",
        json={"guess": word, "index": index},
        headers={"Content-Type": "application/json"},
    )
    try:
        response = r.json()
    except:
        # print(r.text)
        raise

    return response


# Find the word that we can learn the most from
def findBestWord(possibleWords, allWords, history):
    testedLetters = set()
    wrongLetters = set()
    rightLetters = [set()] * 5
    usedLetters = [set()] * 5

    for word, colors in history:
        for i, l in enumerate(word):
            testedLetters.add(l)
            if colors[i] == "grey":
                wrongLetters.add(l)
            elif colors[i] == "yellow":
                usedLetters[i].add(l)
            else:
                rightLetters[i].add(l)

    # Let's solve:
    # - Where does each yellow letter go?
    # - For slots we haven't found yet, what letters are possible?
    # - Which letters in these spots are most likely?
    # - Is this a letter we're found or one we haven't tried?

    # If multiple letters are in contention for the same spot, we can try to test as many of those letters as possible

    # Find all possible letters for each spot
    possibleLetters = [set()] * 5
    for word in possibleWords:
        for i, l in enumerate(word):
            possibleLetters[i].add(l)

    flatPossibleLetters = set(itertools.chain(*possibleLetters))

    flatUsedLetters = set(itertools.chain(*usedLetters))
    flatRightLetters = set(itertools.chain(*rightLetters))

    # Words that have yellow letters in other spots have a higher score
    # Words that maximize the number of possible letters in each spot have a higher score
    # Words that have letters we haven't tested have a higher score

    global values

    bestScore = -100000
    bestWord = "trace"

    for word in allWords:
        score = 0
        for i, l in enumerate(word):

            if l in possibleLetters[i]:
                score += values["possibleLetters"]
            if l in testedLetters:
                score += values["testedLetters"]

            if l in usedLetters[i]:
                score += values["usedLetters"]
            elif l in flatUsedLetters:
                score += values["flatUsedLetters"]

            if l in rightLetters[i]:
                score += values["rightLetters"]
            elif l in flatRightLetters:
                score += values["flatRightLetters"]

            if l in wrongLetters:
                score += values["wrongLetters"]

        if word in possibleWords:
            score += values["possibleWords"]
            score += values["numberOfGuesses"] * len(history)

        # wordScores[word] = score
        if score > bestScore:
            bestScore = score
            bestWord = word

    # Get the word with the highest score
    # bestWord = max(wordScores, key=wordScores.get)

    return bestWord


def solve_word(index=0, getNextWord=findBestWord, testWord=try_word, printOut=True):
    starting_word = "ranes"

    # Initialize the variables
    attempts = 0
    solved = False
    failed_attempts = []
    bad_words = []

    test_word = starting_word

    tempDict = dictionary.copy()

    err = "Out of tries"

    # Start the game
    while attempts < 16 and not solved:
        # Get the word to try
        if printOut:
            print(f"Attempt {attempts + 1}: {test_word}", end="")

        # Try the word
        try:
            # response = try_word(test_word, index)
            response = testWord(test_word, index)
        except Exception as e:
            print(e)
            break

        # Check if it's a string
        if "error" in response:
            err = response.get("error")
            # print(response)
            if "not in dictionary" in err:
                tempDict.remove(test_word)
                bad_words.append(test_word)
                if len(tempDict) == 0:
                    err = "out of words"
                    # print('No more words to try')
                    break
                # attempts += 1
                test_word = random.choice(tempDict)
                if printOut:
                    print("\r", end="")
                continue
            else:
                if printOut:
                    print()
                break
        # print()

        # Check the result from the server
        result = response.get("result")

        must_have = []
        must_not_have = []

        allGreen = True

        toPrint = ["", "", "", "", ""]

        # Go through each letter in the returned result
        for a in result:
            if a.get("color") == "grey":
                toPrint[a.get("index")] = a.get("letter")
                # must_not_have.append((a.get('index'), a.get('letter')))
                allGreen = False
            elif a.get("color") == "yellow":
                toPrint[a.get("index")] = "\033[93m" + a.get("letter") + "\033[0m"
                must_have.append((-1, a.get("letter")))
                must_not_have.append((a.get("index"), a.get("letter")))
                allGreen = False
            elif a.get("color") == "green":
                toPrint[a.get("index")] = "\033[92m" + a.get("letter") + "\033[0m"
                must_have.append((a.get("index"), a.get("letter")))

        for a in result:
            if a.get("color") == "grey":
                found = False
                for _, letter in must_have:
                    if letter == a.get("letter"):
                        found = True
                # If it's not in the must_haves, add it to the must_not_haves
                if not found:
                    must_not_have.append((-1, a.get("letter")))

        # Print the result
        if printOut:
            print(
                f'\rAttempt {attempts + 1}: {"".join(toPrint)} -> {response.get("word")}',
                end="",
            )

        # Check if we solved it
        if allGreen:
            solved = True
            break

        failed_attempts.append(
            (
                test_word,
                [a.get("color") for a in sorted(result, key=lambda x: x.get("index"))],
            )
        )
        # if test_word in tempDict:
        #     tempDict.remove(test_word)

        # Filter the dictionary
        for ind, letter in must_not_have:
            if ind == -1:
                tempDict = [word for word in tempDict if letter not in word]
            else:
                tempDict = [word for word in tempDict if word[ind] != letter]

        for ind, letter in must_have:
            if ind == -1:
                tempDict = [word for word in tempDict if letter in word]
            else:
                tempDict = [word for word in tempDict if word[ind] == letter]

        if printOut:
            print(f" [{len(tempDict)} words left]")

        if len(tempDict) == 0:
            err = "no matching words"
            # print('No more words to try')
            break

        # Find the word that we can learn the most from
        # test_word = random.choice(tempDict)
        # test_word = findBestWord(tempDict, dictionary, failed_attempts)
        test_word = getNextWord(tempDict, dictionary, failed_attempts)

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

    # Remove bad words from the dictionary
    if printOut:
        print()
    for word in bad_words:
        print(f"[removing {word} from the dictionary]")
        dictionary.remove(word)

    # Write the dictionary back to the file
    # with open('dictionary.txt', 'w') as f:
    #     f.write('\n'.join(dictionary))

    return attempts + 1

def colorWord(result):
    toPrint = ["", "", "", "", ""]

    # Go through each letter in the returned result
    for a in result:
        if a.get("color") == "grey":
            toPrint[a.get("index")] = a.get("letter")
        elif a.get("color") == "yellow":
            toPrint[a.get("index")] = "\033[93m" + a.get("letter") + "\033[0m"
        elif a.get("color") == "green":
            toPrint[a.get("index")] = "\033[92m" + a.get("letter") + "\033[0m"

    return ''.join(toPrint)

def main():
    index = 0

    os.system("clear")

    # Start the game
    while True:
        # Print a menu for auto vs manual solve
        # 1. Auto
        # 2. Manual
        # 3. Quit

        # Print menu
        print("|" + "-" * 30 + "|")
        print("|" + "Wordle Solver".center(30) + "|")
        print("|" + "-" * 30 + "|")
        print()
        print("1. Auto")
        print("2. Manual")
        print("3. Quit")
        print()
        choice = input("> ")

        # Check the choice
        if choice == "1":
            # Auto
            attempts = solve_word(index)
            index = index + 1
            print()
        elif choice == "2":
            # Manual
            for i in range(6):
                print("Enter the word to test: ", end="")
                word = input()
                result = try_word(word, index)
                print(f'[{i + 1}] {colorWord(result)}')
                
                print()
                
            index = index + 1
        elif choice == "3":
            # Quit
            break
        else:
            print("Invalid choice")


if __name__ == "__main__":
    main()
