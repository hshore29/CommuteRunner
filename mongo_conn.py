from pymongo import MongoClient

mongo_db = MongoClient('localhost', 27017).commute_runner

def aggregate_commute_times(work_zip):
    docs = mongo_db.commutes.aggregate([
        {"$match": {"_id.end": work_zip}},
        {"$project": {
            "_id": 0,
            "zip": "$_id.start",
            "duration": "$commute.overview.duration"
            }
         },
        ])
    return docs

def aggregate_commute_steps(work_zip):
    docs = mongo_db.commutes.aggregate([
        {"$match": {"_id.end": work_zip}},
        {"$unwind": "$commute.steps"},
        {"$group": {
            "_id": {
                "polyline": "$commute.steps.polyline",
                "startend": "$commute.steps.startend",
                "mode": "$commute.steps.travel_mode",
                "type": "$commute.steps.transit.transit_type"
                },
            "line_name": {
                "$addToSet": {
                    "$ifNull": [
                        "$commute.steps.transit.line_short_name",
                        "$commute.steps.transit.line_name"
                        ]
                    }
                },
            "agencies": {"$addToSet": "$commute.steps.transit.agency"},
            "colors": {"$addToSet": "$commute.steps.transit.line_color"},
            "count": {"$sum": 1}
            }
         },
        {"$project": {
            "_id": 0,
            "polyline": "$_id.polyline",
            "startend": "$_id.startend",
            "mode": "$_id.mode",
            "type": {"$ifNull": ["$_id.type", "$_id.mode"]},
            "line_name": 1, "agencies": 1, "colors": 1, "count": 1
            }
         }
        ])
    return docs
