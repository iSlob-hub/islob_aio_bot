import json

def format_timezone_entry(entry):
    """
    Format timezone entry to match the required format:
    {"name": "Albania (Tirana, -1 h)", "country": "Albania", "offset": -1}
    """
    country = entry["country"]
    capital = entry["capital"]
    offset = entry["offset_from_kyiv"]
    
    # Format offset with sign
    if offset == 0:
        offset_str = "0 h"
    elif offset > 0:
        offset_str = f"+{int(offset)} h" if offset == int(offset) else f"+{offset} h"
    else:
        offset_str = f"{int(offset)} h" if offset == int(offset) else f"{offset} h"
    
    # Create name field
    name = f"{country} ({capital}, {offset_str})"
    
    return {
        "name": name,
        "country": country,
        "offset": offset
    }


def main():
    # Read the generated time_offsets.json
    with open("time_offsets.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Format each entry
    formatted_data = []
    for entry in data:
        formatted_entry = format_timezone_entry(entry)
        formatted_data.append(formatted_entry)
    
    # Sort alphabetically by country name
    formatted_data.sort(key=lambda x: x["country"])
    
    # Generate Python code
    print("COUNTRIES_WITH_TIMEZONES = [")
    for i, entry in enumerate(formatted_data):
        comma = "," if i < len(formatted_data) - 1 else ""
        print(f'    {{"name": "{entry["name"]}", "country": "{entry["country"]}", "offset": {entry["offset"]}}}{comma}')
    print("]")
    
    # Also save to a file
    with open("formatted_timezones.txt", "w", encoding="utf-8") as f:
        f.write("COUNTRIES_WITH_TIMEZONES = [\n")
        for i, entry in enumerate(formatted_data):
            comma = "," if i < len(formatted_data) - 1 else ""
            f.write(f'    {{"name": "{entry["name"]}", "country": "{entry["country"]}", "offset": {entry["offset"]}}}{comma}\n')
        f.write("]\n")
    
    print(f"\n✅ Formatted {len(formatted_data)} countries")
    print("💾 Saved to formatted_timezones.txt")


if __name__ == "__main__":
    main()
