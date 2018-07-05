from pymongo import MongoClient

mongo_db = MongoClient('localhost', 27017).commute_runner

def aggregate_commute_times(work_zip):
    docs = mongo_db.commutes.aggregate([
        {"$match": {"_id.end": work_zip, "commute.status": "OK"}},
        {"$sort": {"commute.overview.duration": 1}},
        {"$group": {
            "_id": {
                "start": "$_id.start", "end": "$_id.end",
                "arrive_by": "$_id.arrive_by"
            },
            "doc": {"$first": "$$ROOT"}
         }},
        {"$project": {
            "_id": 0,
            "zip": "$_id.start",
            "duration": "$doc.commute.overview.duration",
            "weight": "$doc.weight"
            }
         },
        ])
    return docs

def aggregate_commute_steps(work_zip):
    docs = mongo_db.commutes.aggregate([
        {"$match": {"_id.end": work_zip, "commute.status": "OK"}},
        {"$sort": {"commute.overview.duration": 1}},
        {"$group": {
            "_id": {
                "start": "$_id.start", "end": "$_id.end",
                "arrive_by": "$_id.arrive_by"
            },
            "doc": {"$first": "$$ROOT"}
         }},
        {"$unwind": "$doc.commute.steps"},
        {"$group": {
            "_id": {
                "polyline": "$doc.commute.steps.polyline",
                "startend": "$doc.commute.steps.startend",
                "mode": "$doc.commute.steps.travel_mode",
                "type": "$doc.commute.steps.transit.transit_type"
                },
            "line_name": {
                "$addToSet": {
                    "$ifNull": [
                        "$doc.commute.steps.transit.line_short_name",
                        "$doc.commute.steps.transit.line_name"
                        ]
                    }
                },
            "agencies": {"$addToSet": "$doc.commute.steps.transit.agency"},
            "colors": {"$addToSet": "$doc.commute.steps.transit.line_color"},
            "count": {"$sum": 1},
            "weight": {"$sum": "$doc.weight"}
            }
         },
        {"$project": {
            "_id": 0,
            "polyline": "$_id.polyline",
            "startend": "$_id.startend",
            "mode": "$_id.mode",
            "type": {"$ifNull": ["$_id.type", "$_id.mode"]},
            "line_name": 1, "agencies": 1, "colors": 1, "count": 1, "weight": 1
            }
         }
        ])
    return docs
