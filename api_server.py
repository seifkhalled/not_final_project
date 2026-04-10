from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys
from datetime import datetime
import json
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from vector_search import search
from ai.orchestrator import TripOrchestrator
from src.pexels_service import get_place_image_url

app = Flask(__name__)
CORS(app, origins=os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(","))

orchestrator = TripOrchestrator()

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend", "out")

def normalize(name):
    """Normalize names for fuzzy matching."""
    if not name: return ""
    return name.lower().strip()

def safe_avg(items, key, default=0, max_value=None):
    """
    Sanitize and average numerical values from metadata.
    Filters out zeros, non-numerical data, and extreme outliers.
    """
    values = []
    for item in items:
        try:
            # Check both raw item and metadata
            raw_val = item.get(key) or item.get("metadata", {}).get(key, 0)
            val = float(raw_val)
            if val > 0:
                if max_value and val > max_value:
                    continue
                values.append(val)
        except (ValueError, TypeError):
            continue
    return sum(values) / len(values) if values else default

def parse_budget(budget_str):
    """
    Strict budget parsing for EGP ranges. 
    Handles commas and formatted numbers (e.g., '1,000-2,500 EGP').
    """
    try:
        # Normalize: remove commas, 'EGP', '+', and whitespace
        clean = budget_str.replace(",", "").replace("EGP", "").replace("+", "-99999").strip()
        parts = [p.strip() for p in clean.split("-") if p.strip()]
        
        if len(parts) == 1:
            val = int(parts[0])
            return val, val
        elif len(parts) >= 2:
            return int(parts[0]), int(parts[1])
        else:
            raise ValueError("Empty budget parts")
    except (ValueError, IndexError):
        # Fail explicitly in production, but provide defaults for safety
        return 1000, 2000

def calculate_realistic_budget(budget_min, budget_max, hotels, restaurants, places, start_date, end_date, group_size, acc_type, transportation):
    """
    Deterministic budget engine using actual data and Egypt heuristics.
    """
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else datetime.now()
        end_dt = datetime.fromisoformat(end_date) if end_date else datetime.now()
    except:
        start_dt = datetime.now()
        end_dt = datetime.now()
        
    nights = max((end_dt - start_dt).days, 1)
    days = nights + 1
    target_total = (budget_min + budget_max) // 2
    
    # 1. Accommodation (Hotel) costs
    # Cap at 10,000 EGP to ignore garbage data
    base_hotel_price = safe_avg(hotels, "price", default=500, max_value=10000)
    
    # Scale based on accommodation type
    if acc_type == "Budget":
        base_hotel_price *= 0.7
    elif acc_type == "Luxury":
        base_hotel_price *= 1.5
        
    accommodation_cost = round(base_hotel_price * nights)
    
    # 2. Food (Restaurant) costs
    # heuristic: avg_meal_price * 2 meals * days * group_size. Cap at 1,000 EGP per meal.
    avg_meal_price = safe_avg(restaurants, "avg_price", default=150, max_value=1000)
    food_cost = avg_meal_price * 2 * days * group_size
    # Clamp food cost to 40% of target budget to prevent outlier inflation
    food_cost = round(min(food_cost, target_total * 0.4))
    
    # 3. Activities (Places) costs
    # heuristic: avg_ticket * (days // 2) as many days have free activities. Cap at 1,000.
    avg_ticket = safe_avg(places, "ticket_price", default=100, max_value=1000)
    activities_cost = round(avg_ticket * max(1, days // 2))
    
    # 4. Transportation costs (Heuristic based on type)
    if transportation == "Private Car":
        transport_cost = 120 * days
    elif transportation == "Public Transport":
        transport_cost = 30 * days * group_size
    else:
        transport_cost = 50 * days * group_size
    transport_cost = round(transport_cost)
    
    real_total = accommodation_cost + food_cost + activities_cost + transport_cost
    
    # 5. Data Confidence Score
    confidence = 0
    if hotels: confidence += 0.4
    if restaurants: confidence += 0.3
    if places: confidence += 0.3
    
    return {
        "accommodation": accommodation_cost,
        "food": food_cost,
        "activities": activities_cost,
        "transportation": transport_cost,
        "total": real_total,
        "budgetRange": [budget_min, budget_max],
        "withinBudget": real_total <= budget_max,
        "status": "within_budget" if real_total <= budget_max else "over_budget",
        "confidence": round(confidence, 1),
        "currency": "EGP"
    }

def enrich_trip_data(parsed_plan, results_places, results_restaurants, results_hotels):
    """
    Merges database metadata (images, ratings, prices) into the LLM-parsed plan.
    Uses normalization for fuzzy name matching.
    """
    # Create lookups based on normalized names
    place_lookup = {normalize(p.get("metadata", {}).get("name", p.get("name"))): p for p in results_places}
    rest_lookup = {normalize(r.get("metadata", {}).get("name", r.get("name"))): r for r in results_restaurants}
    hotel_lookup = {normalize(h.get("metadata", {}).get("name", h.get("name"))): h for h in results_hotels}
    
    # Enrich Places
    for p in parsed_plan.get("places", []):
        match = place_lookup.get(normalize(p.get("name")))
        if match:
            meta = match.get("metadata", {})
            p["address"] = p.get("address") or meta.get("address", "")
            p["rating"] = p.get("rating") or str(meta.get("rating", ""))
            p["ticketPrice"] = p.get("ticketPrice") or str(meta.get("ticket_price", ""))
            p["timings"] = p.get("timings") or meta.get("timings", "")
            if not p.get("imageUrl"):
                p["imageUrl"] = get_place_image_url(p["name"], p.get("city", ""))
        elif not p.get("imageUrl"):
            p["imageUrl"] = get_place_image_url(p["name"], p.get("city", ""))
            
    # Enrich Restaurants
    for r in parsed_plan.get("restaurants", []):
        match = rest_lookup.get(normalize(r.get("name")))
        if match:
            meta = match.get("metadata", {})
            r["cuisines"] = r.get("cuisines") or meta.get("cuisines", "")
            r["avgPrice"] = r.get("avgPrice") or str(meta.get("avg_price", ""))
            r["location"] = r.get("location") or meta.get("location", "")
            if not r.get("imageUrl"):
                r["imageUrl"] = get_place_image_url(r["name"], r.get("city", ""))
        elif not r.get("imageUrl"):
            r["imageUrl"] = get_place_image_url(r["name"], r.get("city", ""))
            
    # Enrich Hotels
    for h in parsed_plan.get("hotels", []):
        match = hotel_lookup.get(normalize(h.get("name")))
        if match:
            meta = match.get("metadata", {})
            h["rating"] = h.get("rating") or str(meta.get("rating", ""))
            h["price"] = h.get("price") or str(meta.get("price", ""))
            h["distanceKm"] = h.get("distanceKm") or str(meta.get("distance_km", ""))
            if not h.get("imageUrl"):
                h["imageUrl"] = get_place_image_url(h["name"], h.get("city", ""))
        elif not h.get("imageUrl"):
            h["imageUrl"] = get_place_image_url(h["name"], h.get("city", ""))

    return parsed_plan

def parse_trip_plan_to_json(trip_text):
    result = {
        "overview": "",
        "places": [],
        "restaurants": [],
        "hotels": [],
        "itinerary": [],
        "budget": {
            "accommodation": 0,
            "food": 0,
            "activities": 0,
            "transportation": 0,
            "total": 0,
            "currency": "EGP"
        },
        "tips": []
    }

    # Split by ## headers, tolerant of emojis
    # Regex matches '## ' followed by optional emoji/text
    sections = re.split(r'\n##\s+', '\n' + trip_text)
    
    for section in sections:
        if not section.strip():
            continue
            
        lines = section.strip().split('\n')
        title = lines[0].strip() if lines else ""
        content = '\n'.join(lines[1:])
        title_lower = title.lower()
        
        # 1. Overview
        if any(kw in title_lower for kw in ['overview', 'introduction', 'welcome']):
            result["overview"] = content.strip()
            
        # 2. Places / Attractions
        elif 'place' in title_lower or 'visit' in title_lower or 'attraction' in title_lower:
            patterns = [r'\*\*(.+?)\*\*', r'[-*]\s*(.+)']
            for pattern in patterns:
                for match in re.finditer(pattern, content):
                    name = match.group(1).split('|')[0].split('—')[0].strip()
                    if name and name not in [p['name'] for p in result["places"]]:
                        result["places"].append({"name": name, "city": ""})
                
        # 3. Restaurants / Dining
        elif 'restaurant' in title_lower or 'dining' in title_lower or 'food' in title_lower:
            rest_pattern = r'\*\*(.+?)\*\*'
            for match in re.finditer(rest_pattern, content):
                name = match.group(1).split('|')[0].split('—')[0].strip()
                if name and name not in [r['name'] for r in result["restaurants"]]:
                    result["restaurants"].append({"name": name, "city": ""})
                
        # 4. Hotels / Accommodation
        elif 'hotel' in title_lower or 'accommodation' in title_lower:
            hotel_pattern = r'\*\*(.+?)\*\*'
            for match in re.finditer(hotel_pattern, content):
                name = match.group(1).split('|')[0].split('—')[0].strip()
                if name and name not in [h['name'] for h in result["hotels"]]:
                    result["hotels"].append({"name": name, "city": ""})
                
        # 5. Tips
        elif 'tip' in title_lower or 'advice' in title_lower or 'note' in title_lower:
            tips = re.findall(r'[-*]\s*(.+)', content)
            result["tips"].extend([t.strip() for t in tips if t.strip()])
            
        # 6. Itinerary
        elif 'day' in title_lower or 'itinerary' in title_lower:
            # Find all Day X sections
            day_sections = re.split(r'###\s+Day\s+(\d+)', content)
            # day_sections[0] is garbage before Day 1
            for i in range(1, len(day_sections), 2):
                day_num = int(day_sections[i])
                day_content = day_sections[i+1]
                
                day_entry = {
                    "day": day_num,
                    "date": "",
                    "morning": None, "lunch": None, "afternoon": None, "dinner": None,
                    "dayCost": ""
                }
                
                # Extract date if present in title/content
                date_match = re.search(r'\[Date:\s*([^\]]+)\]', day_content)
                if date_match:
                    day_entry["date"] = date_match.group(1)
                
                # Block parsing: Morning, Lunch, Afternoon, Dinner
                blocks = {
                    "morning": [r'\*\*Morning.*?\*\*'],
                    "lunch": [r'\*\*Lunch.*?\*\*'],
                    "afternoon": [r'\*\*Afternoon.*?\*\*'],
                    "dinner": [r'\*\*Dinner.*?\*\*']
                }
                
                lines = day_content.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    
                    for block_key, patterns in blocks.items():
                        for p in patterns:
                            if re.search(p, line, re.IGNORECASE):
                                # Extract Place and Description
                                # Format: **Time:** [Place] — [Description] | [Price]
                                parts = line.split('**', 2)
                                if len(parts) >= 3:
                                    detail = parts[2].strip().lstrip(':').strip()
                                    # Split by — or |
                                    info_parts = re.split(r'[—|]', detail)
                                    place_name = info_parts[0].strip()
                                    desc = info_parts[1].strip() if len(info_parts) > 1 else ""
                                    
                                    day_entry[block_key] = {
                                        "place": place_name,
                                        "description": desc
                                    }
                                    
                                    # Auto-populate master lists
                                    if block_key in ["morning", "afternoon"]:
                                        if place_name and place_name not in [p['name'] for p in result["places"]]:
                                            result["places"].append({"name": place_name, "city": ""})
                                    elif block_key in ["lunch", "dinner"]:
                                        if place_name and place_name not in [r['name'] for r in result["restaurants"]]:
                                            result["restaurants"].append({"name": place_name, "city": ""})
                
                # Day Cost
                cost_match = re.search(r'Day Cost Estimate:\s*~?([\d,]+)', day_content)
                if cost_match:
                    day_entry["dayCost"] = cost_match.group(1)
                    
                result["itinerary"].append(day_entry)

    # Fallback to first section for overview if empty
    if not result["overview"] and trip_text:
        first_section = re.split(r'\n##', trip_text)[0].strip()
        # Remove the main # title if present
        first_section = re.sub(r'^#\s+.*?\n', '', first_section, flags=re.MULTILINE).strip()
        result["overview"] = first_section

    return result

@app.route('/api/trip', methods=['POST'])
def generate_trip():
    try:
        data = request.json
        
        destinations = data.get('destinations', ['Cairo & Giza'])
        budget = data.get('budget', '1000-2000 EGP')
        group_size = data.get('groupSize', 2)
        start_date = data.get('startDate', '')
        end_date = data.get('endDate', '')
        travel_styles = data.get('travelStyles', ['Historical', 'Food & Dining'])
        historical_knowledge = data.get('historicalKnowledge', 'Beginner')
        preferred_time_periods = data.get('preferredTimePeriods', ['Pharaonic', 'Islamic'])
        museum_visits = data.get('museumVisits', True)
        water_activities = data.get('waterActivities', False)
        accommodation_type = data.get('accommodationType', 'Medium')
        transportation = data.get('transportation', 'Private Car')
        food_preferences = data.get('foodPreferences', 'Vegetarian')
        trip_pace = data.get('tripPace', 'Moderate')
        must_visit = data.get('mustVisit', 'Pyramids')
        model = data.get('model')
        provider = data.get('provider')

        budget_min, budget_max = parse_budget(budget)

        city_map = {
            "Cairo & Giza": "cairo",
            "Alexandria": "alexandria",
            "Luxor": "luxor",
            "Aswan": "aswan",
            "Sharm El Sheikh": "sharm",
            "Hurghada": "hurghada",
            "Dahab": "dahab",
        }

        query_parts = []

        if "Historical" in travel_styles:
            if "Pharaonic" in preferred_time_periods:
                query_parts.append("pharaonic ancient pyramids temple historical site")
            if "Islamic" in preferred_time_periods:
                query_parts.append("islamic mosque old cairo historic")
            if "Coptic" in preferred_time_periods:
                query_parts.append("coptic church ancient christian")
            if museum_visits:
                query_parts.append("museum exhibition artifacts")
            if historical_knowledge == "Beginner":
                query_parts.append("introductory guided tour overview")

        if "Food & Dining" in travel_styles:
            if food_preferences == "Vegetarian":
                query_parts.append("vegetarian restaurant plant-based food")
            elif food_preferences == "Vegan":
                query_parts.append("vegan restaurant plant-based food")
            else:
                query_parts.append("restaurant local cuisine dining food")

        if "Water Activities" in travel_styles or water_activities:
            query_parts.append("water activities beach diving snorkeling")

        if accommodation_type == "Budget":
            query_parts.append("budget cheap affordable hotel")
        elif accommodation_type == "Medium":
            query_parts.append("mid-range moderate hotel comfortable")
        elif accommodation_type == "Luxury":
            query_parts.append("luxury premium 5-star resort spa")

        if must_visit:
            query_parts.append(must_visit)

        query = " ".join(query_parts) if query_parts else "tourist attractions restaurants hotels"

        results_places = []
        results_restaurants = []
        results_hotels = []

        for city_label in destinations:
            city = city_map.get(city_label, city_label.lower())
            places = search(query=query, entity_type="place", city=city, k=5)
            results_places.extend(places)
            restaurants = search(query=query, entity_type="restaurant", city=city, max_price=budget_max, k=5)
            results_restaurants.extend(restaurants)
            hotels = search(query=query, entity_type="hotel", city=city, max_price=budget_max, k=5)
            results_hotels.extend(hotels)

        try:
            summary = orchestrator.generate_summary(
                results_places, results_restaurants, results_hotels, destinations,
                model=model, provider=provider
            )
        except Exception as e:
            summary = f"Your trip to {', '.join(destinations)} is ready!"

        try:
            start_dt = datetime.fromisoformat(start_date) if start_date else datetime.now()
            end_dt = datetime.fromisoformat(end_date) if end_date else datetime.now()
        except:
            start_dt = datetime.now()
            end_dt = datetime.now()

        trip_plan_text = orchestrator.generate_trip_plan(
            destinations=destinations,
            budget=budget,
            group_size=group_size,
            start_date=start_dt,
            end_date=end_dt,
            travel_styles=travel_styles,
            historical_knowledge=historical_knowledge,
            preferred_time_periods=preferred_time_periods,
            museum_visits=museum_visits,
            water_activities=water_activities,
            accommodation_type=accommodation_type,
            transportation=transportation,
            food_preferences=food_preferences,
            trip_pace=trip_pace,
            must_visit=must_visit,
            places=results_places,
            restaurants=results_restaurants,
            hotels=results_hotels,
            model=model,
            provider=provider
        )

        parsed_plan = parse_trip_plan_to_json(trip_plan_text)

        # 1. Deterministic Budget Calculation
        computed_budget = calculate_realistic_budget(
            budget_min=budget_min,
            budget_max=budget_max,
            hotels=results_hotels,
            restaurants=results_restaurants,
            places=results_places,
            start_date=start_date,
            end_date=end_date,
            group_size=group_size,
            acc_type=accommodation_type,
            transportation=transportation
        )
        parsed_plan["budget"] = computed_budget

        # 2. Robust Data Enrichment (Images, Ratings, Prices)
        parsed_plan = enrich_trip_data(
            parsed_plan=parsed_plan,
            results_places=results_places,
            results_restaurants=results_restaurants,
            results_hotels=results_hotels
        )

        if not parsed_plan["overview"]:
            parsed_plan["overview"] = summary

        return jsonify(parsed_plan)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)