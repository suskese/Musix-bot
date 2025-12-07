# main.py
import discord
from discord.ext import commands
from discord import Intents
import logging
import asyncio

from core.config import DISCORD_TOKEN, DISCORD_GUILD_IDS
from core.music import MusicPlayer



import os
os.makedirs('cache/logs', exist_ok=True)
spotify_log_path = os.path.join('cache/logs', 'spotify.log')
with open(spotify_log_path, 'w', encoding='utf-8'):
    pass
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=os.path.join('cache/logs', 'bot.log'),
    filemode="w",
    encoding='utf-8',
)
logger = logging.getLogger("bot")

# Setup bot with required intents
intents = Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents, debug_guilds=DISCORD_GUILD_IDS if DISCORD_GUILD_IDS else None)

bot.music_player = MusicPlayer(bot)

# Register cogs
async def load_cogs():
    bot.load_extension("cogs.commands")
    bot.load_extension("cogs.events")
    logger.info("All cogs loaded.")

@bot.event
async def on_ready():
    logger.info(f"Bot connected as {bot.user}")
    logger.info(f"Guild IDs configured: {DISCORD_GUILD_IDS}")
    
    # Connect Wavelink nodes
    try:
        await bot.music_player.connect_nodes()
        logger.info("Wavelink nodes connected.")
    except Exception as e:
        logger.error(f"Failed to connect Wavelink nodes: {e}", exc_info=True)
    
    # Sync commands
    logger.info("Starting application command sync...")
    try:
        synced = await bot.sync_commands()
        logger.info(f"Application commands synced successfully. Synced: {synced}")
    except Exception as e:
        logger.error(f"Error syncing commands: {e}", exc_info=True)

async def main():
    async with bot:
        await load_cogs()
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
