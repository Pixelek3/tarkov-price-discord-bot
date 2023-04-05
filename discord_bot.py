# -*- coding:utf-8 -*-

import cv2
import easyocr
import numpy as np
import re
import requests
from discord.ext import commands
import discord
from Levenshtein import distance
import datetime
import time
from paddleocr import PaddleOCR,draw_ocr
import json

items = {}
# Create a hash map to store the items
item_map = {}


query =   """
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
    
with open('data.json', 'r') as fp:
    if fp:
        print(fp)
        item_map = json.load(fp)
            
                
response = requests.post('https://api.tarkov.dev/graphql', json={'query': query })
if response.status_code == 200:
    data = response.json()
    print(len(item_map))
    has_map = len(item_map) > 0
    print(has_map)
    for item in data["data"]["items"]:
        if not has_map:
            # Add the item to the hash map using the lowercase short name as the key
            item_map[item["shortName"].lower()] = item["id"]
        items[item["id"]] = item
    if not has_map:
        with open('data.json', 'w') as fp:
            json.dump(item_map, fp, sort_keys=True, indent=4)

else:
    raise Exception("Query failed to run by returning code of {}. {}".format(response.status_code, query))


import threading

def update(): 
    response = requests.post('https://api.tarkov.dev/graphql', json={'query': query })
    if response.status_code == 200:
        data = response.json()
        for item in data["data"]["items"]:
            items[item["id"]] = item
        print("ITEMS UPDATED")
        with open('data.json', 'w') as fp:
            json.dump(item_map, fp, sort_keys=True, indent=4)
    else:
        print("ITEMS UPDATED FAILED")
    t = threading.Timer(1800, update ,args=[])
    t.start()


t = threading.Timer(1800, update ,args=[])
t.start()



def findItemMatch(name):
    output = None
    
    # Try to find an exact match in the hash map
    output = item_map.get(name.lower())

    if not output:
        for item_name in item_map.keys():
            if distance(name.lower(), item_name) == 1:
                output = item_map[item_name]
                item_map[name.lower()] = output
                break   
    if not output:
        for item_name in item_map.keys():
            if distance(name.lower(), item_name) == 2 and len(name) > 4:
                output = item_map[item_name]
                item_map[name.lower()] = output
                break
    return output

def findItem(name):

    # Try to find an exact match in the hash map
    output = item_map.get(name.lower())

    if not output:
        for item_name in item_map.keys():
            if distance(name.lower(), item_name) == 1:
                output = item_map[item_name]
                item_map[name.lower()] = output
                break
    if not output:
        for item_name in item_map.keys():
            if distance(name.lower(), item_name) == 2 and len(name) > 4:
                output = item_map[item_name]
                item_map[name.lower()] = output
                break

    return output

def GetPrice(prices):
  for x in prices:
    if x["source"] == "fleaMarket":
      return x["price"]
  return 0



ocr = PaddleOCR(lang='en', det_limit_side_len=1280) 

reader = easyocr.Reader(['en']) # this needs to run only once to load the model into memory

channel_id = 0 #YOUR CHANNEL ID

def apply_brightness_contrast(input_img, brightness = 0, contrast = 0):
    
    if brightness != 0:
        if brightness > 0:
            shadow = brightness
            highlight = 255
        else:
            shadow = 0
            highlight = 255 + brightness
        alpha_b = (highlight - shadow)/255
        gamma_b = shadow
        
        buf = cv2.addWeighted(input_img, alpha_b, input_img, 0, gamma_b)
    else:
        buf = input_img.copy()
    
    if contrast != 0:
        f = 131*(contrast + 127)/(127*(131-contrast))
        alpha_c = f
        gamma_c = 127*(1-f)
        
        buf = cv2.addWeighted(buf, alpha_c, buf, 0, gamma_c)

    return buf


bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    print("Bot gotowy do dzialania")
    activity = discord.Game(name="Checking...", type=3)
    await bot.change_presence(status=discord.Status.idle, activity=activity)

@bot.command()
async def c(ctx):
  if ctx.channel.id == channel_id or ctx.channel.id == channel_id2:
    if ctx.message.attachments:
        st = datetime.datetime.now()
        timemsg = await ctx.send("Calculate...")
        resp = requests.get(ctx.message.attachments[0].url, stream=True).raw
        image = np.asarray(bytearray(resp.read()), dtype="uint8")
        originalImage = cv2.imdecode(image, cv2.IMREAD_COLOR)
        originalImage = cv2.resize(originalImage, None,fx=2 ,fy=2,interpolation=cv2.INTER_LANCZOS4  )

        grayImage = cv2.cvtColor(originalImage, cv2.COLOR_BGR2GRAY)

        kernel = np.ones((1,1), np.uint8)
        img = cv2.dilate(grayImage, kernel, iterations=1)
        img = cv2.erode(img, kernel, iterations=1)



      #  img = cv2.threshold(cv2.medianBlur(img, 1), 10, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        img = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel)


        #img = cv2.threshold(cv2.medianBlur(img, 3), 110, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

        # img = cv2.bitwise_not(img)


        img = apply_brightness_contrast(img, 0, 30)

        normal_res = reader.readtext(img, detail = 1 , blocklist ="[]{}|;@:~", link_threshold  = 1.0)

        test = []
        for x in normal_res:
            if x[2] > 0.15:
                test.append(x[1])

        mainresult = test
        mainresult = sorted(set(mainresult), key=lambda x:mainresult.index(x))


       
        embed = discord.Embed(
            title = "Tarkov Price Checker",
            description= "Allows you to almost quickly check the value of your inventory",
            colour= discord.Colour.blue()
        )

        for name in mainresult:
            names = name.split()
            if len(names) > 1:
                if not findItemMatch(name):
                    for new in names:
                        mainresult.append(new)

        for name in mainresult:
          name = name.replace("/", "").replace("_", " ")
          if not name.isdigit():
            if len(name) >= 2:
                info = findItem(name)
                print(name)
                if info:
                  result = items[info]
                  if result["changeLast48hPercent"] >= 0:
                    tempvalue = "```ansi\n %s₽ \u001b[0;32m(%s)\n```" % (GetPrice(result["sellFor"]), str(result["changeLast48hPercent"]) + "%")
                  else:
                    tempvalue = "```ansi\n %s₽ \u001b[0;31m(%s)\n```" % (GetPrice(result["sellFor"]), str(result["changeLast48hPercent"]) + "%")
                  embed.add_field(name=result["name"], value=tempvalue)
        await timemsg.delete()
        et = datetime.datetime.now()
        elapsed_time = et - st
        embed.set_footer(text="API: tarkov.dev \nOperation time: %s" % str(round(elapsed_time.total_seconds(), 2)) + " s")
        await ctx.send(embed=embed)
    else:   
        await ctx.send("You need to add photo")


@bot.command()
async def c2(ctx):
  if ctx.channel.id == channel_id:
    if ctx.message.attachments:
        st = datetime.datetime.now()
        timemsg = await ctx.send("Calculate...")
        resp = requests.get(ctx.message.attachments[0].url, stream=True).raw
        image = np.asarray(bytearray(resp.read()), dtype="uint8")
        originalImage = cv2.imdecode(image, cv2.IMREAD_COLOR)
        originalImage = cv2.resize(originalImage, None,fx=2 ,fy=2,interpolation=cv2.INTER_LANCZOS4  )

        # grayImage = cv2.cvtColor(originalImage, cv2.COLOR_BGR2GRAY)

        kernel = np.ones((1,1), np.uint8)
        img = cv2.dilate(originalImage, kernel, iterations=1)
        img = cv2.erode(img, kernel, iterations=1)



      #  img = cv2.threshold(cv2.medianBlur(img, 1), 10, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

       

        #img = cv2.threshold(cv2.medianBlur(img, 3), 110, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

        # img = cv2.bitwise_not(img)


        img = apply_brightness_contrast(img, 35, 80)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        img = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel)

        test = []
        result = ocr.ocr(img, cls=False)
        for idx in range(len(result)):
            res = result[idx]
            for line in res:
                if line[1][1] > 0.7:
                    test.append(line[1][0])

    
        mainresult = test
        mainresult = sorted(set(mainresult), key=lambda x:mainresult.index(x))


        embed = discord.Embed(
            title = "Tarkov Price Checker",
            description= "Allows you to almost quickly check the value of your inventory",
            colour= discord.Colour.blue()
        )

        for name in mainresult:
            names = name.split()
            if len(names) > 1:
                if not findItemMatch(name):
                    for new in names:
                        mainresult.append(new)
        test_list = []
        for name in mainresult:
          name = name.replace("/", "").replace("_", " ")
          if not name.isdigit():
           if len(name) >= 2:
                info = findItem(name)
                print(name)
                if info and not info in test_list:
                  test_list.append(info)
                  result = items[info]
                  if result["changeLast48hPercent"] >= 0:
                    tempvalue = "```ansi\n %s₽ \u001b[0;32m(%s)\n```" % (GetPrice(result["sellFor"]), str(result["changeLast48hPercent"]) + "%")
                  else:
                    tempvalue = "```ansi\n %s₽ \u001b[0;31m(%s)\n```" % (GetPrice(result["sellFor"]), str(result["changeLast48hPercent"]) + "%")
                  embed.add_field(name=result["name"], value=tempvalue)
        await timemsg.delete()
        del test_list
        et = datetime.datetime.now()
        elapsed_time = et - st
        embed.set_footer(text="API: tarkov.dev \Operation Time: %s" % str(round(elapsed_time.total_seconds(), 2)) + " s")
        await ctx.send(embed=embed)
    else:   
        await ctx.send("You need to add photo")        
        
bot.run("") #Bot Token