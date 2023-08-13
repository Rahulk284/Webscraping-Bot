from bs4 import BeautifulSoup
import requests
import re
import discord
import sqlite3

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

# Web scraper function
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

# Discord bot event handlers
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
            
            # Retrieve last lowest price from the database
            cursor.execute('SELECT lowest_price FROM lowest_prices WHERE search_term = ?', (search_term,))
            result = cursor.fetchone()
            if result:
                last_lowest_price = result[0]
                priceDifference = items[0][1]['price'] - last_lowest_price
                percentChange = (priceDifference / last_lowest_price) * 100
                response += f"\n\nLast lowest price: ${last_lowest_price}"
                if (priceDifference < 0):
                    absolutePriceDifference = abs(priceDifference)
                    response += f"\nThere is a -${absolutePriceDifference} price change for the cheapest option since the last time it was searched"
                elif (priceDifference > 0):
                    response += f"\nThere is a +${priceDifference} price change for the cheapest option since the last time it was searched"
                else:
                    response += f"\nThere wasn't a price change for the cheapest option since the last time it was searched"
            
            # Update lowest price in the database if necessary
            lowest_price = items[0][1]['price']
            cursor.execute('INSERT OR REPLACE INTO lowest_prices (search_term, lowest_price) VALUES (?, ?)', (search_term, lowest_price))
            conn.commit()
            
            await message.channel.send(response)

client.run("MTEzODk1MDQ2NjY1NTQ5ODMxMg.GRMOkp.-I38Xxw7LYkistfLt9RG2dq-K89uZ7qgQRDaUM")

# Close the database connection
cursor.close()
conn.close()


