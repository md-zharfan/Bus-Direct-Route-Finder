import json

with open("data/import/LiveBus.timings.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for doc in data:
    if "_id" in doc:
        del doc["_id"]

with open("data/import/LiveBus.timings.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)