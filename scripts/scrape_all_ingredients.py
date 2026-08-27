import os
import sys
import re
import urllib.parse
import time
import requests
from bs4 import BeautifulSoup

# Add parent directory to sys.path to import db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import get_conn, save_dish_ingredients
import suggestions

def clean_ingredient(line):
    # Strip leading dash and whitespace
    line = line.strip().lstrip("-").strip()
    
    # 1. Look for text in parentheses
    match = re.search(r'\(([^)]+)\)', line)
    if match:
        name = match.group(1).strip()
    else:
        # Remove numbers and fraction characters
        name = re.sub(r'[\d&/½¼¾\s\-]+', ' ', line)
        # Remove common units and adjectives
        name = re.sub(r'\b(tsp|tbsp|tbs|cup|cups|g|kg|pinch|pinches|piece|pieces|clove|cloves|inch|packet|packets|bottle|can|to taste|taste|halved|whisked|cut|chopped|sliced|grated|powder|paste|oil|water|salt|as required|for smoke|smoke)\b', '', name, flags=re.IGNORECASE)
        name = name.strip()
    
    # Clean up multiple spaces
    name = re.sub(r'\s+', ' ', name)
    return name.lower().strip()

def search_food_fusion(dish_name):
    query = urllib.parse.quote_plus(dish_name + " Food Fusion")
    url = f"https://foodfusion.com/?s={query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        links = []
        for link in soup.select("article h2 a, .entry-title a, a"):
            href = link.get("href")
            if href and "/recipe/" in href:
                links.append(href)
        return links[0] if links else None
    except Exception as e:
        print(f"Error searching for {dish_name}: {e}")
        return None

def extract_ingredients(recipe_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get(recipe_url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        detail_div = soup.select_one("div.english-detail-ff")
        if not detail_div:
            return None
            
        paragraphs = [p.text.strip() for p in detail_div.find_all("p") if p.text.strip()]
        
        ingredients = []
        in_ingredients_section = False
        
        for p in paragraphs:
            if "ingredients:" in p.lower():
                in_ingredients_section = True
                continue
            if "directions:" in p.lower() or "method:" in p.lower():
                in_ingredients_section = False
                break
                
            if in_ingredients_section:
                # If paragraph looks like an ingredient line (starts with - or contains units)
                if p.startswith("-") or any(word in p.lower() for word in ["tsp", "tbsp", "cup", "g", "kg", "pinch", "salt", "oil"]):
                    clean = clean_ingredient(p)
                    if clean and len(clean) > 1 and clean != "-":
                        ingredients.append(clean)
                        
        if not ingredients:
            # Fallback: scan any paragraph starting with - in the whole div
            for p in paragraphs:
                if p.startswith("-"):
                    clean = clean_ingredient(p)
                    if clean and len(clean) > 1 and clean != "-":
                        ingredients.append(clean)
                        
        return ingredients
    except Exception as e:
        print(f"Error parsing recipe {recipe_url}: {e}")
        return None

def scrape_all():
    # Load all dishes from CSV
    inventory = suggestions._load_dishes()
    dish_names = sorted(list({d["name"] for d in inventory}))
    
    print(f"Starting crawl for {len(dish_names)} dishes...")
    
    for i, name in enumerate(dish_names):
        print(f"[{i+1}/{len(dish_names)}] Processing: {name}")
        
        # Check if already in DB
        conn = get_conn()
        row = conn.execute("SELECT dish_name FROM dish_ingredients WHERE LOWER(dish_name) = LOWER(?)", (name,)).fetchone()
        conn.close()
        
        if row:
            print(f"  -> Already in database. Skipping.")
            continue
            
        url = search_food_fusion(name)
        if url:
            print(f"  -> Found recipe URL: {url}")
            ingredients = extract_ingredients(url)
            if ingredients:
                ingredients_str = ", ".join(ingredients)
                save_dish_ingredients(name, ingredients_str, raw_ingredients=url)
                print(f"  -> Saved {len(ingredients)} ingredients: {ingredients_str[:80]}...")
            else:
                print("  -> Could not extract ingredients from page.")
        else:
            print("  -> No Food Fusion recipe link found.")
            
        # Polite delay to avoid hammering the server
        time.sleep(1.0)

if __name__ == "__main__":
    scrape_all()
