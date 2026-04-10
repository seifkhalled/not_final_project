import re
import json

def normalize(name):
    """Normalize names for fuzzy matching."""
    if not name: return ""
    return name.lower().strip()

def parse_trip_plan_to_json(trip_text):
    result = {
        "overview": "",
        "places": [],
        "restaurants": [],
        "hotels": [],
        "itinerary": [],
        "budget": {
            "accommodation": 0, "food": 0, "activities": 0, "transportation": 0, "total": 0, "currency": "EGP"
        },
        "tips": []
    }

    sections = re.split(r'\n##\s+', '\n' + trip_text)
    
    for section in sections:
        if not section.strip():
            continue
            
        lines = section.strip().split('\n')
        title = lines[0].strip() if lines else ""
        content = '\n'.join(lines[1:])
        title_lower = title.lower()
        
        if any(kw in title_lower for kw in ['overview', 'introduction', 'welcome']):
            result["overview"] = content.strip()
        elif 'place' in title_lower or 'visit' in title_lower or 'attraction' in title_lower:
            patterns = [r'\*\*(.+?)\*\*', r'[-*]\s*(.+)']
            for pattern in patterns:
                for match in re.finditer(pattern, content):
                    name = match.group(1).split('|')[0].split('—')[0].strip()
                    if name and name not in [p['name'] for p in result["places"]]:
                        result["places"].append({"name": name, "city": ""})
        elif 'restaurant' in title_lower or 'dining' in title_lower or 'food' in title_lower:
            rest_pattern = r'\*\*(.+?)\*\*'
            for match in re.finditer(rest_pattern, content):
                name = match.group(1).split('|')[0].split('—')[0].strip()
                if name and name not in [r['name'] for r in result["restaurants"]]:
                    result["restaurants"].append({"name": name, "city": ""})
        elif 'hotel' in title_lower or 'accommodation' in title_lower:
            hotel_pattern = r'\*\*(.+?)\*\*'
            for match in re.finditer(hotel_pattern, content):
                name = match.group(1).split('|')[0].split('—')[0].strip()
                if name and name not in [h['name'] for h in result["hotels"]]:
                    result["hotels"].append({"name": name, "city": ""})
        elif 'tip' in title_lower or 'advice' in title_lower or 'note' in title_lower:
            tips = re.findall(r'[-*]\s*(.+)', content)
            result["tips"].extend([t.strip() for t in tips if t.strip()])
        elif 'day' in title_lower or 'itinerary' in title_lower:
            day_sections = re.split(r'###\s+Day\s+(\d+)', content)
            for i in range(1, len(day_sections), 2):
                day_num = int(day_sections[i])
                day_content = day_sections[i+1]
                day_entry = {"day": day_num, "date": "", "morning": None, "lunch": None, "afternoon": None, "dinner": None, "dayCost": ""}
                date_match = re.search(r'\[Date:\s*([^\]]+)\]', day_content)
                if date_match: day_entry["date"] = date_match.group(1)
                blocks = {"morning": [r'\*\*Morning.*?\*\*'], "lunch": [r'\*\*Lunch.*?\*\*'], "afternoon": [r'\*\*Afternoon.*?\*\*'], "dinner": [r'\*\*Dinner.*?\*\*']}
                lines = day_content.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    for block_key, patterns in blocks.items():
                        for p in patterns:
                            if re.search(p, line, re.IGNORECASE):
                                parts = line.split('**', 2)
                                if len(parts) >= 3:
                                    detail = parts[2].strip().lstrip(':').strip()
                                    info_parts = re.split(r'[—|]', detail)
                                    place_name = info_parts[0].strip()
                                    desc = info_parts[1].strip() if len(info_parts) > 1 else ""
                                    day_entry[block_key] = {"place": place_name, "description": desc}
                                    if block_key in ["morning", "afternoon"]:
                                        if place_name and place_name not in [p['name'] for p in result["places"]]:
                                            result["places"].append({"name": place_name, "city": ""})
                                    elif block_key in ["lunch", "dinner"]:
                                        if place_name and place_name not in [r['name'] for r in result["restaurants"]]:
                                            result["restaurants"].append({"name": place_name, "city": ""})
                cost_match = re.search(r'Day Cost Estimate:\s*~?([\d,]+)', day_content)
                if cost_match: day_entry["dayCost"] = cost_match.group(1)
                result["itinerary"].append(day_entry)

    if not result["overview"] and trip_text:
        first_section = re.split(r'\n##', trip_text)[0].strip()
        first_section = re.sub(r'^#\s+.*?\n', '', first_section, flags=re.MULTILINE).strip()
        result["overview"] = first_section
    return result

sample_text = """# 🇪🇬 Trip Plan: Alexandria
## Overview
Explore Alexandria's rich history.

## Day-by-Day Itinerary
### Day 1 [Date: Apr 08]
**Morning (9:00–12:00):** Library of Alexandria — A modern marvel. | Ticket: 70 EGP
**Lunch (12:30):** Fish Market — Fresh seafood. | ~200 EGP/person
**Afternoon (14:00–17:00):** Qaitbay Citadel | Ticket: 60 EGP
**Dinner (19:00):** Trianon | ~150 EGP/person
**Day Cost Estimate: ~600 EGP

## 🏨 Recommended Hotel
**Steigenberger Cecil Hotel** — Luxury historic hotel.
"""

parsed = parse_trip_plan_to_json(sample_text)
print(json.dumps(parsed, indent=2))
