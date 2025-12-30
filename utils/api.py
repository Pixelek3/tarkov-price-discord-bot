from typing import Dict, Any, List

API_URL = 'https://api.tarkov.dev/graphql'

GRAPHQL_QUERY = """
{
    items {
        name
        shortName
        id
        avg24hPrice
        changeLast48hPercent
        basePrice
        sellFor {
            price
            source
        }
    }
}
"""

def get_flea_price(item_data: Dict[str, Any]) -> int:
    if not item_data:
        return 0

    prices = item_data.get("sellFor") or [] 
    
    for p in prices:
        if p.get("source") == "fleaMarket":
            return p.get("price", 0)

    if prices:
        valid_prices = [p.get("price", 0) for p in prices if "price" in p]
        if valid_prices:
            return max(valid_prices)
            
    return 0