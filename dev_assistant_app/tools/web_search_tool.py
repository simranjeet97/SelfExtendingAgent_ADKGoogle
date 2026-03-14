"""
web_search_tool.py

A web search ADK tool using the Tavily Search API.
Call this before write_new_skill to gather real, up-to-date information
that will be embedded into the SKILL.md content.
"""

import logging
from typing import Any

logger = logging.getLogger("web_search_tool")


def web_search(query: str, max_results: int = 5) -> dict:
    """
    Searches the web using DuckDuckGo and returns the top results.

    Use this tool FIRST before calling write_new_skill. Search for the topic
    the user is asking about to gather real, accurate, up-to-date information.
    Then embed that knowledge into the SKILL.md content you write.

    Args:
        query: The search query string. Be specific — include the technology
               name and what you want to learn, e.g.:
               "Redis in-memory database key concepts tutorial"
               "FastAPI Python REST API best practices"
               "Docker container orchestration commands"
        max_results: Number of results to return. Default 5 is usually enough.

    Returns:
        dict with:
          - "query": the search query used
          - "results": list of { "title", "url", "snippet" } dicts
          - "error": error message if search failed (results will be empty)

    Example:
        web_search("Redis data structures tutorial best practices")
        → {
            "query": "Redis data structures tutorial best practices",
            "results": [
              {"title": "Redis Data Types", "url": "https://redis.io/docs/...", "snippet": "..."},
              ...
            ]
          }
    """
    try:
        from tavily import TavilyClient
    except ImportError:
        logger.error("tavily-python package not installed. Run: pip install tavily-python")
        return {
            "query": query,
            "results": [],
            "error": "tavily-python package not installed. Run: pip install tavily-python"
        }

    import os
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        return {
            "query": query,
            "results": [],
            "error": "TAVILY_API_KEY is not set. Add it to dev_assistant_app/.env"
        }
    client = TavilyClient(api_key=api_key)

    try:
        # User requested max 2 results
        # search_depth="advanced" generates high-quality snippets perfect for SKILL.md
        response = client.search(
            query=query,
            max_results=2,
            search_depth="advanced",
            include_answer=True
        )

        results = []
        for r in response.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", ""),
            })

        logger.info(f"WEB_SEARCH (Tavily): query='{query}' returned {len(results)} results")
        return {"query": query, "results": results}

    except Exception as e:
        logger.warning(f"WEB_SEARCH (Tavily): Search failed for '{query}': {e}")
        return {
            "query": query,
            "results": [],
            "error": str(e)
        }
