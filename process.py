# Read in the pickled data and save it as a csv file

import pickle

print('Start')

# Load the pickled data
with open('results.pkl', 'rb') as f:
    data = pickle.load(f)

# Count the items in the dictionary
count = 0
for word in data:
    count += 1
print(f'Number of items in pickle: {count}')

count = 0
# Save the data as a csv file
with open('results.csv', 'w') as f:
    f.write('Word,Low,High,Avg\n')
    for word in data:
        f.write(word + ',' + ','.join([f'{num:0.9f}' for num in data[word]]) + '\n')
        count += 1
    f.close()

print(f'Number of items written to csv: {count}')
print('Done')