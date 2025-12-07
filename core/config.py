# core/config.py
import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
LAVALINK_HOST = os.getenv("LAVALINK_HOST", "http://localhost:2333")
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD", "youshallnotpass")

# Server IDs for slash command synchronization
# Add server IDs here to sync slash commands only to specific servers for faster updates
# TEMPORARILY EMPTY TO DEBUG - Commands should appear in 1 hour globally
# Example: [123456789, 987654321]
DISCORD_GUILD_IDS = []

# Map problematic song queries to direct YouTube links (editable)
HARDCODED_TRACK_MAP = {
    "tom tom": "https://www.youtube.com/watch?v=-8MbcIvCAec",
    "tom tom holy fuck": "https://www.youtube.com/watch?v=-8MbcIvCAec",
    # Add more mappings as needed
}