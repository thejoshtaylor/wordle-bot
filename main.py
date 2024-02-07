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
with open('dictionary.txt', 'r') as f:
    dictionary = f.read().splitlines()

# Try a word
def try_word(word, index=0):
    # Make a get request and parse the response
    r = requests.post(f'http://127.0.0.1:5000/guess', json={'guess': word, 'index': index}, headers={'Content-Type': 'application/json'})
    try:
        response = r.json()
    except:
        print(r.text)
        raise

    return response

def solve_word(index=0):# Initialize the game
    starting_word = 'trace'

    # Initialize the variables
    attempts = 0
    solved = False
    failed_attempts = []
    bad_words = []

    test_word = starting_word

    tempDict = dictionary.copy()

    err = 'Out of tries'

    # Start the game
    while attempts < 16 and not solved:
        # Get the word to try
        print(f'Attempt {attempts + 1}: {test_word}', end='')

        # Try the word
        try:
            response = try_word(test_word, index)
        except Exception as e:
            print(e)
            break

        # Check if it's a string
        if 'error' in response:
            err = response.get('error')
            # print(response)
            if 'not in dictionary' in err:
                tempDict.remove(test_word)
                bad_words.append(test_word)
                if len(tempDict) == 0:
                    err = 'out of words'
                    # print('No more words to try')
                    break
                # attempts += 1
                test_word = random.choice(tempDict)
                print('\r', end='')
                continue
            else:
                print()
                break
        # print()

        # Check the result from the server
        result = response.get('result')

        must_have = []
        must_not_have = []

        allGreen = True

        toPrint = ['', '', '', '', '']

        # Go through each letter in the returned result
        for a in result:
            if a.get('color') == 'grey':
                toPrint[a.get('index')] = a.get('letter')
                # must_not_have.append((a.get('index'), a.get('letter')))
                allGreen = False
            elif a.get('color') == 'yellow':
                toPrint[a.get('index')] = '\033[93m' + a.get('letter') + '\033[0m'
                must_have.append((-1, a.get('letter')))
                must_not_have.append((a.get('index'), a.get('letter')))
                allGreen = False
            elif a.get('color') == 'green':
                toPrint[a.get('index')] = '\033[92m' + a.get('letter') + '\033[0m'
                must_have.append((a.get('index'), a.get('letter')))

        for a in result:
            if a.get('color') == 'grey':
                found = False
                for _, letter in must_have:
                    if letter == a.get('letter'):
                        found = True
                # If it's not in the must_haves, add it to the must_not_haves
                if not found:
                    must_not_have.append((-1, a.get('letter')))

        # Print the result
        print(f'\rAttempt {attempts + 1}: {"".join(toPrint)} -> {response.get("word")}', end='')

        # Check if we solved it
        if allGreen:
            solved = True
            break

        failed_attempts.append((test_word, [a.get('color') for a in sorted(result, key=lambda x: x.get('index'))]))
        if test_word in tempDict:
            tempDict.remove(test_word)

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
                

        print(f' [{len(tempDict)} words left]')

        if len(tempDict) == 0:
            err = 'no matching words'
            # print('No more words to try')
            break

        # Find the word that we can learn the most from
        # test_word = random.choice(tempDict)
        test_word = findBestWord(tempDict, dictionary, failed_attempts)

        # Update the attempts
        attempts += 1

    # Done.
    print()
    # Check if we solved it
    if not solved:
        print(f'Failed to solve the game :( [{err}]')
    else:
        print(f'Solved in {attempts + 1} attempts! [{test_word}]')

    # Remove bad words from the dictionary
    print()
    for word in bad_words:
        print(f'[removing {word} from the dictionary]')
        dictionary.remove(word)
    
    # Write the dictionary back to the file
    with open('dictionary.txt', 'w') as f:
        f.write('\n'.join(dictionary))

    return index + 1

# Find the word that we can learn the most from
def findBestWord(possibleWords, allWords, history):
    testedLetters = set()
    wrongLetters = set()
    rightLetters = [set()] * 5
    usedLetters = [set()] * 5

    for word, colors in history:    
        for i, l in enumerate(word):
            testedLetters.add(l)
            if colors[i] == 'grey':
                wrongLetters.add(l)
            elif colors[i] == 'yellow':
                usedLetters[i].add(l)
            else:
                rightLetters[i].add(l)

    # mostCommonLettersInDictionary = {}
    # for word in words:
    #     for l in word:
    #         if l not in mostCommonLettersInDictionary:
    #             mostCommonLettersInDictionary[l] = 0
    #         mostCommonLettersInDictionary[l] += 1

    # # sort common letters
    # mostCommonLettersInDictionary = sorted(mostCommonLettersInDictionary.items(), key=lambda x: x[1], reverse=True)

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

    wordScores = {}
    for word in allWords:
        score = 0
        for i, l in enumerate(word):
            
            if l in possibleLetters[i]:
                score += 2
            if l in testedLetters:
                score -= 0.25

            if l in usedLetters[i]:
                score += 0.5
            elif l in flatUsedLetters:
                score += 1

            if l in rightLetters[i]:
                score -= 0
            elif l in flatRightLetters:
                score -= 0.75

            if l in wrongLetters:
                score -= 20

        if word in possibleWords:
            score += 2

        wordScores[word] = score

    # Get the word with the highest score
    bestWord = max(wordScores, key=wordScores.get)



    # Solve entropy by putting letters in specific spots
    # entropy = {}
    # for word in possibleWords:
    #     for i, l in enumerate(word):
    #         if i not in entropy:
    #             entropy[i] = {}
    #         if l not in entropy[i]:
    #             entropy[i][l] = 0

    #         if l in testedLetters:
    #             entropy[i][l] += 0.5
    #         else:
    #             entropy[i][l] += 1

    #         if l in usedLetters:
    #             entropy[i][l] += 0.5
    #         if l in wrongLetters:
    #             entropy[i][l] -= 1
    #         if l in rightLetters:
    #             entropy[i][l] -= 1

    #         entropy[i][l] += 1

    # # Sort entropy to maximize it
    # # entropy = sorted(entropy.items(), key=lambda x: len(x[1]), reverse=True)

    # # Find the word that has the maximum entropy
    # bestWord = None
    # bestWordEntropy = 0
    # for word in possibleWords:
    #     e = 0
    #     for i, l in enumerate(word):
    #         e += entropy[i][l]
    #     if e > bestWordEntropy:
    #         bestWordEntropy = e
    #         bestWord = word

    return bestWord        

    

def main():
    index = 0

    # Start the game
    while True:
        print('Starting a new game...')
        index = solve_word(index)
        print("Press enter to start a new game, [q] to quit")
        temp = input()
        if temp.lower() == 'q':
            break
        print()


if __name__ == '__main__':
    main()