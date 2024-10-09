import discord
import logging
import mysql.connector
import requests
from datetime import datetime, timedelta
import pytz
from discord.ext import commands
from discord import ButtonStyle
from discord.ui import Button, View, Modal, TextInput
from dotenv import load_dotenv
import os

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
API_URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")
VIP_DURATION_HOURS = int(os.getenv("VIP_DURATION_HOURS"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
LOCAL_TIMEZONE = pytz.timezone(os.getenv('LOCAL_TIMEZONE'))
conn = mysql.connector.connect(
    host=os.getenv('DATABASE_HOST'),
    port=int(os.getenv('DATABASE_PORT')),
    user=os.getenv('DATABASE_USER'),
    password=os.getenv('DATABASE_PASSWORD'),
    database=os.getenv('DATABASE_NAME')
)
cursor = conn.cursor()
logging.basicConfig(level=logging.INFO)
cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS `{os.getenv('DATABASE_TABLE')}` (
        id INT AUTO_INCREMENT PRIMARY KEY,
        discord_id VARCHAR(255) UNIQUE NOT NULL,
        steam_id VARCHAR(255) UNIQUE NOT NULL
    )
''')

conn.commit()
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Bot is ready: {bot.user}')
    channel = bot.get_channel(CHANNEL_ID)
    
    if channel:
        view = CombinedView()
        await channel.send(f"Welcome! Use the buttons below to register your player ID and receive VIP status on all connected servers. You only need to register once, but afterward, you can claim temporary VIP status for {VIP_DURATION_HOURS} hours.", view=view)
    else:
        print(f"Error: Channel ID {CHANNEL_ID} not found.")

class PlayerIDModal(Modal):
    def __init__(self):
        super().__init__(title="Please input Player-ID")
        self.player_id = TextInput(label="Player-ID (Steam-ID or Gamepass-ID)", placeholder="12345678901234567")
        self.add_item(self.player_id)
    
    async def on_submit(self, interaction: discord.Interaction):
        steam_id = self.player_id.value
        cursor.execute(f"INSERT INTO `{os.getenv('DATABASE_TABLE')}` (discord_id, steam_id) VALUES (%s, %s) ON DUPLICATE KEY UPDATE steam_id = %s", (str(interaction.user.id), steam_id, steam_id))
        conn.commit()
        await interaction.response.send_message(f'Your Player-ID {steam_id} has been saved!', ephemeral=True)

class CombinedView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Register", style=ButtonStyle.danger)
    async def register_button(self, interaction: discord.Interaction, button: Button):
        modal = PlayerIDModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label=f"get VIP ({VIP_DURATION_HOURS} hours)", style=ButtonStyle.green)
    async def give_vip_button(self, interaction: discord.Interaction, button: Button):
        cursor.execute(f"SELECT steam_id FROM `{os.getenv('DATABASE_TABLE')}` WHERE discord_id=%s", (str(interaction.user.id),))
        player = cursor.fetchone()

        if player:
            steam_id = player[0]
            local_time = datetime.now(LOCAL_TIMEZONE)
            expiration_time_local = local_time + timedelta(hours=VIP_DURATION_HOURS)
            expiration_time_utc = expiration_time_local.astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')
            data = {
                "player_id": steam_id,
                "description": f"VIP for {VIP_DURATION_HOURS} hours",
                "expiration": expiration_time_utc
            }
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }
            response = requests.post(f"{API_URL}/add_vip", json=data, headers=headers)
            if response.status_code == 200:
                await interaction.channel.send(f'You now got VIP for {VIP_DURATION_HOURS} hours! Expiration: {expiration_time_local}')
            else:
                await interaction.channel.send(f'Error: VIP status could not been set: {response.text}')
        else:
            await interaction.channel.send("You are not registered! Please use register-button for registration first.")

bot.run(DISCORD_TOKEN)
