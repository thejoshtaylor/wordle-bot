# This script is intended to train the model to solve the wordle faster

# import main

import random
import signal
import pickle
import time

# import multiprocessing.pool as pool

# Add parent folder to path
import sys
# sys.path.append('..')

# from wordle_server import main as wordle

# Get the average number of guesses to solve the wordle with just a random guess
# def getAverageRandomGuesses(maxIndex=10, numTrials=100):
#     start = time.time()
#     totalGuesses = 0
#     for index in range(maxIndex):
#         for i in range(numTrials):
#             if i % 10 == 0:
#                 print(f'\r[{index + 1:3d}/{maxIndex}] -> [{i:4d}/{numTrials}]', end='', flush=True)
#             totalGuesses += main.solve_word(index=index, getNextWord=lambda x, y, z: str(random.seed() or random.choice(x)), testWord=wordle.checkGuess, printOut=False)
            
#     print(f'\r[{maxIndex:3d}/{maxIndex}] -> [{numTrials:4d}/{numTrials}] (took {time.time() - start:.2f} seconds)')
#     return totalGuesses / (numTrials * maxIndex)

# Get the average number of guesses to solve the wordle with the model
# def getAverageModelGuesses(maxIndex=10):
#     start = time.time()
#     totalGuesses = 0
#     for index in range(maxIndex):
#         print(f'\r[{index + 1:3d}/{maxIndex}]', end='', flush=True)
#         totalGuesses += main.solve_word(index=index, testWord=wordle.checkGuess, printOut=False)
            
#     print(f'\r[{maxIndex:3d}/{maxIndex}] (took {time.time() - start:.2f} seconds)')
#     return totalGuesses / maxIndex

# Run through to find the average number of guesses for each of the models
# # def trials(numPerModel=100):
#     print()
#     print('-----------------')
#     print('Starting Training')
#     print('-----------------')
#     print()

#     print('Random Guesses')
#     randomGuesses = getAverageRandomGuesses(maxIndex=numPerModel)
#     print(randomGuesses)

#     trainStart = time.time()
#     bestGuesses = 0

#     # With default values
#     print('Model Guesses')
#     lastGuesses = getAverageModelGuesses(maxIndex=numPerModel)
#     print(lastGuesses)

#     # Optimize each of the values
#     for key in main.values:
#         print()
#         print('-' * 50)
#         print(f'Optimizing: {key}')
#         print(f'Current Value: {main.values[key]}')
#         print('-' * 50)
#         bestValue = main.values[key]
#         bestGuesses = lastGuesses

#         # defaultValue = values[key]

#         # lastGuesses = getAverageModelGuesses(maxIndex=numPerModel)

#         incrementer = 2

#         pastValues = [main.values[key]]
#         pastGuesses = [lastGuesses]

#         same = False

#         for i in range(100):
#             main.values[key] += incrementer


#             print(f'[{i + 1:3d}/100] -> Set {key} to {main.values[key]}')
            
#             if main.values[key] in pastValues:
#                 guesses = pastGuesses[pastValues.index(main.values[key])]
#             else:
#                 guesses = getAverageModelGuesses(maxIndex=numPerModel)

#                 pastValues.append(main.values[key])
#                 pastGuesses.append(guesses)

#             print(f'Average Guesses Required: {guesses}')
#             print()

#             if guesses == lastGuesses:
#                 if same:
#                     print('No change in average guesses, stopping')
#                     main.values[key] -= incrementer
#                     break
#                 same = True
#             else:
#                 same = False

#             if guesses < bestGuesses:
#                 bestGuesses = guesses
#                 bestValue = main.values[key]

#             if guesses > lastGuesses:
#                 # Flip incrementing direction
#                 incrementer = -incrementer
#                 # If we've switch before, half the incrementer
#                 if i != 0:
#                     incrementer = incrementer / 2
#                 else:
#                     # Go back to last value so we just go past it
#                     main.values[key] += incrementer
#                     guesses = lastGuesses

#             lastGuesses = guesses

#         # print()


#         main.values[key] = bestValue
#         lastGuesses = bestGuesses
#         print(f'Best value for {key}: {bestValue} ({bestGuesses} guesses)')

#     print()
#     print()
#     print('-' * 50)
#     print('Training Complete')
#     print(f'Done in {round((time.time() - trainStart) / 60 - 0.5)}:{round((time.time() - trainStart) % 60):02d} minutes')
#     print('-' * 50)
#     print()
#     print('Best Guess Average Achieved: ', bestGuesses)
#     print('Random Guess Average:        ', randomGuesses)
#     print()
#     print('Best Values:')
#     print()
#     print('values =', str(main.values).replace(', ', ',\n'))
#     print()
#     print()

def checkGuess(guess, actualWord):
    # Start preparing the result
    result = []

    # Convert string to list of characters
    partialWord = list(actualWord)

    # Get the details of the guess
    for i in range(len(guess)):
        temp = {
            'index': i,
            'letter': guess[i],
            'color': 'grey'
        }
        if guess[i] == partialWord[i]:
            temp['color'] = 'green'
            partialWord[i] = ' '
        result.append(temp)

    for i in range(len(guess)):
        if guess[i] in partialWord and result[i]['color'] != 'green':
            result[i]['color'] = 'yellow'
    
    return result

# Get the remaining words from the result
def getRemainingWords(dictionary, result):
    must_have = []
    must_not_have = []

    tempDict = dictionary.copy()

    # Go through each letter in the returned result
    for a in result:
        if a.get("color") == "yellow":
            must_have.append((-1, a.get("letter")))
            must_not_have.append((a.get("index"), a.get("letter")))
        elif a.get("color") == "green":
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

    return tempDict

times = [0.0] * 10

# Check the guess and get the remaining words
def checkGuessAndGetRemainingWords(dictionary, guess, actualWord):
    global times

    start = time.time()
    # More efficient to do it in one go
    # tempDict = dictionary.copy()
    times[0] += time.time() - start
    start = time.time()

    letters = list(actualWord)
    times[1] += time.time() - start
    start = time.time()

    exactly = []
    exactlyNot = []
    justNot = set()
    justHas = set()

    # Check each letter in the guess to see if it's in the word
    for i, letter in enumerate(guess):
        # Green
        if letters[i] == letter:
            exactly.append((i, letter))
            # tempDict = [word for word in tempDict if word[i] == letter]
            letters[i] = ''

    times[2] += time.time() - start
    start = time.time()
    
    # After we have all the greens found, we can check the rest
    for i, letter in enumerate(guess):
        # Yellow
        if letter in actualWord:
            exactlyNot.append((i, letter))
            justHas.add(letter)
            # tempDict = [word for word in tempDict if letter in word]

            # Only make a yellow for the first instance of the letter
            letters[i] = ''
        # Grey
        elif letter not in [x for (_, x) in exactly]:
            justNot.add(letter)
            # tempDict = [word for word in tempDict if letter not in word]

    times[3] += time.time() - start
    start = time.time()

    # Filter the dictionary
    # tempDict = dictionary.copy()
    # foundWords = 0
            
    tempDict = dictionary.copy()
    # tempDict = filter(lambda _: True, dictionary)
    
    # Count the number of words that fit the criteria
    for ind, letter in exactly:
        tempDict = [word for word in tempDict if word[ind] == letter]
        # tempDict = filter(lambda word: word[ind] == letter, tempDict)
    for letter in justHas:
        tempDict = [word for word in tempDict if letter in word]
        # tempDict = filter(lambda word: letter in word, tempDict)
    for ind, letter in exactlyNot:
        tempDict = [word for word in tempDict if word[ind] != letter]
        # tempDict = filter(lambda word: word[ind] != letter, tempDict)
    for letter in justNot:
        tempDict = [word for word in tempDict if letter not in word]
        # tempDict = filter(lambda word: letter not in word, tempDict)
    
    times[4] += time.time() - start
    start = time.time()

    foundWords = len(tempDict)
    # foundWords = sum(1 for _ in tempDict)

    # del tempDict

    # tempDict = [word for word in dictionary if all(word[ind] == letter for ind, letter in exactly)]
    # tempDict = [word for word in tempDict if all(word[ind] != letter for ind, letter in exactlyNot)]
    # tempDict = [word for word in tempDict if all(letter in word for letter in justHas)]
    # tempDict = [word for word in tempDict if all(letter in word for letter in justNot)]
    # foundWords = len(tempDict)
    # for word in dictionary:
    #     if all(word[ind] == letter for ind, letter in exactly):
    #         if all(word[ind] != letter for ind, letter in exactlyNot):
    #             if all(letter in word for letter in justHas):
    #                 if all(letter in word for letter in justNot):
    #                     # tempDict.append(word)
    #                     foundWords += 1
    
    times[5] += time.time() - start
    
    return foundWords

stopSig = False


# Find the word that reduces the number of words left in the dictionary the most, on average
def findHighestReductionWord(dictionary, results=None):
    global stopSig
    global times

    if results is None:
        results = { }
    
    print()
    print('-----------------')
    print('Starting Training')
    print('-----------------')
    print()

    # Count how many words are in the results
    startIndex = 0
    for word in results:
        startIndex += 1
    
    # Start variables
    startTime = time.time()

    startSize = len(dictionary)

    for i, trialWord in enumerate(dictionary):
        # Skip over words that we've already tested
        if i < startIndex:
            continue
        elif i == startIndex and startIndex != 0:
            print(f'Starting at "{trialWord}"')
            print()
        # if i >= 5:
        #     break
        print(f'\r[{i + 1:5d}/{startSize}] - [    0/{startSize}] => {trialWord}', end='', flush=True)

        avgSize = 0.0
        minSize = startSize
        maxSize = 0

        # Test this word on every word in the dictionary
        for x, word in enumerate(dictionary):
            # Status
            if x % 100 == 0:
                print(f'\r[{i + 1:5d}/{startSize}] - [{x:5d}/{startSize}] => {trialWord} -> {word}', end='', flush=True)

            # Test the word
            words = checkGuessAndGetRemainingWords(dictionary, trialWord, word)
            # wordsLeft = getRemainingWords(dictionary, result)
            if words < minSize and words != 0:
                minSize = words
            if words > maxSize:
                maxSize = words

            avgSize += float(words)

        # Get the average number of words left
        avgSize /= float(len(dictionary))

        results[trialWord] = (minSize, maxSize, avgSize)

        # Keep the 20 words that have the lowest average number of words left
        # if len(top25Best) > 25:
        #     top25Best = {k: v for k, v in sorted(top25Best.items(), key=lambda item: item[1])[:25]}

        # Print remaining time
        # Skip over current printing
        print('\r', end='')
        print(' ' * (47 + 5), end='')
        # Print time in a dd:hh:mm:ss format
        timeTaken = time.time() - startTime
        numDone = i - startIndex + 1
        numLeft = startSize - numDone
        # timeLeft = round(timeTaken / (i + 1) * (startSize - i - 1))
        # timeLeft = round(timeTaken / numDone * (startSize - numDone))
        timeLeft = round(timeTaken / numDone * numLeft)
        
        days, r = divmod(timeLeft, 86400)
        hours, r = divmod(r, 3600)
        minutes, seconds = divmod(r, 60)

        print(f'{days:02}:{hours:02}:{minutes:02}:{seconds:02} left ', end='')

        # DEBUG
        print('  [', end='')
        for t in times:
            print(f'{t:.2f}s, ', end='')
        print(']', end='')

        if stopSig:
            break
    
    # Sort the results by average size
    results = {k: v for k, v in sorted(results.items(), key=lambda item: item[1][2])}

    print()
    # Print the best words
    for i, word in enumerate(results):
        if i >= 25:
            break
        print(f'{i + 1:2}. {word} [{results[word][0]:5}, {results[word][1]:5}, {results[word][2]:7.1f}]')
    print()

    return results

# Handle the signal
def signal_handler(sig, frame):
    global stopSig
    print()
    print()
    print('You pressed Ctrl+C!', flush = True)
    print('Stopping at end of this word.', flush = True)
    print()
    stopSig = True
    # time.sleep(1)
    # sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    # signal.signal(signal.SIGTERM, signal_handler)
    # trials()
    with open("dictionary.txt", "r") as f:
        dictionary = f.read().splitlines()

    # check if the pickle file exists
    print()
    try:
        with open('results.pkl', 'rb') as f:
            res = pickle.load(f)
            print('Results loaded from pickle')
    except:
        res = None
        print('Results not found, running training')

    if res is not None:
        # Count how many words are in the results
        count = 0
        for word in res:
            count += 1
        print(f'{count} words loaded')
        print()


    res = findHighestReductionWord(dictionary, res)


    with open('results.pkl', 'wb') as f:
        pickle.dump(res, f)

    print('Results pickled')