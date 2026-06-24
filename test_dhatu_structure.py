import json

with open("data/dhatu_data.json", "r") as f:
    data = json.load(f)
    print("Sample Dhatu Data:")
    for item in data.get("data", [])[:3]:
        print({
            "dhatu": item.get("dhatu"),
            "aupadeshik": item.get("aupadeshik"),
            "settva": item.get("settva"),
            "tags": item.get("tags")
        })
