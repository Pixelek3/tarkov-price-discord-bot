import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import datetime
import logging
from typing import Dict, Any
import io

logger = logging.getLogger("TarkovBot.market")

from utils.api import API_URL, GRAPHQL_QUERY, get_flea_price
from utils.matching import get_best_match
from utils.ocr import process_image_ocr

class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.item_map: Dict[str, Any] = {}
        self.update_prices.start()

    def cog_unload(self):
        self.update_prices.cancel()

    @tasks.loop(minutes=30)
    async def update_prices(self):
        logger.info("Updating prices from API...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, json={'query': GRAPHQL_QUERY}) as response:
                    if response.status == 200:
                        data = await response.json()
                        new_map = {}
                        
                        items = data.get('data', {}).get('items', [])
                        for item in items:
                            key_name = item['name'].lower()
                            key_short = item['shortName'].lower()
                            
                            new_map[key_name] = item
                            new_map[key_short] = item
                        
                        self.item_map = new_map
                        logger.info(f"Successfully updated {len(items)} items.")
                    else:
                        logger.error(f"API Error: {response.status}")
        except Exception as e:
            logger.exception(f"Update loop error: {e}")

    @update_prices.before_loop
    async def before_update_prices(self):
        await self.bot.wait_until_ready()

    @commands.command(name="c")
    async def check_price(self, ctx):
        if not ctx.message.attachments:
            await ctx.send("Please attach an inventory image!")
            return

        status_msg = await ctx.send("🔍 Analyzing image...")
        start_time = datetime.datetime.now()
        
        logger.info(f"User {ctx.author} requested price check.")

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
                logger.warning("OCR detected no text on the image.")
                await status_msg.edit(content="❌ No text detected.")
                return

            found_items = []
            processed_ids = set()

            for text in detected_texts:
                if len(text) < 3 or text.isdigit(): continue
                
                match = get_best_match(text, self.item_map)
                
                if match and match['id'] not in processed_ids:
                    processed_ids.add(match['id'])
                    found_items.append(match)

            if not found_items:
                await status_msg.edit(content=f"Text found: {', '.join(detected_texts[:3])}...\nBut no items matched.")
                return

            # Budowanie Embed
            embed = discord.Embed(
                title="Tarkov Price Check",
                color=discord.Color.dark_green(),
                timestamp=datetime.datetime.now()
            )

            for item in found_items[:24]:
                price = get_flea_price(item)
                avg_price = item.get("avg24hPrice") or 0
                
                change = 0.0
                if avg_price and avg_price > 0:
                    change = ((price - avg_price) / avg_price) * 100

                color_code = "32" if change >= 0 else "31"
                sign = "+" if change > 0 else ""
                
                val_str = f"```ansi\n{price:,} ₽ \u001b[0;{color_code}m({sign}{change:.1f}%)\u001b[0m\n```"
                embed.add_field(name=item['name'], value=val_str, inline=True)

            elapsed = (datetime.datetime.now() - start_time).total_seconds()
            embed.set_footer(text=f"Processed in {elapsed:.2f}s | API: tarkov.dev")
            
            await status_msg.delete()
            await ctx.send(embed=embed)
            logger.info(f"Processed image in {(datetime.datetime.now() - start_time).total_seconds():.2f}s")

        except Exception as e:
            logger.exception(f"Critical error in command !c")
            await status_msg.edit(content="❌ Critical error.")

async def setup(bot):
    await bot.add_cog(Market(bot))