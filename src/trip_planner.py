import os
import re
import json
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime

from src.search_tools import (
    TOOL_DEFINITION,
    execute_tool_call,
    format_tavily_results,
    search_destinations_proactive,
)
from src.pexels_service import fetch_pexels_photos, get_place_image_url
from src.utils import clean_name, truncate_context, safe_llm_call

load_dotenv()

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Groq configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Separate env vars for trip generation vs. tool calling models
LLM_MODEL = os.getenv("OPENROUTER_TRIP_MODEL", "nvidia/nemotron-3-nano-30b-a3b:free")
TOOL_CALL_MODEL = os.getenv("OPENROUTER_TOOL_MODEL", "nvidia/nemotron-3-nano-30b-a3b:free")

# Fallback model lists per provider
_OPENROUTER_FALLBACK_MODELS = [
    LLM_MODEL,
    "google/gemma-3-12b-it:free",
    "deepseek/deepseek-r1-distill-llama-70b:free",
    "meta-llama/llama-4-scout:free",
]

_GROQ_FALLBACK_MODELS = [
    os.getenv("LLM_MODEL", "llama-3.1-8b-instant"),
    "llama-3.3-70b-versatile",
]

# ==============================
# LAZY CLIENT INITIALIZER
# ==============================

_clients: dict = {}


def get_client(provider: str = "openrouter") -> OpenAI:
    """Return a provider-specific OpenAI-compatible client, creating it on first call."""
    global _clients
    if provider not in _clients:
        if provider == "groq":
            _clients["groq"] = OpenAI(
                base_url=GROQ_BASE_URL,
                api_key=GROQ_API_KEY,
            )
        else:
            _clients["openrouter"] = OpenAI(
                base_url=OPENROUTER_BASE_URL,
                api_key=OPENROUTER_API_KEY,
            )
    return _clients[provider]


# ==============================
# DEDUPLICATE + CLEAN RESULTS
# ==============================

def deduplicate_results(items: list[dict]) -> list[dict]:
    """Keep only the first occurrence of each unique place/restaurant/hotel."""
    seen = set()
    unique = []
    for item in items:
        raw_name = item.get("name") or item.get("metadata", {}).get("name", "")
        base_name = clean_name(raw_name)
        if base_name and base_name not in seen:
            seen.add(base_name)
            item["name"] = base_name
            if "metadata" in item and item["metadata"].get("name"):
                item["metadata"]["name"] = base_name
            unique.append(item)
    return unique


# ==============================
# FORMAT RESULTS FOR PROMPT (compact, token-efficient)
# ==============================

def format_search_results(places, restaurants, hotels):
    """Format DB results into a compact markdown string. No HTTP calls."""
    lines = []

    if places:
        lines.append("### Places to Visit")
        for p in deduplicate_results(places):
            meta = p.get("metadata", {})
            name = clean_name(p.get("name") or meta.get("name", "Unknown"))
            city = p.get("city", meta.get("city", ""))
            rating = meta.get("rating", "N/A")
            ticket = meta.get("ticket_price", "")
            address = meta.get("address", "")
            timings = meta.get("timings", "")

            line = f"- {name} ({city})"
            if rating and rating != "N/A":
                line += f" | ⭐{rating}/5"
            if ticket:
                line += f" | 🎫{ticket} EGP"
            if address:
                line += f" | 📍{address}"
            if timings:
                line += f" | ⏰{timings}"
            lines.append(line)
        lines.append("")

    if restaurants:
        lines.append("### Restaurants")
        for r in deduplicate_results(restaurants):
            meta = r.get("metadata", {})
            name = clean_name(r.get("name") or meta.get("name", "Unknown"))
            city = r.get("city", meta.get("city", ""))
            cuisines = meta.get("cuisines", "")
            avg_price = meta.get("avg_price", "")
            location = meta.get("location", meta.get("address", ""))

            line = f"- {name} ({city})"
            if cuisines:
                line += f" | 🍴{cuisines}"
            if avg_price:
                line += f" | 💰~{avg_price} EGP/person"
            if location:
                line += f" | 📍{location}"
            lines.append(line)
        lines.append("")

    if hotels:
        lines.append("### Hotels")
        for h in deduplicate_results(hotels):
            meta = h.get("metadata", {})
            name = clean_name(h.get("name") or meta.get("name", "Unknown"))
            city = h.get("city", meta.get("city", ""))
            rating = meta.get("rating", meta.get("stars", "N/A"))
            price = meta.get("price", meta.get("price_per_night", ""))
            dist = meta.get("distance_km", "")

            line = f"- {name} ({city})"
            if rating and str(rating) not in ("N/A", "None", "0"):
                line += f" | ⭐{rating}/10"
            if price:
                line += f" | 💰{price} EGP/night"
            if dist:
                line += f" | 📍{dist}km from center"
            lines.append(line)
        lines.append("")

    return "\n".join(lines) if lines else "No specific results found in database."


# ==============================
# OPTIONAL: ENRICH ITEMS WITH IMAGES
# ==============================

def enrich_with_images(items: list[dict]) -> list[dict]:
    """
    Fetch a Pexels image URL for each item and store it under item['image_url'].
    Call this AFTER format_search_results() only when images are needed.
    """
    for item in items:
        meta = item.get("metadata", {})
        name = item.get("name") or meta.get("name", "")
        city = item.get("city", meta.get("city", ""))
        try:
            item["image_url"] = get_place_image_url(name, city)
        except Exception:
            item["image_url"] = None
    return items


# ==============================
# PHASE 1: TOOL CALLING (let model decide what to search)
# ==============================

def run_tool_calling_phase(
    destinations, budget, group_size, start_date, end_date,
    travel_styles, historical_knowledge, preferred_time_periods,
    museum_visits, water_activities, accommodation_type,
    transportation, food_preferences, trip_pace, must_visit,
    db_context,
):
    client = get_client()
    num_days = max(1, (end_date - start_date).days + 1)

    system_msg = (
        "You are an Egypt travel planning assistant with web search capability. "
        "You have a curated database of places, restaurants, and hotels. "
        "Use the search_travel_info tool to find: current ticket prices, opening hours, "
        "specific restaurants the user mentioned (must-visit), or any place not in the database. "
        "Always search for must-visit places the user specified."
    )

    must_visit_instruction = ""
    if must_visit:
        must_visit_instruction = (
            f"\n⚠️ IMPORTANT: The user specifically wants to visit: '{must_visit}'. "
            f"Search for this place immediately — it may not be in the database."
        )

    user_msg = f"""USER TRIP REQUEST:
- Destinations: {', '.join(destinations)}
- Budget: {budget} EGP | Group: {group_size} people
- Dates: {start_date.strftime('%b %d')} to {end_date.strftime('%b %d, %Y')} ({num_days} days)
- Travel Styles: {', '.join(travel_styles)}
- Food Preference: {food_preferences}
- Must Visit: {must_visit if must_visit else 'None'}{must_visit_instruction}

DATABASE RESULTS (already retrieved):
{db_context}

Search the web for any missing info, especially the must-visit place and current prices."""

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    tavily_results = []

    try:
        response = client.chat.completions.create(
            model=TOOL_CALL_MODEL,
            messages=messages,
            tools=[TOOL_DEFINITION],
            tool_choice="auto",
            temperature=0.2,
            max_tokens=512,
        )

        finish_reason = response.choices[0].finish_reason
        print(f"\n[Tool Calling] Finish reason: {finish_reason}")

        if response.choices[0].message.tool_calls:
            for tool_call in response.choices[0].message.tool_calls:
                print(f"[Tool Calling] Calling: {tool_call.function.name}({tool_call.function.arguments})")
                tool_result = execute_tool_call(tool_call)
                result_data = json.loads(tool_result)
                tavily_results.extend(result_data.get("results", []))

                messages.append(response.choices[0].message)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })
                print(f"[Tool Calling] Got {len(result_data.get('results', []))} results")
        else:
            print("[Tool Calling] Model skipped web search — using DB only")

    except Exception as e:
        print(f"[Tool Calling] Error: {e}")

    return tavily_results, messages


# ==============================
# PHASE 2: FINAL TRIP PLAN GENERATION
# ==============================

def generate_trip_plan(
    destinations, budget, group_size, start_date, end_date,
    travel_styles, historical_knowledge, preferred_time_periods,
    museum_visits, water_activities, accommodation_type,
    transportation, food_preferences, trip_pace, must_visit,
    places_results, restaurants_results, hotels_results,
    model=None, provider=None,
):
    provider = provider or "openrouter"
    client = get_client(provider)
    num_days = max(1, (end_date - start_date).days + 1)

    budget_raw = budget
    budget_max = 99999
    if isinstance(budget, str):
        cleaned = budget.replace(" EGP", "").replace("+", "-99999")
        try:
            parts = cleaned.split("-")
            budget_max = int(parts[-1].strip())
        except (ValueError, IndexError):
            pass

    budget_per_day = budget_max // num_days if num_days > 0 else budget_max
    budget_per_person = budget_max // group_size if group_size > 0 else budget_max

    # Format and deduplicate DB results
    db_context = format_search_results(places_results, restaurants_results, hotels_results)

    # Phase 1: Tool calling
    print("\n[Phase 1] Tool-calling phase...")
    tavily_results, _ = run_tool_calling_phase(
        destinations, budget, group_size, start_date, end_date,
        travel_styles, historical_knowledge, preferred_time_periods,
        museum_visits, water_activities, accommodation_type,
        transportation, food_preferences, trip_pace, must_visit,
        db_context,
    )

    # Phase 1b: Proactive search if tool calling returned nothing
    if not tavily_results:
        print("[Phase 1b] Running proactive Tavily search...")
        tavily_results = search_destinations_proactive(
            destinations=destinations,
            travel_styles=travel_styles,
            must_visit=must_visit,
            food_preferences=food_preferences,
        )

    tavily_context = format_tavily_results(tavily_results)

    # Combine contexts
    combined_context = db_context
    if tavily_context:
        combined_context += "\n" + tavily_context
        print(f"[Phase 2] Using DB + {len(tavily_results)} web results")
    else:
        print("[Phase 2] Using DB only (no web results)")

    # Truncate combined context to prevent LLM context overflow
    combined_context = truncate_context(combined_context, max_chars=25000)

    # Build must-visit enforcement string
    must_visit_block = ""
    if must_visit:
        must_visit_block = f"""
⚠️ MUST-VISIT REQUIREMENT:
The user MUST visit: {must_visit}
Include this in the itinerary even if it's not in the database. Use web results or general knowledge."""

    # Build time period context
    periods_str = ", ".join(preferred_time_periods) if preferred_time_periods else "any"

    print(f"[Phase 2] Generating trip plan with {LLM_MODEL}...")

    system_prompt = f"""You are an expert Egypt travel planner. Generate detailed, practical trip plans.

STRICT RULES:
- Only list REAL places from the provided data — do NOT invent fictional sections or variations
- Each place appears ONCE maximum in the entire plan
- Do NOT fabricate opening hours — write "Check locally" if unknown
- Always include the must-visit place the user specified
- Tailor the plan to the user's knowledge level, budget, pace, and food preferences
- BUDGET ENFORCEMENT: Total budget is {budget_raw} (max {budget_max} EGP). The total MUST NOT exceed {budget_max} EGP.
  - Daily spending cap: ~{budget_per_day} EGP/day
  - Per-person cap: ~{budget_per_person} EGP/person
  - Hotel cost: {budget_per_day * 0.4:.0f} EGP/day max (40% of daily budget)
  - Food cost: {budget_per_day * 0.3:.0f} EGP/day max (30% of daily budget)
  - Activities: {budget_per_day * 0.2:.0f} EGP/day max (20% of daily budget)
  - Transport: {budget_per_day * 0.1:.0f} EGP/day max (10% of daily budget)
- Calculate realistic costs based on group size and budget
- Format as clean markdown"""

    user_prompt = f"""Create a {num_days}-day trip plan for {', '.join(destinations)}, Egypt.

USER PREFERENCES:
- Budget: {budget_raw} (max {budget_max} EGP for {group_size} people over {num_days} days)
  - Daily cap: ~{budget_per_day} EGP | Per person: ~{budget_per_person} EGP
- Dates: {start_date.strftime('%b %d')} → {end_date.strftime('%b %d, %Y')} ({num_days} days)
- Travel Styles: {', '.join(travel_styles)}
- Historical Knowledge: {historical_knowledge} (adjust explanations accordingly)
- Preferred Eras: {periods_str}
- Museum Visits: {'Yes' if museum_visits else 'No'}
- Water Activities: {'Yes' if water_activities else 'No'}
- Accommodation: {accommodation_type}
- Transportation: {transportation}
- Food Preference: {food_preferences}
- Trip Pace: {trip_pace} (Relaxed=2-3 stops/day, Moderate=3-4, Fast=5+)
{must_visit_block}

AVAILABLE DATA:
{combined_context}

Generate the trip plan with this structure:

# 🇪🇬 Trip Plan: {', '.join(destinations)}
## Overview (2-3 sentences)

## Day-by-Day Itinerary
### Day 1 — [Date: {start_date.strftime('%b %d')}]
**Morning (9:00–12:00):** [Place from data] — [brief description for {historical_knowledge} level] | Ticket: X EGP
**Lunch (12:30):** [Restaurant from data] — [cuisine] | ~X EGP/person
**Afternoon (14:00–17:00):** [Place from data] | Ticket: X EGP
**Dinner (19:00):** [Restaurant from data] | ~X EGP/person
**Transport:** [How to get around using {transportation}]
**Day Cost Estimate:** ~X EGP for {group_size} people

[Continue for all {num_days} days...]

## 🏨 Recommended Hotel
[Pick best match from hotels data for {accommodation_type} budget]
Price: X EGP/night × {num_days} nights = X EGP total

## 💰 Budget Breakdown
- Accommodation: X EGP
- Food: X EGP  
- Activities & Tickets: X EGP
- Transportation: X EGP
- **Total: X EGP** (Budget: {budget_raw} — MUST be ≤ {budget_max} EGP)

## 💡 Tips
- 3-4 practical tips for this specific trip"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Build models to try based on provider and user choice
    if provider == "groq":
        fallbacks = _GROQ_FALLBACK_MODELS
    else:
        fallbacks = _OPENROUTER_FALLBACK_MODELS

    if model and model not in fallbacks:
        models_to_try = [model] + fallbacks
    else:
        models_to_try = fallbacks if not model else [model] + [m for m in fallbacks if m != model]

    print(f"[Phase 2] Generating trip plan with {models_to_try[0]} (provider: {provider})...")

    result = safe_llm_call(
        client=client,
        models=models_to_try,
        messages=messages,
        temperature=0.6,
        max_tokens=2500,
    )

    if result is None:
        raise Exception("All models rate-limited. Please try again later.")

    return result


# ==============================
# SHORT SUMMARY (for top of results)
# ==============================

def generate_short_summary(places_results, restaurants_results, hotels_results, destinations):
    client = get_client("openrouter")
    context = format_search_results(places_results, restaurants_results, hotels_results)

    messages = [
        {
            "role": "system",
            "content": "You are a travel expert. Give a concise 2-3 sentence summary.",
        },
        {
            "role": "user",
            "content": f"Summarize what travelers can expect in {', '.join(destinations)}, Egypt based on:\n{context}",
        },
    ]

    result = safe_llm_call(
        client=client,
        models=_OPENROUTER_FALLBACK_MODELS,
        messages=messages,
        temperature=0.7,
        max_tokens=200,
    )

    if result is None:
        raise Exception("All models rate-limited. Please try again later.")

    return result