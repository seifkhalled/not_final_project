import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai.config import AIConfig
from ai.client import LLMClient, LLMResponse
from ai.prompts import SystemPrompts
from src.trip_planner import (
    generate_trip_plan as _generate_trip_plan,
)


class TripOrchestrator:
    def __init__(self):
        self.client = LLMClient()
        self.last_summary_tokens = None
        self.last_trip_plan_tokens = None

    @staticmethod
    def format_search_results(places, restaurants, hotels):
        lines = []

        if places:
            lines.append("## Places to Visit")
            for p in places:
                meta = p.get("metadata", {})
                lines.append(f"- **{meta.get('name', p.get('name', 'Unknown'))}** ({p.get('city', '')})")
                if meta.get("address"):
                    lines.append(f"  Address: {meta['address']}")
                if meta.get("rating"):
                    lines.append(f"  Rating: {meta['rating']}/5")
                if meta.get("ticket_price"):
                    lines.append(f"  Ticket: {meta['ticket_price']} EGP")
                if meta.get("timings"):
                    lines.append(f"  Hours: {meta['timings']}")
                if p.get("document"):
                    doc = p['document']
                    truncated = doc[:200] + ('...' if len(doc) > 200 else '')
                    lines.append(f"  Info: {truncated}")
            lines.append("")

        if restaurants:
            lines.append("## Restaurants")
            for r in restaurants:
                meta = r.get("metadata", {})
                lines.append(f"- **{meta.get('name', r.get('name', 'Unknown'))}** ({r.get('city', '')})")
                if meta.get("cuisines"):
                    lines.append(f"  Cuisines: {meta['cuisines']}")
                if meta.get("avg_price"):
                    lines.append(f"  Avg Price: ~{meta['avg_price']} EGP")
                if meta.get("location"):
                    lines.append(f"  Location: {meta['location']}")
            lines.append("")

        if hotels:
            lines.append("## Hotels")
            for h in hotels:
                meta = h.get("metadata", {})
                lines.append(f"- **{meta.get('name', h.get('name', 'Unknown'))}** ({h.get('city', '')})")
                if meta.get("rating"):
                    lines.append(f"  Rating: {meta['rating']}/10")
                if meta.get("price"):
                    lines.append(f"  Price: {meta['price']} EGP")
                if meta.get("distance_km"):
                    lines.append(f"  Distance from center: {meta['distance_km']} km")
            lines.append("")

        return "\n".join(lines) if lines else "No specific results found."

    def generate_summary(self, places, restaurants, hotels, destinations, model=None, provider=None):
        context = self.format_search_results(places, restaurants, hotels)
        prompt = SystemPrompts.summary_prompt(destinations, context)
        result: LLMResponse = self.client.chat(
            SystemPrompts.SUMMARY, 
            prompt, 
            max_tokens=AIConfig.LLM_SUMMARY_MAX_TOKEMENT_TOKENS,
            model=model,
            provider=provider
        )
        self.last_summary_tokens = result
        return result.content

    def generate_trip_plan(
        self,
        destinations, budget, group_size, start_date, end_date,
        travel_styles, historical_knowledge, preferred_time_periods,
        museum_visits, water_activities, accommodation_type,
        transportation, food_preferences, trip_pace, must_visit,
        places, restaurants, hotels,
        model=None, provider=None
    ):
        result = _generate_trip_plan(
            destinations=destinations,
            budget=budget,
            group_size=group_size,
            start_date=start_date,
            end_date=end_date,
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
            places_results=places,
            restaurants_results=restaurants,
            hotels_results=hotels,
            model=model,
            provider=provider
        )
        self.last_trip_plan_tokens = result
        return result.content if hasattr(result, 'content') else result