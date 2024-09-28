import discord
import logging
import sqlite3
import requests
from datetime import datetime, timedelta
import pytz
from discord.ext import commands
from discord import ButtonStyle
from discord.ui import Button, View, Modal, TextInput
from dotenv import load_dotenv
import os

# Lade Umgebungsvariablen aus der .env-Datei
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
API_URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")
VIP_DURATION_HOURS = int(os.getenv("VIP_DURATION_HOURS"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

# Definiere deine lokale Zeitzone (z.B. UTC+2)
LOCAL_TIMEZONE = pytz.timezone('Europe/Berlin')

# Verbindung zur SQLite-Datenbank herstellen
conn = sqlite3.connect('players.db')
cursor = conn.cursor()
logging.basicConfig(level=logging.INFO)
# Tabelle für Spieler erstellen, falls sie nicht existiert
cursor.execute('''CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id TEXT UNIQUE NOT NULL,
    steam_id TEXT UNIQUE NOT NULL
)''')
conn.commit()

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Bot ist bereit als {bot.user}')
    channel = bot.get_channel(CHANNEL_ID)
    
    if channel:
        view = CombinedView()  # Erstelle eine View mit beiden Buttons
        await channel.send(f"Willkommen! Verwende die Buttons unten, um deine Player-ID zu registrieren und VIP auf allen angeschlossenen Servern zu erhalten. Du musst Dich einmalig registrieren, kannst Dir danach aber ein temporäres VIP für {VIP_DURATION_HOURS} Std. abholen.", view=view)
    else:
        print(f"Fehler: Kanal mit ID {CHANNEL_ID} nicht gefunden.")

# Modal für die Player-ID Eingabe
class PlayerIDModal(Modal):
    def __init__(self):
        super().__init__(title="Player-ID Eingeben")

        # TextInput für die Player-ID
        self.player_id = TextInput(label="Player-ID (Steam-ID oder Gamepass-ID)", placeholder="12345678901234567")
        self.add_item(self.player_id)

    # Wird aufgerufen, wenn das Formular abgeschickt wird
    async def on_submit(self, interaction: discord.Interaction):
        steam_id = self.player_id.value
        
        # Speichern in der Datenbank
        cursor.execute("INSERT OR REPLACE INTO players (discord_id, steam_id) VALUES (?, ?)", (str(interaction.user.id), steam_id))
        conn.commit()

        await interaction.response.send_message(f'Deine Player-ID {steam_id} wurde gespeichert!', ephemeral=True)  # Antwort nur für den Benutzer sichtbar


# Ansicht für beide Buttons (Registrierung und VIP)
class CombinedView(View):
    def __init__(self):
        super().__init__(timeout=None)

    # Anpassung des Register-Buttons
    @discord.ui.button(label="Register", style=ButtonStyle.danger)
    async def register_button(self, interaction: discord.Interaction, button: Button):
        modal = PlayerIDModal()
        await interaction.response.send_modal(modal)

    # Button für VIP-Vergabe
    @discord.ui.button(label=f"get VIP ({VIP_DURATION_HOURS} hours)", style=ButtonStyle.green)
    async def give_vip_button(self, interaction: discord.Interaction, button: Button):
        # Hol die SteamID des Benutzers aus der Datenbank
        cursor.execute("SELECT steam_id FROM players WHERE discord_id=?", (str(interaction.user.id),))
        player = cursor.fetchone()

        if player:
            steam_id = player[0]

            # Lokale Zeit und VIP-Dauer berechnen
            local_time = datetime.now(LOCAL_TIMEZONE)
            expiration_time_local = local_time + timedelta(hours=VIP_DURATION_HOURS)

            # Konvertiere die lokale Ablaufzeit in UTC
            expiration_time_utc = expiration_time_local.astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')

            data = {
                "player_id": steam_id,
                "description": f"VIP for {VIP_DURATION_HOURS} hours",
                "expiration": expiration_time_utc
            }

            # API-Key in die Header der Anfrage einfügen
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }

            # Anfrage an die API senden
            response = requests.post(f"{API_URL}/add_vip", json=data, headers=headers)

            if response.status_code == 200:
                await interaction.channel.send(f'Du hast jetzt {VIP_DURATION_HOURS} Stunden VIP-Status! Ablauf: {expiration_time_local}')
            else:
                await interaction.channel.send(f'Fehler bei der Vergabe des VIP-Status: {response.text}')
        else:
            await interaction.channel.send("Du bist noch nicht registriert! Verwende den Button, um dich zu registrieren.")

# Starte den Bot
bot.run(DISCORD_TOKEN)
