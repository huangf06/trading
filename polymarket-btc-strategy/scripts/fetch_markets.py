import requests
import json

def fetch_btc_markets():
    url = "https://gamma-api.polymarket.com/events"
    params = {
        "limit": 50,
        "active": "true",
        "closed": "false",
        "order": "volume_24h",
        "ascending": "false",
        "tag_id": "1" # Assuming tag_id 1 is crypto or searching text
    }
    
    # Alternatively, just search? Gamma API docs are sparse, let's try a broad fetch and filter.
    # The search result mentioned /events
    
    try:
        response = requests.get(url, params={"limit": 100})
        response.raise_for_status()
        events = response.json()
        
        btc_markets = []
        for event in events:
            if "Bitcoin" in event.get("title", "") or "BTC" in event.get("title", ""):
                btc_markets.append(event)
        
        print(f"Found {len(btc_markets)} BTC-related events.")
        
        # Save to file for inspection
        with open("data/btc_markets.json", "w") as f:
            json.dump(btc_markets, f, indent=2)
            
        # Print the first few titles
        for event in btc_markets[:5]:
            print(f"- {event['title']} (ID: {event['id']})")
            
    except Exception as e:
        print(f"Error fetching markets: {e}")

if __name__ == "__main__":
    fetch_btc_markets()
