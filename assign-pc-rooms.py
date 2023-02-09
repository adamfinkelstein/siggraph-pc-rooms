import sys
import math
import networkx as nx
from random import shuffle
from networkx.algorithms import community
from pysat.formula import WCNFPlus
from pysat.examples.rc2 import RC2

# GLOBAL VARIABLES -- see README.md for meaning of these rooms

ROOM_LABELS = ['A','B','X','Y']
AX,BX,AY,BY,CX,CY,AZ,BZ,CZ = list(range(9)) # ints 0,1,...8
CATEGORY_LABELS = ['AX','BX','AY','BY','CX','CY','AZ','BZ','CZ']

''' Category meanings:
| 0 | AX | in A or X
| 1 | BX | in B or X
| 2 | AY | in A or Y
| 3 | BY | in B or Y
| 4 | CX | in X
| 5 | CY | in Y
| 6 | AZ | in A
| 7 | BZ | in B
| 8 | CZ | no room possible
'''
#    012345 = code
LIST_ABCXYZ = [
    (AX, 0, 3),
    (BX, 1, 3),
    (CX, 2, 3),
    (AY, 0, 4),
    (BY, 1, 4),
    (CY, 2, 4),
    (AZ, 0, 5),
    (BZ, 1, 5),
    (CZ, 2, 5)
]

LIST_OPTIONS = [ 
    (0,2), # AX, coding for A,B,X,Y = 0,1,2,3
    (1,2), # BX
    (0,3), # AY
    (1,3)  # BY
]

ONLY_OPTIONS = [9,9,9,9,2,3,0,1,9] # lists 4-7 can specifically only go to X,Y,A,B = 2,3,0,1 (9=None)

def halt_with_error(msg):
    print(msg)
    sys.exit()

# Input CSV file has this header/format:
# Submission ID,Withdrawn,Primary,Secondary,Second Secondary
# Note: currentlly ignores withdrawn papers or those with <1 reviewer.
def read_assignments(fname):
    reviewers = set()
    papers = {}
    singles = {}
    with open(fname) as f:
        lines = f.readlines()
    lines = lines[1:] # skip header
    for line in lines:
        parts = line.split(',')
        if len(parts) < 4:
            continue
        parts = [p.strip() for p in parts] # remove surrounding whitespace
        pid,withdraw = parts[:2]
        if not pid or withdraw == 'True':
            continue
        revs = parts[2:] # reviewers
        revs = [r for r in revs if len(r)] # remove blank reviewers
        if len(revs) < 1: # no reviewers
            print(f'skipping paper {pid} because no reviewers')
            continue
        if len(revs) < 2: # just one reviewer
            singles[pid] = revs[0]
            continue
        pri = revs[0]
        sec = revs[1]
        reviewers.add(pri)
        reviewers.add(sec)
        papers[pid] = (pri, sec)
    reviewers = list(reviewers)
    return reviewers, papers, singles

def make_graph_from_paper_reviews(reviewers, papers):
    graph = nx.Graph()
    for r in reviewers:
        graph.add_node(r)
    for pid in papers:
        pri,sec = papers[pid]
        if graph.has_edge(pri,sec):
            graph[pri][sec]['weight'] += 1
            graph[pri][sec]['pids'].append(pid)
        else:
            graph.add_edge(pri,sec)
            graph[pri][sec]['weight'] = 1
            graph[pri][sec]['pids'] = [ pid ]
    graph_node_count = len(list(graph.nodes))
    graph_edge_count = len(list(graph.edges))
    print(f'Added {graph_node_count} nodes and {graph_edge_count} edges to graph.')
    return graph

def partition_kl_bisection(graph):
    split = community.kernighan_lin_bisection(graph, max_iter=100, weight='weight')
    return split

def partition_graph(graph):
    split = partition_kl_bisection(graph)
    room0 = list(split[0])
    room1 = list(split[1])
    cut_edges = list(nx.edge_boundary(graph, room0))
    return room0, room1, cut_edges

def get_papers_in_graph_cut(graph, cut):
    in_cut = []
    for edge in cut:
        r1, r2 = edge
        in_cut += graph[r1][r2]['pids']
    return list(set(in_cut))

def get_reviewers_in_graph_cut(graph, cut):
    in_cut = []
    for edge in cut:
        r1, r2 = edge
        in_cut.append(r1)
        in_cut.append(r2)
    return list(set(in_cut))

def make_subgraph_from_cut(graph, partition):
    roomA, roomB, cutC = partition
    subgraph = nx.Graph()
    reviewers = get_reviewers_in_graph_cut(graph, cutC)
    for r in reviewers:
        subgraph.add_node(r)
    for edge in cutC:
        pri, sec = edge
        paper_weight = graph[pri][sec]['weight']
        paper_pids = graph[pri][sec]['pids']
        subgraph.add_edge(pri,sec)
        subgraph[pri][sec]['weight'] = paper_weight
        subgraph[pri][sec]['pids'] = paper_pids
    return subgraph

def dump_string_to_file(fname, lines):
    with open(fname, 'w') as f:
        f.write(lines)

def dump_people_rooms(fname, room0, room1):
    lines = 'Reviewer,Room\n'
    for person in room0:
        lines += f'{person},Room0\n'
    for person in room1:
        lines += f'{person},Room1\n'
    dump_string_to_file(fname, lines)

def get_room(person, room0):
    if person in room0:
        return 0
    return 1

def get_list_lengths(pid_lists):
    list_lengths = [len(pid_lists[i]) for i in range(9)]
    return list_lengths    

def dump_list_lengths(pid_lists):
    list_lengths = get_list_lengths(pid_lists)
    for i in range(9):
        print(CATEGORY_LABELS[i],':',list_lengths[i])

def classify_papers_ABC(papers, partition):
    roomA, roomB, cutC = partition
    pidsABC = [ [] for i in range(3) ]
    for pid in papers:
        pri,sec = papers[pid]
        if pri in roomA and sec in roomA:
            pidsABC[0].append(pid)
        elif pri in roomB and sec in roomB:
            pidsABC[1].append(pid)
        else:
            pidsABC[2].append(pid)
    # print('papers outside rooms:', len(pidsC))
    return pidsABC

def pid_in_ABCXYZ(pid, pidsABCXYZ):
    inABCXYZ = [ (pid in pidsABCXYZ[i]) for i in range(6) ]
    return inABCXYZ

def append_pid_to_list(pid, pid_lists, inABCXYZ):
    for i,tup in enumerate(LIST_ABCXYZ):
        index, room0, room1 = tup
        if inABCXYZ[room0] and inABCXYZ[room1]:
            pid_lists[index].append(pid)
            return
    halt_with_error(f'cannot assign pid {pid} to room pair list', inABCXYZ)

def classify_papers_ABCXYZ(papers, partition1, partition2):
    pidsABC = classify_papers_ABC(papers, partition1)
    pidsXYZ = classify_papers_ABC(papers, partition2)
    pidsABCXYZ = pidsABC + pidsXYZ
    pid_lists = [ [] for i in range(9) ]
    for pid in papers:
        inABCXYZ = pid_in_ABCXYZ(pid, pidsABCXYZ)
        append_pid_to_list(pid, pid_lists, inABCXYZ)
    return pid_lists

def assign_people_missing_from_XY(reviewers, partion2):
    roomX, roomY, cutZ = partion2
    revs = set(reviewers)
    missing = list( (revs - set(roomX)) - set(roomY) )
    # print('missing:', missing)
    # print('roomX, roomY sizes:', len(roomX), len(roomY))
    shuffle(missing)
    for rev in missing:
        if len(roomX) <= len(roomY):
            roomX.append(rev)
        else:
            roomY.append(rev)
    # print('roomX, roomY sizes:', len(roomX), len(roomY))

def get_neg_and_pos(i):
    neg,pos = LIST_OPTIONS[i]
    return neg,pos

def get_max_sat_per_room(pid_lists):
    list_lengths = get_list_lengths(pid_lists)
    count_assignable = sum(list_lengths[:8])
    quarter = int(math.ceil(count_assignable/4.0))
    countCX, countCY, countAZ, countBZ = list_lengths[4:8]
    maxA = quarter - countAZ
    maxB = quarter - countBZ
    maxX = quarter - countCX
    maxY = quarter - countCY
    return [maxA, maxB, maxX, maxY]

def sat_solve(sat_lists, max_list):
    cnf = WCNFPlus()
    for i in range(4):
        cnf.append([sat_lists[i], max_list[i]], is_atmost=True) 
    solver = 'minicard'
    model = None
    with RC2(cnf, solver=solver) as rc2:
        model = rc2.compute()
    return model

def assign_pids_to_rooms(pid_lists):
    sat_count = 1
    sat_lists = [ [] for i in range(4) ]
    sat_to_pid = {}
    for i in range(4):
        pid_list = pid_lists[i]
        # list_label = CATEGORY_LABELS[i]
        # list_len = len(pid_list)
        neg,pos = get_neg_and_pos(i)
        # print(f'assign sat vars to {list_len} papers in {list_label} with neg {neg} and pos {pos} ...')
        for pid in pid_list:
            tup = (pid, neg, pos)
            sat_to_pid[sat_count] = tup
            sat_lists[neg].append(-sat_count)
            sat_lists[pos].append( sat_count)
            sat_count += 1
    max_list = get_max_sat_per_room(pid_lists) # max in rooms A, B, X, Y

    model = sat_solve(sat_lists, max_list)
    if not model:
        return None

    paper_rooms = [ [], [], [], [] ] # four empty lists

    # first assign pids that only have one option to that room
    for i in range(4,8):
        assign_to = ONLY_OPTIONS[i]
        for pid in pid_lists[i]:
            paper_rooms[assign_to].append(pid)

    # next go through model solution assigning to each room
    for var in model:
        sat_var = abs(var)
        pid, neg, pos = sat_to_pid[sat_var] 
        if var > 0:
            paper_rooms[pos].append(pid)
        else:
            paper_rooms[neg].append(pid)

    return paper_rooms

def assign_papers_to_rooms(reviewers, papers, partition1, partition2):
    assign_people_missing_from_XY(reviewers, partition2)
    pid_lists = classify_papers_ABCXYZ(papers, partition1, partition2)
    paper_rooms = assign_pids_to_rooms(pid_lists) # pidsA, pidsB, pidsX, pidsY
    return paper_rooms

def partition_cut_cost(graph, partition):
    roomA, roomB, cutC = partition
    cut_cost = nx.cut_size(graph, roomA, weight='weight')
    return cut_cost

def partition_ABXY_trials(graph, reviewers, papers, num_trials=1000):
    min_cut_cost = 9999999 # a big number
    min_paper_rooms = None
    min_partitions = None
    for i in range(num_trials):
        partition1 = partition_graph(graph)
        subgraph = make_subgraph_from_cut(graph, partition1)
        partition2 = partition_graph(subgraph)
        cut_cost = partition_cut_cost(subgraph, partition2)
        if min_cut_cost > cut_cost:
            paper_rooms = assign_papers_to_rooms(reviewers, papers, partition1, partition2)
            if paper_rooms:
                min_cut_cost = cut_cost
                min_paper_rooms = paper_rooms
                min_partitions = [partition1, partition2]
                min_sizes = [len(r) for r in paper_rooms]
                print(f'iter: {i} cost: {cut_cost} rooms sizes:', min_sizes)
    return min_partitions, min_paper_rooms

# This function is called to validate both reviewers and papers.
# Variables are named for reviewers, but the same works for papers.
def validate_room_count_is_one(reviewers, reviewer_rooms, label):
    # ensure each reviewer is in exactly one room
    all_room_participants = sum(reviewer_rooms, [])
    for rev in reviewers:
        count = all_room_participants.count(rev)
        if count != 1:
            print(f'{label} {rev} is in {count} rooms (should be 1)')
    # next ensure each room occupant is one of our reviewers
    uniq_room_participants = set(all_room_participants)
    for p in uniq_room_participants:
        if p not in reviewers:
            print(f'{label} {p} is in a room (but not our list of {label}s)')

def validate_paper_rooms(reviewers, papers, reviewer_rooms, paper_rooms, pids_in_cut):
    validate_room_count_is_one(reviewers, reviewer_rooms[:2], 'reviewer') # rooms A,B
    validate_room_count_is_one(reviewers, reviewer_rooms[2:], 'reviewer') # rooms X,Y
    rooms_with_cut = paper_rooms + [ pids_in_cut ]
    validate_room_count_is_one(papers, rooms_with_cut, 'paper')

def add_singles_to_rooms(rooms_by_person, paper_rooms, singles):
    for pid in singles:
        print('checking single '+pid)
        reviewer = singles[pid]
        rooms = rooms_by_person[reviewer]
        room = rooms[0]
        print(f'room: {room}')
        if room == 'A':
            index = 0
        elif room == 'B':
            index = 1
        else:
            print(f'cannot find paper for single {pid} reviewed by reviewer {reviewer}')
            continue
        paper_room = paper_rooms[index]
        paper_room.append(pid)
        print(f'add single paper {pid} to room {room} (reviewer {reviewer})')

def dump_string_to_file(fname, lines):
    print(f'writing {fname}')
    with open(fname, 'w') as f:
        f.write(lines)

def write_rooms_file(fname, rooms, label, extra=None):
    lines = f'{label},Room\n'
    for i,room in enumerate(rooms):
        room_label = ROOM_LABELS[i]
        for p in room: # either person or paper
            lines += f'{p},{room_label}\n'
    if extra:
        lines += extra
    dump_string_to_file(fname, lines)

def consolidate_rooms_by_person(reviewer_rooms):
    rooms_by_person = {}
    for i,room in enumerate(reviewer_rooms):
        room_label = ROOM_LABELS[i]
        for p in room:
            if p not in rooms_by_person:
                rooms_by_person[p] = room_label
            else:
                rooms_by_person[p] += room_label
    return rooms_by_person

def write_people_rooms_file(rooms_by_person):
    fname = 'people-rooms.csv'
    lines = f'Reviewer,Rooms\n'
    for p in rooms_by_person:
        rooms = rooms_by_person[p]
        lines += f'{p},{rooms}\n'
    dump_string_to_file(fname, lines)

def write_paper_rooms_file(paper_rooms, pids_in_cut):
    lines = ''
    for pid in pids_in_cut:
        lines += f'{pid},P\n'
    write_rooms_file('paper-rooms.csv', paper_rooms, 'Paper', lines)

def dump_room_counts(reviewer_rooms, paper_rooms, pids_in_cut):
    for i,room_label in enumerate(ROOM_LABELS):
        paper_count = len(paper_rooms[i])
        reviewer_count = len(reviewer_rooms[i])
        print(f'{i}: Room {room_label} has {paper_count} papers and {reviewer_count} reviewers')
    print('Papers in Plenary: ', len(pids_in_cut))

def main():
    fname = 'fake-data.csv'
    ntrials = 1000
    if len(sys.argv) > 1:
        fname = sys.argv[1]
    if len(sys.argv) > 2:
        ntrials = int(sys.argv[2])
    print(f'Reading {fname} ...')
    reviewers, papers, singles = read_assignments(fname)
    print('Input reviewers and papers:', len(reviewers), len(papers))
    graph = make_graph_from_paper_reviews(reviewers, papers)
    print(f'About to run {ntrials} trials for partioning into rooms A,B,X and Y...')
    both_partitions, paper_rooms = partition_ABXY_trials(graph, reviewers, papers, ntrials)
    if not paper_rooms:
        print('Uh-oh -- partition failed! Quitting...')
        return
    partition1, partition2 = both_partitions
    roomA, roomB, cutC = partition1
    roomX, roomY, cutZ = partition2
    reviewer_rooms = [roomA, roomB, roomX, roomY]
    pids_in_cut = get_papers_in_graph_cut(graph, cutZ)
    validate_paper_rooms(reviewers, papers, reviewer_rooms, paper_rooms, pids_in_cut)
    rooms_by_person = consolidate_rooms_by_person(reviewer_rooms)
    add_singles_to_rooms(rooms_by_person, paper_rooms, singles)
    dump_room_counts(reviewer_rooms, paper_rooms, pids_in_cut)
    write_people_rooms_file(rooms_by_person)
    write_paper_rooms_file(paper_rooms, pids_in_cut)

main()
