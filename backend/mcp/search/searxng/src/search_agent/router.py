from .schemas import ClassifierOutput

def route_query(classifier_output: ClassifierOutput) -> dict:
    """
    Maps ClassifierOutput to SearXNG query parameters.
    Returns a dictionary of parameters that can be passed directly to the SearXNG API.
    """
    # SearXNG built-in categories
    valid_searxng_categories = {
        "general", "news", "science", "it", "finance",
        "images", "videos", "map", "music", "files"
    }
    
    # Filter to valid SearXNG categories
    mapped_categories = [cat for cat in classifier_output.categories if cat in valid_searxng_categories]
    
    # Default to 'general' if no categories map properly
    if not mapped_categories:
        mapped_categories = ["general"]
        
    # Map natural language date ranges to SearXNG time_range enum ('day', 'week', 'month', 'year')
    time_range = None
    if classifier_output.date_range:
        dr_lower = classifier_output.date_range.lower()
        if "day" in dr_lower or "24 hours" in dr_lower or "today" in dr_lower:
            time_range = "day"
        elif "week" in dr_lower:
            time_range = "week"
        elif "month" in dr_lower:
            time_range = "month"
        elif "year" in dr_lower:
            time_range = "year"
            
    # Language defaults to en-US if none provided
    language = classifier_output.language_hint if classifier_output.language_hint else "en-US"
    
    # Determine federated sources based on categories
    sources = set()
    for cat in classifier_output.categories:
        if cat == "packages":
            sources.update(["pypi", "npm", "github", "fallback_docs"])
        elif cat == "it":
            sources.update(["fallback_docs", "searxng"])
        elif cat == "academic":
            sources.add("arxiv")
        elif cat == "economic":
            sources.update(["worldbank", "economic_databases", "searxng"])
        elif cat == "finance":
            sources.update(["yfinance", "economic_databases", "searxng"])
        elif cat == "patents":
            sources.update(["wipo", "searxng"])
        elif cat == "legal":
            sources.update(["indian_kanoon", "searxng"])
        elif cat == "news":
            sources.update(["rss_global_news", "gdelt", "searxng"])
        elif cat == "india_news":
            sources.update(["rss_india_news", "searxng"])
        elif cat == "india_public":
            sources.update(["rss_india_public", "searxng"])
        elif cat == "india_finance":
            sources.update(["nse", "bse", "yfinance", "economic_databases", "rss_india_finance", "searxng"])
        elif cat == "general":
            sources.update(["wikipedia", "searxng"])
        else:
            # Fallback to searxng for other topics
            sources.add("searxng")
            
    if not sources:
        sources.add("searxng")
            
    return {
        "categories": ",".join(mapped_categories),
        "time_range": time_range or "",
        "language": language,
        "sources": list(sources)
    }
