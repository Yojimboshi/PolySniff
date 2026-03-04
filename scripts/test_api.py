"""Simple API test script to fetch market data from Polymarket using the SDK."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

from py_clob_client.client import ClobClient


def get_markets(limit: int = 5, start_date_max_yesterday: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch markets from Polymarket using the SDK.
    
    NOTE: No authentication needed for market data - it's public!
    
    Args:
        limit: Number of markets to fetch
        start_date_max_yesterday: If True, filter for markets with start date max = yesterday
        
    Returns:
        List of market dictionaries
    """
    # Initialize client - no auth needed for public data
    client = ClobClient("https://clob.polymarket.com")
    
    # Calculate yesterday's date for filtering
    yesterday = (datetime.now() - timedelta(days=1)).date()
    yesterday_str = yesterday.strftime("%Y-%m-%d")
    yesterday_max = f"{yesterday_str}T23:59:59Z"
    
    # Fetch more markets if filtering by date (to ensure we get enough matches)
    fetch_limit = limit * 50 if start_date_max_yesterday else limit
    
    # Get markets - SDK returns PaginationPayload object
    # Try using start_date_max parameter if filtering by date
    try:
        if start_date_max_yesterday:
            # Try with start_date_max parameter
            response = client.get_markets(
                limit=fetch_limit,
                start_date_max=yesterday_max,
                closed=False
            )
        else:
            response = client.get_markets(limit=fetch_limit, closed=False)
    except TypeError:
        try:
            if start_date_max_yesterday:
                # Try with just start_date_max
                response = client.get_markets(
                    limit=fetch_limit,
                    start_date_max=yesterday_max
                )
            else:
                response = client.get_markets(limit=fetch_limit)
        except TypeError:
            # If date parameters not supported, fetch all and filter client-side
            try:
                response = client.get_markets(limit=fetch_limit)
            except TypeError:
                response = client.get_markets()
    
    # Extract the actual markets list from the pagination response
    # PaginationPayload has: limit, count, data (array of markets)
    if hasattr(response, 'data'):
        markets = response.data
    elif isinstance(response, dict) and 'data' in response:
        markets = response['data']
    elif isinstance(response, list):
        markets = response
    else:
        # Debug: print what we got
        print(f"DEBUG: Unexpected response type: {type(response)}")
        print(f"DEBUG: Response attributes: {dir(response)}")
        markets = []
    
    # Filter by start date max (yesterday) if requested
    if start_date_max_yesterday and markets:
        filtered_markets = []
        for market in markets:
            # Check various start date fields
            start_date_iso = (
                market.get("start_date_iso") or 
                market.get("game_start_time") or 
                market.get("start_date") or
                ""
            )
            if start_date_iso:
                # Parse date from ISO format (e.g., "2023-03-15T00:00:00Z")
                try:
                    # Handle both "Z" suffix and timezone-aware formats
                    date_str = start_date_iso.replace("Z", "+00:00") if start_date_iso.endswith("Z") else start_date_iso
                    market_date = datetime.fromisoformat(date_str).date()
                    # Include markets with start date <= yesterday
                    if market_date <= yesterday:
                        filtered_markets.append(market)
                except (ValueError, AttributeError):
                    # Try parsing just the date part (YYYY-MM-DD)
                    if start_date_iso.startswith(yesterday_str) or start_date_iso < yesterday_str:
                        filtered_markets.append(market)
        
        if filtered_markets:
            markets = filtered_markets
        else:
            # No matches found
            print(f"Note: No markets found with start date max {yesterday_str}.")
            print(f"Searched through {len(markets)} markets.")
            return []
    
    # Return limited results
    return markets[:limit] if markets else []


def print_market_summary(market: Dict[str, Any]) -> None:
    """Print a formatted summary of a market."""
    # Extract market ID (condition_id is the primary identifier)
    market_id = market.get("condition_id") or market.get("id") or market.get("market_id") or "unknown"
    
    # Extract question
    question = market.get("question") or market.get("title") or market.get("description", "N/A")
    
    # Extract prices from tokens array
    # Tokens contain outcome and price information
    tokens = market.get("tokens", [])
    yes_price = 0.5
    no_price = 0.5
    
    if tokens:
        # For binary markets, typically first token is one outcome, second is the other
        # Prices are normalized (should sum to ~1.0 for active markets)
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
    
    # Start date and end date
    start_date = (
        market.get("start_date_iso") or 
        market.get("game_start_time") or 
        market.get("start_date") or
        "N/A"
    )
    end_date = market.get("end_date_iso", "N/A")
    
    print(f"\n{'='*60}")
    print(f"Market ID: {market_id}")
    print(f"Status: {status}")
    print(f"Start Date: {start_date}")
    print(f"End Date: {end_date}")
    print(f"Question: {question}")
    if tokens:
        print(f"Outcome 1 ({tokens[0].get('outcome', 'YES')}): {yes_price:.4f}")
        if len(tokens) >= 2:
            print(f"Outcome 2 ({tokens[1].get('outcome', 'NO')}): {no_price:.4f}")
    else:
        print(f"YES Price: {yes_price:.4f}")
        print(f"NO Price:  {no_price:.4f}")
    print(f"{'='*60}")


def main():
    """Main test function."""
    yesterday = (datetime.now() - timedelta(days=1)).date()
    print(f"Fetching 5 markets with start date max yesterday ({yesterday})...")
    print("=" * 60)
    
    try:
        markets = get_markets(limit=5, start_date_max_yesterday=True)
        
        if not markets:
            print("\nNo markets returned.")
            return
        
        print(f"\nFound {len(markets)} markets:\n")
        
        for i, market in enumerate(markets, 1):
            print(f"\n--- Market {i} ---")
            print_market_summary(market)
        
        # Save raw JSON for inspection
        output_file = Path("scripts/markets_sample.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w") as f:
            json.dump(markets, f, indent=2)
        
        print(f"\n\nRaw JSON saved to: {output_file}")
        print("Inspect this file to see the exact API response structure.")
        
    except Exception as e:
        print(f"\nError fetching markets: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
