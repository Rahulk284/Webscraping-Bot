from bs4 import BeautifulSoup
import requests
import re
import discord
import sqlite3
from dotenv import load_dotenv
from tokens import DISCORD_TOKEN, OPENAI_API_KEY
import os
import openai
from keepalive import keep_alive


openai.api_key = OPENAI_API_KEY

intents = discord.Intents.all()
client = discord.Client(intents=intents)

conn = sqlite3.connect('prices.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS lowest_prices (
        search_term TEXT PRIMARY KEY,
        lowest_price INTEGER
    )
''')

conn.commit()

def scrape_newegg(search_term):
    items_found = {}
    url = f"https://www.newegg.com/p/pl?d={search_term}&N=4131"
    page = requests.get(url).text
    doc = BeautifulSoup(page, "html.parser")

    page_text = doc.find(class_="list-tool-pagination-text").strong
    pages = int(str(page_text).split("/")[-2].split(">")[-1][:-1])

    for page in range(1, pages + 1):
        url = f"https://www.newegg.com/p/pl?d={search_term}&N=4131&page={page}"
        page = requests.get(url).text
        doc = BeautifulSoup(page, "html.parser")

        div = doc.find(
            class_=
            "item-cells-wrap border-cells items-grid-view four-cells expulsion-one-cell"
        )
        items = div.find_all(string=re.compile(search_term))

        for item in items:
            parent = item.parent
            if parent.name != "a":
                continue

            link = parent['href']
            next_parent = item.find_parent(class_="item-container")
            try:
                price = next_parent.find(class_="price-current").find("strong").string
                items_found[item] = {"price": int(price.replace(",", "")), "link": link}
            except:
                pass

    sorted_items = sorted(items_found.items(), key=lambda x: x[1]['price'])
    return sorted_items[:3]

async def generate_openai(user_input):
    try:
        response = await openai.Completion.create(
            engine="davinci",
            prompt=user_input,
            max_tokens=50
        )
        return response.choices[0].text.strip()
    except Exception as e:
        print(e)
        return "An error occurred while generating a response."

@client.event
async def on_ready():
    print("Bot has logged in as {0.user}".format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if message.content.startswith("!search"):
        await message.channel.send("Finding the three cheapest options...")
        search_term = message.content[8:]
        items = scrape_newegg(search_term)
        
        if not items:
            await message.channel.send("No items found.")
        else:
            response = "\n\n".join([f"{item[0]}\n${item[1]['price']}\n{item[1]['link']}" for item in items])
            
            cursor.execute('SELECT lowest_price FROM lowest_prices WHERE search_term = ?', (search_term,))
            result = cursor.fetchone()
            if result:
                last_lowest_price = result[0]
                priceDifference = items[0][1]['price'] - last_lowest_price
                basePercentChange = (priceDifference / last_lowest_price) * 100
                percentChange = round(basePercentChange, 2)
                response += f"\n\nLast lowest price: ${last_lowest_price}"
                if (priceDifference < 0):
                    absolutePriceDifference = abs(priceDifference)
                    absolutePercentDifference = abs(percentChange)
                    response += f"\nThere is a -${absolutePriceDifference}(-{absolutePercentDifference}%) price change for the cheapest option since the last time it was searched"
                elif (priceDifference > 0):
                    response += f"\nThere is a +${priceDifference}(+{percentChange}%) price change for the cheapest option since the last time it was searched"
                else:
                    response += f"\nThere wasn't a price change for the cheapest option since the last time it was searched"
            
            lowest_price = items[0][1]['price']
            cursor.execute('INSERT OR REPLACE INTO lowest_prices (search_term, lowest_price) VALUES (?, ?)', (search_term, lowest_price))
            conn.commit()
            
            await message.channel.send(response)
    if message.content.startswith("!ask_bot"):
        user_input = message.content[9:]
        openai_response = await generate_openai(user_input)
        await message.channel.send(openai_response)

keep_alive()

client.run(DISCORD_TOKEN)

cursor.close()
conn.close()


