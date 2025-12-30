# -*- coding:utf-8 -*-
import discord
from discord.ext import commands, tasks
import numpy as np
import cv2
import aiohttp
import asyncio
from paddleocr import PaddleOCR
from Levenshtein import distance
import json
import datetime
import io
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# CONFIGURATION
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("ERROR: Token not found in .env file!")
    exit()

CHANNEL_ID = 0  # 0 = works everywhere, or set specific ID
API_URL = 'https://api.tarkov.dev/graphql'

# Initialize PaddleOCR
ocr = PaddleOCR(use_textline_orientation=False, lang='en')

# GraphQL Query
QUERY = """
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

class TarkovBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        self.item_map = {}   # Map: name -> item data
        self.item_names = [] # List of names for searching

    async def setup_hook(self):
        self.update_prices.start()

    @tasks.loop(minutes=30)
    async def update_prices(self):
        """Fetches prices from the API every 30 minutes."""
        print(f"[{datetime.datetime.now()}] Updating prices...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, json={'query': QUERY}) as response:
                    if response.status == 200:
                        data = await response.json()
                        new_map = {}
                        new_names = []
                        
                        for item in data['data']['items']:
                            key_name = item['name'].lower()
                            key_short = item['shortName'].lower()
                            
                            new_map[key_name] = item
                            new_map[key_short] = item
                            
                            new_names.append(key_name)
                            new_names.append(key_short)
                        
                        self.item_map = new_map
                        self.item_names = list(set(new_names))
                        print(f"Loaded {len(self.item_map)} items.")
                        
                        # Emergency backup
                        with open('data.json', 'w') as fp:
                            json.dump(self.item_map, fp, indent=4)
                    else:
                        print(f"API Error: {response.status}")
        except Exception as e:
            print(f"Error occurred during update: {e}")

    @update_prices.before_loop
    async def before_update_prices(self):
        await self.wait_until_ready()

bot = TarkovBot()

def get_best_match(text, item_map, threshold=3):
    """Searches for an item by Name and ShortName."""
    clean_text = text.lower().strip().replace('.', '') 
    original_text_lower = text.lower().strip()
    
    # Fast lookup (O(1))
    if clean_text in item_map:
        return item_map[clean_text]
    if original_text_lower in item_map:
        return item_map[original_text_lower]
    
    if len(clean_text) < 2: return None

    # Fallback: Check ShortName manually
    for item in item_map.values():
        item_short = item['shortName'].lower().replace('.', '')
        if item_short == clean_text:
            return item

    # Fuzzy Search (Levenshtein)
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

def get_flea_price(item_data):
    """Extracts the Flea Market price."""
    prices = item_data.get("sellFor", [])
    for p in prices:
        if p["source"] == "fleaMarket":
            return p["price"]
    # If not on Flea, return highest trader price
    if prices:
        return max(p["price"] for p in prices)
    return 0

def extract_text_smart(data):
    """Helper function to extract text from nested structures."""
    found = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            found.extend(extract_text_smart(value))
            
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                if isinstance(item[1], (list, tuple)) and len(item[1]) >= 1:
                    found.append(item[1][0])
                elif isinstance(item[1], str):
                    found.append(item[1])
            else:
                found.extend(extract_text_smart(item))
                
    elif isinstance(data, str):
        if len(data) > 2:
            pass 

    return found

def process_image_ocr(image_bytes):
    image = np.asarray(bytearray(image_bytes), dtype="uint8")
    img = cv2.imdecode(image, cv2.IMREAD_COLOR)
    
    if img is None:
        return []

    # Upscaling 2x
    try:
        img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    except Exception:
        pass

    try:
        result = ocr.ocr(img)
    except Exception as e:
        print(f"OCR engine error: {e}")
        return []

    detected_texts = []

    try:
        if isinstance(result, list) and len(result) > 0:
            data = result[0]
            
            if isinstance(data, dict) and 'rec_texts' in data:
                texts = data['rec_texts']
                scores = data.get('rec_scores', [])
                
                for i, text in enumerate(texts):
                    score = scores[i] if i < len(scores) else 0.0
                    
                    if score > 0.5 and len(text) > 2:
                        detected_texts.append(text)
            
            # Fallback method
            else:
                print("Missing 'rec_texts' key, attempting fallback method...")
                detected_texts = extract_text_recursive_fallback(result)

    except Exception as e:
        print(f"Error extracting text: {e}")
        return []

    return list(set(detected_texts))

def extract_text_recursive_fallback(data):
    found = []
    if isinstance(data, list):
        for item in data:
            found.extend(extract_text_recursive_fallback(item))
    elif isinstance(data, dict):
        for val in data.values():
            found.extend(extract_text_recursive_fallback(val))
    elif isinstance(data, str) and len(data) > 2:
        found.append(data)
    return found

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.change_presence(activity=discord.Game(name="Checking Flea prices"))

@bot.command()
async def c(ctx):
    """Command to check prices from an image."""
    if CHANNEL_ID != 0 and ctx.channel.id != CHANNEL_ID:
        return

    if not ctx.message.attachments:
        await ctx.send("Please attach an inventory image!")
        return

    status_msg = await ctx.send("🔍 Analyzing image...")
    start_time = datetime.datetime.now()

    try:
        attachment = ctx.message.attachments[0]
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                if resp.status != 200:
                    await status_msg.edit(content="❌ Error downloading image.")
                    return
                image_bytes = await resp.read()

        loop = asyncio.get_running_loop()
        detected_texts = await loop.run_in_executor(None, process_image_ocr, image_bytes)

        if not detected_texts:
            await status_msg.edit(content="❌ No text detected on the image.")
            return

        found_items = []
        processed_names = set()

        for text in detected_texts:
            if len(text) < 3 or text.isdigit(): continue
            
            match = get_best_match(text, bot.item_map)
            
            if match and match['id'] not in processed_names:
                processed_names.add(match['id'])
                found_items.append(match)

        if not found_items:
            await status_msg.edit(content=f"Read text: *{', '.join(detected_texts[:5])}...*\nBut no items matched.")
            return

        embed = discord.Embed(
            title="Tarkov Price Check",
            color=discord.Color.dark_green(),
            timestamp=datetime.datetime.now()
        )

        for item in found_items[:24]:
            price = get_flea_price(item)
            avg_price = item.get("avg24hPrice", 0) or 0
            
            change = item.get("changeLast48hPercent")
            
            if change is None and avg_price > 0 and price > 0:
                try:
                    change = ((price - avg_price) / avg_price) * 100
                except ZeroDivisionError:
                    change = 0
            
            if change is None:
                change = 0

            color_code = "32" if change >= 0 else "31" # Green / Red
            sign = "+" if change > 0 else ""
            
            val_str = f"```ansi\n{price:,} ₽ \u001b[0;{color_code}m({sign}{change:.1f}%)\u001b[0m\n```"
            
            embed.add_field(name=item['name'], value=val_str, inline=True)

        elapsed = (datetime.datetime.now() - start_time).total_seconds()
        embed.set_footer(text=f"Processed in {elapsed:.2f}s | API: tarkov.dev")
        
        await status_msg.delete()
        await ctx.send(embed=embed)

    except Exception as e:
        print(f"Error in !c command: {e}")
        await status_msg.edit(content="❌ Critical error during processing.")

bot.run(TOKEN)