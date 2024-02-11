# This script is intended to train the model to solve the wordle faster

import main

import random
import time

# Add parent folder to path
import sys
sys.path.append('..')

from wordle_server import main as wordle

# Get the average number of guesses to solve the wordle with just a random guess
def getAverageRandomGuesses(maxIndex=10, numTrials=100):
    start = time.time()
    totalGuesses = 0
    for index in range(maxIndex):
        for i in range(numTrials):
            if i % 10 == 0:
                print(f'\r[{index + 1:3d}/{maxIndex}] -> [{i:4d}/{numTrials}]', end='', flush=True)
            totalGuesses += main.solve_word(index=index, getNextWord=lambda x, y, z: str(random.seed() or random.choice(x)), testWord=wordle.checkGuess, printOut=False)
            
    print(f'\r[{maxIndex:3d}/{maxIndex}] -> [{numTrials:4d}/{numTrials}] (took {time.time() - start:.2f} seconds)')
    return totalGuesses / (numTrials * maxIndex)

# Get the average number of guesses to solve the wordle with the model
def getAverageModelGuesses(maxIndex=10):
    start = time.time()
    totalGuesses = 0
    for index in range(maxIndex):
        print(f'\r[{index + 1:3d}/{maxIndex}]', end='', flush=True)
        totalGuesses += main.solve_word(index=index, testWord=wordle.checkGuess, printOut=False)
            
    print(f'\r[{maxIndex:3d}/{maxIndex}] (took {time.time() - start:.2f} seconds)')
    return totalGuesses / maxIndex

# Run through to find the average number of guesses for each of the models
def trials(numPerModel=100):
    print()
    print('-----------------')
    print('Starting Training')
    print('-----------------')
    print()

    print('Random Guesses')
    randomGuesses = getAverageRandomGuesses(maxIndex=numPerModel)
    print(randomGuesses)

    trainStart = time.time()
    bestGuesses = 0

    # With default values
    print('Model Guesses')
    lastGuesses = getAverageModelGuesses(maxIndex=numPerModel)
    print(lastGuesses)

    # Optimize each of the values
    for key in main.values:
        print()
        print('-' * 50)
        print(f'Optimizing: {key}')
        print(f'Current Value: {main.values[key]}')
        print('-' * 50)
        bestValue = main.values[key]
        bestGuesses = lastGuesses

        # defaultValue = values[key]

        # lastGuesses = getAverageModelGuesses(maxIndex=numPerModel)

        incrementer = 2

        pastValues = [main.values[key]]
        pastGuesses = [lastGuesses]

        same = False

        for i in range(100):
            main.values[key] += incrementer


            print(f'[{i + 1:3d}/100] -> Set {key} to {main.values[key]}')
            
            if main.values[key] in pastValues:
                guesses = pastGuesses[pastValues.index(main.values[key])]
            else:
                guesses = getAverageModelGuesses(maxIndex=numPerModel)

                pastValues.append(main.values[key])
                pastGuesses.append(guesses)

            print(f'Average Guesses Required: {guesses}')
            print()

            if guesses == lastGuesses:
                if same:
                    print('No change in average guesses, stopping')
                    main.values[key] -= incrementer
                    break
                same = True
            else:
                same = False

            if guesses < bestGuesses:
                bestGuesses = guesses
                bestValue = main.values[key]

            if guesses > lastGuesses:
                # Flip incrementing direction
                incrementer = -incrementer
                # If we've switch before, half the incrementer
                if i != 0:
                    incrementer = incrementer / 2
                else:
                    # Go back to last value so we just go past it
                    main.values[key] += incrementer
                    guesses = lastGuesses

            lastGuesses = guesses

        # print()


        main.values[key] = bestValue
        lastGuesses = bestGuesses
        print(f'Best value for {key}: {bestValue} ({bestGuesses} guesses)')

    print()
    print()
    print('-' * 50)
    print('Training Complete')
    print(f'Done in {round((time.time() - trainStart) / 60 - 0.5)}:{round((time.time() - trainStart) % 60):02d} minutes')
    print('-' * 50)
    print()
    print('Best Guess Average Achieved: ', bestGuesses)
    print('Random Guess Average:        ', randomGuesses)
    print()
    print('Best Values:')
    print()
    print('values =', str(main.values).replace(', ', ',\n'))
    print()
    print()

if __name__ == '__main__':
    trials()