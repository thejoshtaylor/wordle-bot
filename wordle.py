# Wordle Helper File
# Joshua Taylor
# February 2024

import time
import random

# This module offers helper functions to solve the wordle game

# Load the dictionary on initialization
with open("dictionary.txt", "r") as f:
    dictionary = f.read().splitlines()

# Get word of the day based on random number determined by day of the year and year
def get_word_of_the_day(index=0):
    assert index >= 0

    # Seed the random number generator with the day and year
    day = time.localtime().tm_yday
    year = time.localtime().tm_year
    random.seed(day + (year * 366))

    # Get the word
    word = random.choice(dictionary)
    for _ in range(index):
        word = random.choice(dictionary)
        
    return word

# This function checks if a guess is valid
def is_valid_guess(guess):
    if guess not in dictionary:
        return False
    return True

# This gets a valid word from user input
def get_valid_word():
    while True:
        word = input("> ").lower()

        if is_valid_guess(word):
            return word
        elif word == '':
            return get_word_of_the_day()
        print("Invalid word. Try again.")

# This function gets the green, yellow, and gray pattern of a guess
def check_guess(word, guess):
    assert len(word) == 5
    assert len(guess) == 5
    assert is_valid_guess(guess)

    # The response will be a list of 5 characters
    # g = green, y = yellow, ' ' = gray
    response = [' '] * 5

    # Split the word into a list of characters
    wordList = list(word)

    # Check each letter for an exact match
    for i in range(5):
        if guess[i] == word[i]:
            response[i] = 'g'
            wordList[i] = ' '

    # Check each letter for a partial match
    for i in range(5):
        if response[i] != 'g' and guess[i] in wordList:
            response[i] = 'y'
            wordList[wordList.index(guess[i])] = ' '

    return response

# This function takes the response and returns the printable string for console coloring
def colored_word(guess, response):
    assert len(guess) == 5
    assert len(response) == 5

    colored_word = ""
    for i in range(5):
        if response[i] == 'g':
            colored_word += f"\033[92m{guess[i]}\033[0m"
        elif response[i] == 'y':
            colored_word += f"\033[93m{guess[i]}\033[0m"
        else:
            colored_word += guess[i]
    return colored_word

# This function returns the list of words that match the response
def find_words(guess, response, dict=None):
    assert len(guess) == 5
    assert len(response) == 5

    # Load dictionary
    if dict is None:
        dict = dictionary.copy()

    # Keep track of letters and their positions
    exact = [''] * 5
    exactNot = [''] * 5
    mustHave = []
    mustNotHave = []

    # Split the word into a list of characters
    guessList = list(guess)

    # Check for each letter in the response
    for i, r in enumerate(response):
        # Check for green first
        if r == 'g':
            exact[i] = guessList[i]
            guessList[i] = ''
        # Check for yellow
        elif r == 'y':
            exactNot[i] = guessList[i]
            mustHave.append(guessList[i])
            guessList[i] = ''
        # Grey
        else:
            tmp = guessList[i]
            guessList[i] = ''
            if tmp not in guessList and tmp not in exact and tmp not in mustHave and tmp not in exactNot:
                mustNotHave.append(tmp)
            exactNot[i] = tmp

    # Filter the dictionary
    
    # Filter the exact matches
    for i, l in enumerate(exact):
        if l != '':
            dict = [w for w in dict if w[i] == l]
    # Filter the must haves
    for l in mustHave:
        dict = [w for w in dict if l in w]
    # Filter the exact not matches
    for i, l in enumerate(exactNot):
        if l != '':
            dict = [w for w in dict if w[i] != l]
    # Filter the must not haves
    for l in mustNotHave:
        dict = [w for w in dict if l not in w]

    return dict
