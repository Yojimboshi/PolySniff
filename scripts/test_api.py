"""Fetch markets from Polymarket Gamma API by closing-time window, then categorize."""

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

# Server-side filter: Gamma /markets?end_date_min=…&end_date_max=… (UTC). This is the primary query.
CLOSING_WINDOW_HOURS = 6

GAMMA_MARKETS_URL = "https://gamma-api.polymarket.com/markets"
HTTP_USER_AGENT = "PolySniff/1.0"

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MARKET_DATA_DIR = _REPO_ROOT / "data"
CATEGORIZED_MARKETS_JSON = _MARKET_DATA_DIR / "categorized_markets.json"


# Market categories and their keywords for classification
MARKET_CATEGORIES = {
    "Politics": [
        "election", "president", "biden", "trump", "congress", "senate", "house", "vote", "voting",
        "democrat", "republican", "political", "politics", "campaign", "candidate", "governor",
        "mayor", "primary", "ballot", "poll", "approval", "impeach", "cabinet", "supreme court"
    ],
    "Sports": [
        "nba", "nfl", "mlb", "nhl", "ncaa", "ncaab", "ncaaf", "soccer", "football", "basketball",
        "baseball", "hockey", "tennis", "golf", "olympics", "world cup", "championship", "playoffs",
        "super bowl", "world series", "stanley cup", "march madness", "fifa", "uefa", "premier league"
    ],
    "Crypto": [
        "bitcoin", "btc", "ethereum", "eth", "crypto", "cryptocurrency", "blockchain", "defi",
        "nft", "dogecoin", "doge", "solana", "sol", "cardano", "ada", "binance", "bnb",
        "polygon", "matic", "avalanche", "avax", "chainlink", "link", "uniswap", "uni"
    ],
    "Iran": [
        "iran", "iranian", "tehran", "persian", "middle east", "sanctions", "nuclear", "iaea",
        "khamenei", "rouhani", "raisi", "persian gulf", "strait of hormuz"
    ],
    "Finance": [
        "stock", "stocks", "market", "dow", "nasdaq", "s&p", "sp500", "fed", "federal reserve",
        "interest rate", "inflation", "gdp", "unemployment", "recession", "bull market", "bear market",
        "earnings", "ipo", "merger", "acquisition", "bank", "banking", "financial", "economy"
    ],
    "Geopolitics": [
        "war", "conflict", "ukraine", "russia", "china", "taiwan", "north korea", "syria",
        "afghanistan", "israel", "palestine", "nato", "un", "united nations", "sanctions",
        "treaty", "diplomacy", "military", "invasion", "ceasefire", "peace", "alliance"
    ],
    "Tech": [
        "tech", "technology", "ai", "artificial intelligence", "apple", "google", "microsoft",
        "amazon", "meta", "facebook", "twitter", "tesla", "spacex", "nvidia", "amd", "intel",
        "software", "hardware", "startup", "ipo", "venture capital", "silicon valley"
    ]
}


def categorize_market(market: Dict[str, Any]) -> str:
    """
    Categorize a market based on its question, description, and tags.
    
    Args:
        market: Market dictionary from Polymarket API
        
    Returns:
        Category name or "Other" if no match found
    """
    # Get text to analyze
    question = (market.get("question") or "").lower()
    description = (market.get("description") or "").lower()
    tags_raw = market.get("tags") or []
    tags = [tag.lower() for tag in tags_raw if tag is not None]
    
    # Combine all text for analysis
    combined_text = f"{question} {description} {' '.join(tags)}"
    
    # Check each category with scoring system to handle overlaps
    category_scores = {}
    
    for category, keywords in MARKET_CATEGORIES.items():
        score = 0
        for keyword in keywords:
            # Count occurrences of keyword
            keyword_count = combined_text.count(keyword.lower())
            if keyword_count > 0:
                # Weight longer keywords more heavily
                weight = len(keyword.split())
                score += keyword_count * weight
        
        if score > 0:
            category_scores[category] = score
    
    # Return category with highest score, or "Other" if no matches
    if category_scores:
        return max(category_scores, key=category_scores.get)
    
    return "Other"


def _parse_json_field(raw: Any) -> Any:
    if raw is None:
        return None
    if isinstance(raw, (list, dict)):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    return None


def normalize_gamma_market(m: Dict[str, Any]) -> Dict[str, Any]:
    """Map Gamma market payload to the shape used by parse_end_time / print_market_summary."""
    out = dict(m)
    end = m.get("endDate") or m.get("end_date_iso")
    if end:
        out["end_date_iso"] = end
    cid = m.get("conditionId") or m.get("condition_id")
    if cid:
        out["condition_id"] = cid

    tags: List[str] = []
    gc = m.get("category")
    if gc:
        tags.append(str(gc))
    if m.get("tags"):
        for t in m.get("tags") or []:
            if t is not None:
                tags.append(str(t))
    out["tags"] = tags

    outcomes = _parse_json_field(m.get("outcomes")) or []
    prices = _parse_json_field(m.get("outcomePrices")) or []
    tokens = []
    for i, label in enumerate(outcomes):
        p = float(prices[i]) if i < len(prices) else 0.5
        tokens.append({"outcome": label, "price": p})
    out["tokens"] = tokens
    return out


def fetch_gamma_markets_closing_within_hours(hours: float) -> List[Dict[str, Any]]:
    """
    Primary data path: Gamma API with end_date_min / end_date_max (UTC), closed=false, paginated.
    """
    now = datetime.now(timezone.utc)
    end = now + timedelta(hours=hours)

    def _fmt(t: datetime) -> str:
        return t.strftime("%Y-%m-%dT%H:%M:%SZ")

    collected: List[Dict[str, Any]] = []
    offset = 0
    page_limit = 500
    n_requests = 0

    while True:
        n_requests += 1
        q = urllib.parse.urlencode(
            {
                "closed": "false",
                "limit": str(page_limit),
                "offset": str(offset),
                "end_date_min": _fmt(now),
                "end_date_max": _fmt(end),
            }
        )
        url = f"{GAMMA_MARKETS_URL}?{q}"
        req = urllib.request.Request(url, headers={"User-Agent": HTTP_USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                batch = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Gamma API HTTP {e.code}: {e.reason}") from e

        if not batch:
            break
        collected.extend(normalize_gamma_market(m) for m in batch if isinstance(m, dict))
        if len(batch) < page_limit:
            break
        offset += page_limit

    # One endpoint, one query shape; extra GETs only when Gamma returns a full page (pagination).
    print(
        f"Gamma HTTP: {n_requests} GET request(s) to /markets "
        f"(up to {page_limit} markets per page)."
    )
    return collected


def parse_end_time(market: Dict[str, Any]) -> Optional[datetime]:
    """
    Parse the end time from a market dictionary.
    
    Args:
        market: Market dictionary
        
    Returns:
        datetime object or None if parsing fails
    """
    end_date_iso = market.get("end_date_iso")
    if not end_date_iso:
        return None
    
    try:
        # Handle both "Z" suffix and timezone-aware formats
        if end_date_iso.endswith("Z"):
            date_str = end_date_iso.replace("Z", "+00:00")
        else:
            date_str = end_date_iso
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt
    except (ValueError, AttributeError):
        return None


def filter_closing_within_next_hours(
    markets: List[Dict[str, Any]],
    hours: float,
    *,
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Keep markets whose end time is strictly in the future and at or before now + hours (UTC).
    """
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    else:
        now = now.astimezone(timezone.utc)

    window_end = now + timedelta(hours=hours)
    result: List[Dict[str, Any]] = []
    for market in markets:
        end_time = parse_end_time(market)
        if end_time is None:
            continue
        if now < end_time <= window_end:
            m = dict(market)
            m["_parsed_end_time"] = end_time
            result.append(m)

    result.sort(key=lambda m: m["_parsed_end_time"])
    return result


def categorized_to_json_dict(
    categorized_markets: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Strip runtime fields and attach category for each market."""
    json_data: Dict[str, Any] = {}
    for category, markets in categorized_markets.items():
        json_markets = []
        for market in markets:
            market_copy = {k: v for k, v in market.items() if k != "_parsed_end_time"}
            market_copy["category"] = category
            json_markets.append(market_copy)
        json_data[category] = json_markets
    return json_data


def write_categorized_json(path: Path, categorized_markets: Dict[str, List[Dict[str, Any]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(categorized_to_json_dict(categorized_markets), f, indent=2)


def filter_markets_by_categories(
    markets: List[Dict[str, Any]],
    categories: List[str],
    markets_per_category: Optional[int] = 5,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Filter and categorize markets, returning up to markets_per_category per bucket (None = no cap).
    """
    # Categorize all markets
    categorized_markets = {}
    for category in categories:
        categorized_markets[category] = []
    
    for market in markets:
        category = categorize_market(market)
        if category in categories:
            categorized_markets[category].append(market)
    
    # Sort each category by end time (soonest first) and limit results
    for category in categories:
        # Filter out markets without end times and sort
        markets_with_end_times = []
        for market in categorized_markets[category]:
            end_time = parse_end_time(market)
            if end_time:
                market['_parsed_end_time'] = end_time
                markets_with_end_times.append(market)
        
        # Sort by end time (soonest first)
        markets_with_end_times.sort(key=lambda m: m['_parsed_end_time'])
        
        if markets_per_category is not None:
            markets_with_end_times = markets_with_end_times[:markets_per_category]
        categorized_markets[category] = markets_with_end_times
    
    return categorized_markets


# def print_market_summary(market: Dict[str, Any], category: str = None) -> None:
    """Print a formatted summary of a market."""
    # Extract market ID (condition_id is the primary identifier)
    market_id = market.get("condition_id") or market.get("id") or market.get("market_id") or "unknown"
    
    # Extract question
    question = market.get("question") or market.get("title") or market.get("description", "N/A")
    
    # Extract prices from tokens array
    tokens = market.get("tokens", [])
    yes_price = 0.5
    no_price = 0.5
    
    if tokens:
        if len(tokens) >= 2:
            yes_price = float(tokens[0].get("price", 0.5))
            no_price = float(tokens[1].get("price", 0.5))
        elif len(tokens) == 1:
            yes_price = float(tokens[0].get("price", 0.5))
            no_price = 1.0 - yes_price
    
    # Market status
    closed = market.get("closed", False)
    active = market.get("active", False)
    status = "CLOSED" if closed else ("ACTIVE" if active else "INACTIVE")
    
    # End date (most important for filtering)
    end_date = market.get("end_date_iso", "N/A")
    end_time_parsed = market.get("_parsed_end_time")
    
    # Format end time for display
    if end_time_parsed:
        end_time_display = end_time_parsed.strftime("%Y-%m-%d %H:%M UTC")
        # Calculate time until end
        now = datetime.now(timezone.utc)
        time_until_end = end_time_parsed - now
        if time_until_end.total_seconds() > 0:
            days = time_until_end.days
            hours, remainder = divmod(time_until_end.seconds, 3600)
            if days > 0:
                time_until_display = f"{days}d {hours}h remaining"
            else:
                time_until_display = f"{hours}h remaining"
        else:
            time_until_display = "ENDED"
    else:
        end_time_display = end_date
        time_until_display = "Unknown"
    
    # Category
    if not category:
        category = categorize_market(market)
    
    print(f"\n{'='*70}")
    print(f"CATEGORY: {category.upper()}")
    print(f"END TIME: {end_time_display} ({time_until_display})")
    print(f"STATUS: {status}")
    print(f"QUESTION: {question}")
    print(f"Market ID: {market_id[:16]}...")
    
    if tokens:
        print(f"PRICES:")
        for i, token in enumerate(tokens[:2]):
            outcome = token.get('outcome', f'Outcome {i+1}')
            price = float(token.get('price', 0))
            percentage = price * 100
            print(f"   {outcome}: {price:.3f} ({percentage:.1f}%)")
    
    print(f"{'='*70}")


def main():
    """Gamma API (end_date window) → optional local tighten → categorize → one JSON file."""
    target_categories = ["Politics", "Sports", "Crypto", "Iran", "Finance", "Geopolitics", "Tech"]
    markets_per_category: Optional[int] = None  # no per-category cap for this window

    print("=" * 70)
    print("Gamma API (primary): open markets with end_date in the UTC window below.")
    print(f"  {GAMMA_MARKETS_URL}")
    print(f"  Window: now → now + {CLOSING_WINDOW_HOURS}h (UTC)")
    print("=" * 70)

    try:
        print("Requesting markets from Gamma…")
        raw = fetch_gamma_markets_closing_within_hours(CLOSING_WINDOW_HOURS)
        print(f"Gamma returned {len(raw)} market(s) in that window.")

        closing_soon = filter_closing_within_next_hours(raw, CLOSING_WINDOW_HOURS)
        print(
            f"After strict local check (now < end ≤ now+{CLOSING_WINDOW_HOURS}h UTC): {len(closing_soon)}"
        )

        print(f"Categorizing into: {', '.join(target_categories)}")
        categorized_markets = filter_markets_by_categories(
            closing_soon,
            target_categories,
            markets_per_category,
        )
        
        # Display results by category
        total_filtered = 0
        for category in target_categories:
            markets_in_category = categorized_markets[category]
            total_filtered += len(markets_in_category)
            
            print(f"\n{category.upper()} MARKETS ({len(markets_in_category)} found, sorted by end time)")
            print("-" * 70)
            
            if not markets_in_category:
                print(f"   No {category} markets found in current dataset")
                continue
            
            for i, market in enumerate(markets_in_category, 1):
                print(f"\n--- {category} Market {i} ---")
                # print_market_summary(market, category)
        
        print("\nSUMMARY")
        print("=" * 70)
        print(f"In window (Gamma + local check): {len(closing_soon)}")
        print(f"Total in target categories (shown): {total_filtered}")
        print(f"Categories: {len(target_categories)}")

        for category in target_categories:
            count = len(categorized_markets[category])
            print(f"  {category}: {count} markets")

        write_categorized_json(CATEGORIZED_MARKETS_JSON, categorized_markets)
        print(f"\nSaved: {CATEGORIZED_MARKETS_JSON}")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
