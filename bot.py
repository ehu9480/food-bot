import discord
import requests
import time
import pytz
import os
from datetime import datetime, date
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = 1071187673676529876

dic = {1:'1️⃣', 2:'2️⃣', 3:'3️⃣', 4:'4️⃣', 5:'5️⃣', 6:'6️⃣', 7: '7️⃣'}

bot = commands.Bot(command_prefix="!", intents = discord.Intents.all())
scheduler = AsyncIOScheduler()

# Hard-coded date ranges (inclusive) for Spring 2025:
BOT_ON_RANGES = [
    (date(2025, 1, 21), date(2025, 2, 14)),  # Instruction
    (date(2025, 2, 19), date(2025, 3, 28)),  # Instruction
    (date(2025, 4, 7),  date(2025, 5, 6)),   # Instruction
    (date(2025, 5, 7),  date(2025, 5, 9)),   # Study Days
    (date(2025, 5, 10), date(2025, 5, 17)),  # Exams
]

def bot_should_run_today() -> bool:
    """Return True if today (Eastern time) is an 'on' day, otherwise False."""
    eastern = pytz.timezone('US/Eastern')
    today_date = datetime.now(eastern).date()
    
    for start, end in BOT_ON_RANGES:
        if start <= today_date <= end:
            return True
    return False

def fetch_dining_data():
    """
    Return a tuple (message, hall_count).
      - message: str with collected dinner items from certain categories
      - hall_count: how many halls actually had items
    """
    URL = "https://now.dining.cornell.edu/api/1.0/dining/eateries.json"
    response = requests.get(URL)
    if response.status_code != 200:
        print("Failed to fetch data")
        return ("", 0)
    
    data = response.json()
    eateries_data = data['data']['eateries']
    
    eastern = pytz.timezone('US/Eastern')
    current_date = datetime.now(eastern).strftime("%Y-%m-%d")
    
    dining_halls = [
        'Becker House Dining Room',
        'Cook House Dining Room',
        "Jansen's Dining Room at Bethe House",
        'Keeton House Dining Room',
        'Rose House Dining Room'
    ]
    
    # We only look for these categories:
    categories = ['Grill', "Chef's Table", "Specialty Station", 'Special']
    
    # We only keep items that contain at least one of these keywords:
    key_words = [
        'Dumpling', "Beef", "Chicken", "Pork", "Pizza", "Pasta",
        'Mango Lassi', 'Curry', 'Fried', 'Smoothie', 'Ravioli',
        'Quesadilla','Onion Ring', "Bread", "Potato", "Ham", "Ramen",
        'Guacamole', 'Grilled Cheese'
    ]
    
    fin = []
    # Start hall_index at 0 so if we find no items, it remains 0
    hall_index = 0
    
    for hall_name in dining_halls:
        for eatery in eateries_data:
            if eatery['name'] == hall_name:
                for operating_hour in eatery.get('operatingHours', []):
                    if operating_hour['date'] == current_date:
                        # Looking specifically for "Dinner" in the events:
                        dinner_events = [
                            event for event in operating_hour.get('events', [])
                            if event['descr'] == 'Dinner'
                        ]
                        for event in dinner_events:
                            str_build = f"**{hall_name.split(' ')[0]}:** "
                            
                            items_added = set()
                            for menu in event.get('menu', []):
                                # Only gather from the categories you care about
                                if menu['category'] in categories:
                                    for item in menu.get('items', []):
                                        # Avoid duplicates
                                        if item['item'] not in items_added:
                                            # If it has any of the keywords, append
                                            if any(word in item['item'] for word in key_words):
                                                str_build += item['item'] + ", "
                                                items_added.add(item['item'])
                            
                            if items_added:
                                # We found actual items for this hall
                                fin.append(str_build.rstrip(', '))
                                hall_index += 1
                        break
                break  # We found the matching hall, no need to check more
    
    return ("\n".join(fin), hall_index)

async def send_daily_message():
    # 1) Check if the bot is "on" for today's date:
    if not bot_should_run_today():
        print("Bot is OFF today (break or past exam period). Exiting.")
        await bot.close()
        return
    
    # 2) Fetch the dining info
    message, hall_count = fetch_dining_data()
    
    # If there's NO valid items for dinner (hall_count == 0), skip sending
    if hall_count == 0:
        print("No matching dinner items found; skipping message.")
        await bot.close()
        return
    
    # Otherwise, append a line for "Collegetown" at the end:
    message += f"\n**{hall_count}: Collegetown**"
    
    channel = bot.get_channel(CHANNEL_ID)
    sent_message = await channel.send(message)
    
    # Add numeric reactions for each hall (1..hall_count)
    for i in range(1, hall_count + 1):
        await sent_message.add_reaction(dic[i])
    # Also add some time emojis
    for e in ['🕕', '🕡', '🕖']:
        await sent_message.add_reaction(e)
    
    # Then close the bot (assuming you only want to run once a day)
    await bot.close()
    
@bot.event
async def on_ready():
    # Schedule the daily job
    scheduler.add_job(send_daily_message)
    scheduler.start()

bot.run(BOT_TOKEN)
