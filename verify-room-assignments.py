import sys
import random

PLENARY = 'P'

def split_csv_row(line):
    line = line.strip()
    row = line.split(',')
    row = [item.strip() for item in row]
    return row

def read_csv_rows(fname):
    with open(fname) as f:
        lines = f.readlines()
    lines = lines[1:] # skip header
    rows = [split_csv_row(line) for line in lines]
    return rows

# Submission ID,Withdrawn,Primary,Secondary,Second Secondary
def read_data_file(fname):
    rows = read_csv_rows(fname)
    tups = []
    n_withdrawn = 0
    n_single = 0
    for row in rows:
        if (len(row)) < 4:
            continue
        paper,withdrawn,primary,secondary = row[:4]
        if withdrawn == 'False':
            if secondary and not primary:
                primary,secondary = secondary,primary
            if not secondary:
                n_single += 1
            tup = (paper,primary,secondary)
            tups.append(tup)
        else:
            n_withdrawn += 1
    n = len(tups)
    print(f'Read {n} papers from {fname}.')
    if n_single:
        print(f'-- with {n_single} single reviewers (primary or secondary).')
    if n_withdrawn:
        print(f'-- ignoring {n_withdrawn} withdrawn papers.')
    return tups

def read_paper_or_people_rooms(fname, label, target_number):
    rows = read_csv_rows(fname)
    rooms = {}
    for item,room in rows:
        if item not in rooms:
            rooms[item] = room
        else:
            rooms[item] += room # this tolerates separate room rows for each person/paper (not needed, but nice)
    n = len(rooms)
    print(f'Read {n} room assignments for {label} from {fname}.')
    for item in rooms:
        room = rooms[item]
        n = len(room)
        if n != target_number:
            print(f'Error in {label}: target number of rooms for {item} is {target_number} but actual is {n} ({room}).')
    return rooms

def get_paper_room_assignment(paper, rooms):
    if paper in rooms:
        return rooms[paper]
    return PLENARY

def fail_exit(msg):
    print('FATAL error: ' + msg)
    sys.exit(-1)

def get_person_room_assignment(person, rooms):
    if not person:
        return None
    if person in rooms:
        return rooms[person]
    fail_exit(f'no room assignment for person {person}!')

def potential_reviewer_room_match(primary_room, secondary_room):
    for room in primary_room:
        if room in secondary_room:
            return True
    for room in secondary_room:
        if room in primary_room:
            return True
    return False

LEGAL_PAPER_ROOMS = 'PABXY'
LEGAL_PERSON_ROOMS = 'AX,BX,AY,BY'.split(',')

def check_legal_paper_room(paper, paper_room):
    if len(paper_room) != 1:
        fail_exit(f'paper {paper} not assigned to exactly one room: {paper_room}')
    if paper_room not in LEGAL_PAPER_ROOMS:
        fail_exit(f'paper {paper} not assigned to legal room: {paper_room}')

def check_legal_person_room(person, person_room):
    if len(person_room) != 2:
        fail_exit(f'person {person} not assigned to exactly two rooms: {person_room}')
    if person_room not in LEGAL_PERSON_ROOMS:
        fail_exit(f'person {person} assigned to illegal room combo: {person_room}')

def check_assignments_match(paper, paper_room, primary, primary_room, secondary, secondary_room, verbose=False):
    if verbose:
        print(f'Checking paper {paper},{primary},{secondary} paper_room {paper_room} primary_room {primary_room} secondary_room {secondary_room}.')
    check_legal_paper_room(paper, paper_room)
    check_legal_person_room(primary, primary_room)
    if secondary:
        check_legal_person_room(secondary, secondary_room)
    if paper_room == PLENARY and potential_reviewer_room_match(primary_room, secondary_room):
        print(f'Error: paper {paper} is in Plenary but primary and secondary have match ({primary_room},{secondary_room})!')
        return paper
    if paper_room in primary_room and not secondary_room:
        return None
    if paper_room in primary_room and paper_room in secondary_room:
        return None
    if paper_room == PLENARY:
        return paper
    return None

def verify_rooms(data_file, paper_file, people_file):
    data = read_data_file(data_file)
    paper_rooms = read_paper_or_people_rooms(paper_file, 'papers', 1)
    people_rooms = read_paper_or_people_rooms(people_file, 'people', 2)
    all_plenary = []
    for paper,primary,secondary in data:
        paper_room = get_paper_room_assignment(paper, paper_rooms)
        primary_room = get_person_room_assignment(primary, people_rooms)
        secondary_room = get_person_room_assignment(secondary, people_rooms)
        plenary = check_assignments_match(paper, paper_room, primary, primary_room, secondary, secondary_room)
        if plenary:
            all_plenary.append(plenary)
    n_plenary = len(all_plenary)
    if n_plenary:
        print(f'There are {n_plenary} papers in Plenary.')
    print('Done verifying assignments.')

def main():
    data_file = 'fake-data.csv'
    paper_file = 'paper-rooms.csv'
    people_file = 'people-rooms.csv'
    if len(sys.argv) > 1:
        data_file = sys.argv[1]
    if len(sys.argv) > 2:
        paper_file = sys.argv[2]
    if len(sys.argv) > 3:
        people_file = sys.argv[3]
    verify_rooms(data_file, paper_file, people_file)

main()