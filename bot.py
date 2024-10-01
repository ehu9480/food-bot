import discord
import requests
import time
import pytz
import os
from datetime import datetime
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = 1071187673676529876
#CHANNEL_ID = 1204200927536488508 #TEST
dic = {1:'1️⃣', 2:'2️⃣', 3:'3️⃣', 4:'4️⃣', 5:'5️⃣', 6:'6️⃣', 7: '7️⃣'}

bot = commands.Bot(command_prefix="!", intents = discord.Intents.all())
scheduler = AsyncIOScheduler()


def fetch_dining_data():
    URL = "https://now.dining.cornell.edu/api/1.0/dining/eateries.json"
    response = requests.get(URL)
    if response.status_code == 200:
        data = response.json()
        eateries_data = data['data']['eateries']
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        dining_halls = [
            'Becker House Dining Room',
            'Cook House Dining Room',
            "Jansen's Dining Room at Bethe House",
            'Keeton House Dining Room',
            'Rose House Dining Room'
        ]
        
        categories = ['Grill', "Chef's Table", "Specialty Station",'Special']
        key_words = ['Dumpling',"Beef","Chicken","Pork","Pizza","Pasta",
                     'Mango Lassi', 'Curry', 'Fried', 'Smoothie', 'Ravioli',
                     'Quesadilla','Onion Ring',"Bread","Potato","Ham","Ramen",
                     'Guacamole','Cheese']
        
        fin = []
        hall_index = 1 # Start index for numbering
        
        for hall_name in dining_halls:
            for eatery in eateries_data:
                if eatery['name'] == hall_name:
                    for operating_hour in eatery.get('operatingHours', []):
                        if operating_hour['date'] == current_date:
                            dinner_events = [event for event in operating_hour.get('events', []) if event['descr'] == 'Dinner']
                            for event in dinner_events:
                                str_build = f"**{hall_index}: {hall_name.split(' ')[0]}:** "  # Add index and simplify names for output
                                
                                items_added = set()  # Track added items to avoid duplicates
                                for menu in event.get('menu', []):
                                    if menu['category'] in categories:
                                        for item in menu.get('items', []):
                                            if item['item'] not in items_added:
                                                if any(word in item['item'] for word in key_words):
                                                    str_build += item['item'] + ", "
                                                    items_added.add(item['item'])
                                if items_added:  # If any items were added, append the result
                                    fin.append(str_build.rstrip(', '))
                                    hall_index += 1  # Increment index for next hall
                            break  # Only consider the first matching 'Dinner' event

        return ("\n".join(f"{menu}" for index, menu in enumerate(fin)), hall_index)
    else:
        print("Failed to fetch data")

async def send_daily_message():
    today = datetime.now(pytz.timezone('US/Eastern')).weekday()  # Monday is 0, Sunday is 6
    channel = bot.get_channel(CHANNEL_ID)
    
    if today == 2:  # Checks if today is Wednesday (where Monday is 0)
        message = "Keeton House Dinner at 6!"
        emojis = ['👍']  # List of emojis you want to react with
    else:
        message, hall_count = fetch_dining_data() 
        message += f"\n**{hall_count}: Collegetown**"
        emojis = []
        for i in range(1, hall_count+1):
            emojis.append(dic[i])
        emojis += ['🕕', '🕡', '🕖']  # List of emojis you want to react with
    
    sent_message = await channel.send(message)
    for emoji in emojis:
        await sent_message.add_reaction(emoji)

    await bot.close()
    
@bot.event
async def on_ready():
    scheduler.add_job(send_daily_message)
    scheduler.start()
  
bot.run(BOT_TOKEN)
