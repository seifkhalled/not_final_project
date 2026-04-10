import os
import json
from datetime import datetime
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
tavily = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None

if tavily:
    print("[Tavily] OK Client initialized successfully")
else:
    print("[Tavily] WARNING: No TAVILY_API_KEY found in .env - web search disabled")


TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "search_travel_info",
        "description": (
            "Search the web for real-time travel information about Egypt destinations. "
            "Use this to get current ticket prices, opening hours, recent reviews, "
            "events, weather, and to find specific restaurants or places the user mentioned."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Specific search query, e.g. "
                        f"'Pyramids of Giza ticket price {datetime.now().year}' or "
                        "'izoya restaurant Alexandria Egypt'"
                    ),
                },
                "destinations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Egypt destinations relevant to this search, e.g. ['Alexandria']",
                },
            },
            "required": ["query"],
        },
    },
}


def tavily_search(query: str, max_results: int = 5) -> list[dict]:
    if not tavily:
        print("[Tavily] Skipping — no API key")
        return []

    try:
        response = tavily.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",
            topic="general",
        )
        results = []
        for result in response.get("results", []):
            results.append({
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", ""),
                "score": result.get("score", 0),
            })
        print(f"[Tavily] '{query}' → {len(results)} results")
        return results
    except Exception as e:
        print(f"[Tavily] Error on '{query}': {e}")
        return []


def execute_tool_call(tool_call) -> str:
    if tool_call.function.name != "search_travel_info":
        return json.dumps({"error": f"Unknown tool: {tool_call.function.name}"})

    try:
        args = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON arguments"})

    query = args.get("query", "")

    # Only search for what the user actually asked — no generic filler queries
    all_results = []
    results = tavily_search(query, max_results=5)
    all_results.extend(results)

    if not all_results:
        return json.dumps({"error": "No results found", "query": query})

    destinations = args.get("destinations", [])
    formatted = []
    for r in all_results:
        formatted.append({
            "title": r["title"],
            "url": r["url"],
            "snippet": r["content"][:300],
        })

    return json.dumps({
        "query": query,
        "destinations": destinations,
        "results": formatted,
        "total_sources": len(formatted),
    })


def format_tavily_results(results: list[dict]) -> str:
    """Format Tavily results as markdown context. No HTTP side effects."""
    if not results:
        return ""

    lines = ["## 🌐 Real-Time Web Data (Tavily)"]
    seen_titles = set()
    for r in results:
        title = r.get("title", "Unknown")
        if title in seen_titles:
            continue
        seen_titles.add(title)
        snippet = r.get("content", r.get("snippet", ""))
        url = r.get("url", "")

        lines.append(f"- **{title}**")
        if snippet:
            lines.append(f"  {snippet[:250]}")
        if url:
            lines.append(f"  Source: {url}")

    lines.append("")
    return "\n".join(lines)


def search_destinations_proactive(
    destinations: list[str],
    travel_styles: list[str],
    must_visit: str = "",
    food_preferences: str = "",
) -> list[dict]:
    year = datetime.now().year
    queries = []

    if must_visit:
        for place in must_visit.split(","):
            place = place.strip()
            if place:
                dest = destinations[0] if destinations else "Egypt"
                queries.append(f"{place} {dest} Egypt review location {year}")

    for dest in destinations[:2]:
        queries.append(f"{dest} Egypt top attractions ticket prices {year}")
        if "Food & Dining" in travel_styles:
            pref = food_preferences if food_preferences != "No Preference" else ""
            queries.append(f"best {pref} restaurants {dest} Egypt {year}".strip())
        if "Historical" in travel_styles:
            queries.append(f"{dest} historical sites opening hours {year}")

    all_results = []
    seen = set()
    for q in queries[:5]:
        if q in seen:
            continue
        seen.add(q)
        results = tavily_search(q, max_results=3)
        all_results.extend(results)

    return all_results
