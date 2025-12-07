# cogs/events.py
import discord
import asyncio
import logging
from discord.ext import commands
import wavelink

logger = logging.getLogger(__name__)

class EventHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
             self.music_player_instance = bot.music_player
             self.music = self.music_player_instance
        except AttributeError:
             logger.error("Failed to access bot.music_player in EventHandler.__init__! Music features may fail.")
             self.music = None
             self.music_player_instance = None

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"EventHandler Cog ready. Bot: {self.bot.user}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        music_player = self.bot.music_player
        if not music_player or not music_player.vc or not music_player.vc.connected:
            return

        if music_player.vc.channel == before.channel and before.channel != after.channel:
            human_members = [m for m in music_player.vc.channel.members if not m.bot]
            if not human_members:
                logger.info(f"Bot is alone in {music_player.vc.channel.name}, scheduling disconnect.")
                await asyncio.sleep(60) 
                if music_player.vc and music_player.vc.connected:
                    human_members_recheck = [m for m in music_player.vc.channel.members if not m.bot]
                    if not human_members_recheck:
                         logger.info(f"Disconnecting from empty channel: {music_player.vc.channel.name}")
                         await music_player.vc.disconnect()
                         music_player.vc = None 
                         music_player.queue.clear()
                         music_player.loop_mode = "off"
                         music_player.current_song = None

    # --- Wavelink Event Listeners ---
    @commands.Cog.listener("on_wavelink_node_ready")
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        """Log when Lavalink node connects."""
        logger.info(f"✅ Wavelink Node '{payload.node.identifier}' is ready!")


    @commands.Cog.listener("on_wavelink_track_start")
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        """Log when a track starts and update current_song."""
        player: wavelink.Player | None = payload.player
        track: wavelink.Playable | None = payload.track
        music_player = self.bot.music_player
        if not music_player: return

        if player and track:
            logger.info(f"Track started in {player.guild.id}: {track.title}")
            if music_player.vc == player:
                music_player.current_song = track
            else:
                logger.warning(f"TrackStart event received for player not matching managed VC. Event Player: {player.guild.id}, Managed VC: {music_player.vc.guild.id if music_player.vc else 'None'}")



    @commands.Cog.listener("on_wavelink_track_end")
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player: wavelink.Player | None = payload.player
        track: wavelink.Playable | None = payload.track
        reason: str = payload.reason

        music_player = self.bot.music_player
        if not music_player:
            logger.error("Cannot process track_end: self.bot.music_player is not available!")
            return

        if not player or not music_player.vc or player != music_player.vc:
            logger.warning(f"Track end event ignored because player ({player.guild.id if player else 'N/A'}) does not match managed VC ({music_player.vc.guild.id if music_player.vc else 'N/A'}).")
            return

        logger.info(f"Track ended in Cog: {track.title if track else 'N/A'}. Reason: {reason}. Player Guild: {player.guild.id}")

        ended_track = track

        if reason.upper() == "FINISHED":
            if music_player.loop_mode == "single" and ended_track:
                logger.info(f"Attempting to loop single track: {ended_track.title}")
                try:
                    await player.play(ended_track)
                except Exception as e:
                    logger.error(f"Error re-playing single loop {ended_track.title} via Cog: {e}", exc_info=True)
                    music_player.current_song = None
                    if music_player.queue:
                        logger.info("Single loop failed, attempting next in queue.")
                        await music_player.start_playback()
            elif music_player.loop_mode == "queue" and ended_track:
                logger.info(f"Attempting to loop queue. Adding back: {ended_track.title}")
                music_player.queue.append(ended_track)
                logger.debug(f"Queue size after append: {len(music_player.queue)}. Calling start_playback.")
                await music_player.start_playback()
            elif music_player.queue:
                logger.info("Playing next track in queue (loop mode off).")
                await music_player.start_playback()
            else:
                logger.info("Queue empty, not looping. Playback finished.")
                music_player.current_song = None
                if getattr(music_player, 'autoplay_enabled', False):
                    ctx = None
                    try:
                        guild = player.guild
                        if guild and guild.text_channels:
                            ctx = guild.text_channels[0]
                    except Exception:
                        ctx = None
                    track = await music_player.autoplay_random(ctx)
                    if track:
                        await music_player.start_playback()

        elif reason.upper() == "LOAD_FAILED":
            logger.warning(f"Track '{track.title if track else 'N/A'}' failed to load (case-insensitive check).")
            if music_player.current_song == track:
                music_player.current_song = None
            if music_player.queue:
                logger.info("Load failed, attempting to play next in queue.")
                await music_player.start_playback()
            else:
                logger.info("Load failed and queue is empty.")

        else: 
            logger.debug(f"Track end reason ({reason}) doesn't require starting next song (case-insensitive check).")
            if reason.upper() in ("STOPPED", "REPLACED") and music_player.loop_mode != "single":
                if reason.upper() == "STOPPED":
                    logger.debug(f"Clearing current_song due to STOPPED and not looping single.")
                    music_player.current_song = None

def setup(bot):
    bot.add_cog(EventHandler(bot))