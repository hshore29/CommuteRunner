from collections import defaultdict
from pymongo import MongoClient
import polyline
unpolyline = lambda p: tuple(map(tuple, map(reversed, polyline.decode(p))))
mongo = MongoClient('localhost', 27017)
mongodb = mongo.commute_runner

# Get MongoDB collections
comms = mongodb.commutes
steps = mongodb.steps

# Unwind Steps
s = comms.aggregate([
    {'$unwind': '$commute.steps'},
    {'$match': {
        'commute.steps.travel_mode': 'TRANSIT',
        'commute.steps.transit.line_short_name': {'$in': ['7', '7X']}}},
    {'$group': {'_id': '$commute.steps.polyline'}},
    ])

polylines = [i['_id'] for i in s]
output = defaultdict(set)

def segment(A, B):
    # Get number of points from A contained in B
    inter = len([i for i in A if i in B])
    # If A & B do not overlap or A is entirely in B, return A un-split
    if inter == 0:
        return (A,)

    # Split A into segments based on overlap with B into output
    # Keep track of whether they were common segs or not in overlap
    output = [list(),]
    overlap = list()
    common = A[0] in B
    for x in range(len(A)):
        new_common = A[x] in B
        if new_common != common:
            overlap.append(new_common)
            output.append(list())
        output[-1].append(A[x])
        common = new_common

    # For all non-common segs, grab the neighboring common points
    for i, common in enumerate(overlap):
        if not common:
            if i > 0:
                output[i] = [output[i-1][-1]] + output[i]
            if i < len(output):
                output[i] = output[i] + [output[i+1][0]]

    # Remove any single point segs
    output = [o for o in output if len(o) > 1]

    # Return split segments
    output = tuple(map(tuple, output))
    return output

for poly in polylines:
    print('Next Polyline')
    A = (unpolyline(poly),)
    print(A[0][0], A[0][-1])
    segments = output.copy()
    output = defaultdict(set)

    for seg_key, seg_val in segments.items():
        B = seg_key
        for a in A:
            for seg in segment(B, a):
                output[seg].update(seg_val)
        A = sum((segment(a, B) for a in A), tuple())

    for a in A:
        output[a].add(poly)

    for k, v in output.items():
        print(k[0], k[-1], len(v))
