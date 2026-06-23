import csv

with open('all-wordle-words.txt', 'r') as f:
    all_words = f.read().splitlines()
    all_words = [word.strip().lower() for word in all_words]

with open('dict-rank.csv', 'r') as f:
    dict_rank = f.read().splitlines()
    dict_rank = [line.split(",")[0].strip().lower() for line in dict_rank]

ranks = []
with open('wordle-to-rank.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['word', 'rank'])
    for word in all_words:
        if word in dict_rank:
            rank = dict_rank.index(word) + 1  # ranks are 1-indexed
            ranks.append(rank)
        else:
            rank = None  # or some default value for words not in the rank list
        writer.writerow([word, rank])

print(f"Max rank found: {max(ranks)}")
print(f"Average rank: {sum(ranks) / len(ranks)}")
print(f"Std dev of ranks: {(sum((rank - (sum(ranks) / len(ranks))) ** 2 for rank in ranks) / len(ranks)) ** 0.5}")
print(f"2std dev above average: {(sum(ranks) / len(ranks)) + 2 * ((sum((rank - (sum(ranks) / len(ranks))) ** 2 for rank in ranks) / len(ranks)) ** 0.5)}")