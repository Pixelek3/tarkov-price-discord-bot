from Levenshtein import distance
from typing import Optional, Dict, Any

def get_best_match(text: str, item_map: Dict[str, Any], threshold: int = 3) -> Optional[Dict[str, Any]]:
    if not text:
        return None
        
    clean_text = text.lower().strip().replace('.', '')
    original_text_lower = text.lower().strip()

    if clean_text in item_map:
        return item_map[clean_text]
    if original_text_lower in item_map:
        return item_map[original_text_lower]

    if len(clean_text) < 2:
        return None

    for item in item_map.values():
        item_short = item['shortName'].lower().replace('.', '')
        if item_short == clean_text:
            return item

    best_item = None
    best_dist = 100

    for key in item_map.keys():
        if abs(len(key) - len(clean_text)) > threshold:
            continue

        dist = distance(clean_text, key)

        if dist == 0:
            return item_map[key]

        if dist < best_dist:
            best_dist = dist
            best_item = item_map[key]

    if best_dist <= threshold:
        return best_item

    return None