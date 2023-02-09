import sys
import random

def get_array_indices_matching_given_val(arr, val):
    return [i for i, arr_val in enumerate(arr) if arr_val == val]

def assign_random_reviewer_among_min_count(counts):
    min_count = min(counts)
    indices = get_array_indices_matching_given_val(counts, min_count)
    index = random.choice(indices)
    counts[index] += 1 # this person's review count just went up by one
    return index

def get_reviewers(n_papers, n_people, fname):
    with open(fname, 'w') as f:
        line = 'Submission ID,Withdrawn,Primary,Secondary,Second Secondary\n'
        f.write(line)
        counts = [0 for i in range(n_people)]
        for i in range(n_papers):
            r1 = assign_random_reviewer_among_min_count(counts)
            r2 = assign_random_reviewer_among_min_count(counts)
            line = f'p{i},False,r{r1},r{r2},\n'
            f.write(line)
    print(f'wrote {fname} with reviewer counts: {counts}')

def main():
    n_papers = 1000
    n_people = 100
    fname = 'fake-data.csv'
    if len(sys.argv) > 1:
        n_papers = int(sys.argv[1])
    if len(sys.argv) > 2:
        n_people = int(sys.argv[2])
    if len(sys.argv) > 3:
        fname = sys.argv[3]
    get_reviewers(n_papers, n_people, fname)

main()