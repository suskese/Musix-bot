# core/music.py
import discord
import wavelink
import asyncio
import logging
from core.config import LAVALINK_HOST, LAVALINK_PASSWORD

logger = logging.getLogger(__name__)

class MusicPlayer:

    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.vc: wavelink.Player | None = None
        self.volume = 0.2
        self.loop_mode = "off" #'off', 'single', 'queue'
        self.current_song: wavelink.Playable | None = None
        self.nightcore_enabled = False
        self.history = [] 
        self.autoplay_enabled = False
        
    async def set_bassboost(self, value: int | str):
        """Set bassboost filter. Value: 1-100 or 'off'."""
        if not self.vc or not self.vc.connected:
            return False

        filters: wavelink.Filters = self.vc.filters if hasattr(self.vc, 'filters') else wavelink.Filters()
        if value == 'off' or value == 0:
            filters.equalizer.reset()
            await self.vc.set_filters(filters)
            return True

        try:
            value = int(value)
            if not (1 <= value <= 100):
                return False
        except Exception:
            return False

        # Bassboost
        boost = (value / 100) * 0.5
        bands = [{"band": i, "gain": boost if i < 7 else 0.0} for i in range(15)]
        filters.equalizer.set(bands=bands)
        await self.vc.set_filters(filters)
        return True
            
    async def play_next(self, ctx, query):
        """Add a track to the front of the queue and play if nothing is playing."""
        from core.config import HARDCODED_TRACK_MAP
        current_vc = await self.join(ctx)
        if not current_vc:
            return None
        self.vc = current_vc
        try:
            # Check hardcoded map first (case-insensitive, strip)
            q = query.lower().strip()
            url = HARDCODED_TRACK_MAP.get(q)
            if not url:
                for k, v in HARDCODED_TRACK_MAP.items():
                    if k in q:
                        url = v
                        break
            if url:
                tracks = await wavelink.Playable.search(url)
            else:
                tracks = await wavelink.Playable.search(query)
            if not tracks:
                embed = discord.Embed(title="No Results", description=f"Couldn't find any tracks for '{query}'.", color=0xED4245)
                await ctx.followup.send(embed=embed, ephemeral=True)
                return None
            track = tracks[0]
            self.queue.insert(0, track)
            if not self.vc.playing:
                await self.start_playback()
            return track
        except Exception as e:
            logger.error(f"Error during play_next: {e}", exc_info=True)
            embed = discord.Embed(title="Error", description="An error occurred while adding the song to the front of the queue.", color=0xED4245)
            await ctx.followup.send(embed=embed, ephemeral=True)
            return None

    def shuffle_queue(self):
        import random
        random.shuffle(self.queue)

    def clear_queue(self):
        self.queue.clear()

    def get_nowplaying(self):
        return self.current_song

    async def seek(self, position_ms):
        if self.vc and self.vc.connected and self.vc.playing:
            await self.vc.seek(position_ms)
            return True
        return False

    async def search_tracks(self, query):
        try:
            tracks = await wavelink.Playable.search(query)
            return tracks
        except Exception as e:
            logger.error(f"Error during search_tracks: {e}", exc_info=True)
            return []
        
    async def autoplay_random(self, ctx=None):
        # Pick a random song from history
        import random
        if self.history:
            track = random.choice(self.history)
            self.queue.append(track)
            if ctx:
                await ctx.send(f"Autoplay: Queued random track **{track.title}**.")
            return track
        return None

    async def set_nightcore(self, enabled: bool):
        self.nightcore_enabled = enabled

        if self.vc and self.vc.connected:
            filters: wavelink.Filters = self.vc.filters if hasattr(self.vc, 'filters') else wavelink.Filters()
            if enabled:
                # Nightcore: speed up and pitch up
                filters.timescale.set(pitch=1.2, speed=1.1, rate=1)
            else:
                filters.timescale.reset()
            await self.vc.set_filters(filters)

    async def normalize(self):
        self.volume = 0.2
        await self.set_nightcore(False)
        
        if self.vc and self.vc.connected:
            await self.vc.set_volume(int(self.volume * 100))

    async def connect_nodes(self):
        if wavelink.Pool.nodes:
             logger.info("Lavalink nodes already connected or connection attempt in progress. Skipping new connection.")
             return

        logger.info("Attempting to connect to Lavalink node...")
        await self.bot.wait_until_ready()

        try:
            node = wavelink.Node(
                uri=LAVALINK_HOST,
                password=LAVALINK_PASSWORD,
            )
            await wavelink.Pool.connect(nodes=[node], client=self.bot, cache_capacity=100)
        except Exception as e:
            logger.error(f"❌ Lavalink connection failed: {e}", exc_info=True)

    async def join(self, ctx):
        if not ctx.author.voice or not ctx.author.voice.channel:
            response_method = ctx.followup.send if ctx.interaction.response.is_done() else ctx.respond
            await response_method("You need to be in a voice channel first.", ephemeral=True)
            return None
        channel = ctx.author.voice.channel

        if self.vc and self.vc.connected and self.vc.channel == channel:
             return self.vc
        elif self.vc and self.vc.connected and self.vc.channel != channel:
             logger.info(f"Moving from {self.vc.channel.name} to {channel.name}")
             await self.vc.move_to(channel)
             return self.vc

        try:
            self.vc = await channel.connect(cls=wavelink.Player)
            await self.vc.set_volume(int(self.volume * 100)) 
            logger.info(f"Connected to voice channel: {channel.name}")
            return self.vc
        except discord.ClientException: 
            logger.warning(f"Bot is already connected to a voice channel (Guild: {ctx.guild.me.voice.channel.guild.id if ctx.guild.me.voice else 'N/A'}, Channel: {ctx.guild.me.voice.channel.name if ctx.guild.me.voice else 'N/A'}). Trying to retrieve.")
            if ctx.voice_client and isinstance(ctx.voice_client, wavelink.Player):
                self.vc = ctx.voice_client
                if self.vc.channel != channel:
                     logger.info(f"Found existing connection, moving to {channel.name}")
                     await self.vc.move_to(channel)
                return self.vc
            else: 
                 response_method = ctx.followup.send if ctx.interaction.response.is_done() else ctx.respond
                 await response_method("I seem to be connected elsewhere or stuck. Try disconnecting me manually.", ephemeral=True)
                 return None
        except Exception as e:
            logger.error(f"Error joining voice channel: {e}", exc_info=True)
            response_method = ctx.followup.send if ctx.interaction.response.is_done() else ctx.respond
            await response_method("Couldn't join the voice channel due to an error.", ephemeral=True)
            return None

    async def search_and_play(self, ctx, query, return_track=False):
        from core.config import HARDCODED_TRACK_MAP
        current_vc = await self.join(ctx) 
        if not current_vc:
            return None if return_track else None
        self.vc = current_vc 

        try:
            # Check hardcoded map first (case-insensitive, strip)
            q = query.lower().strip()
            url = HARDCODED_TRACK_MAP.get(q)
            if not url:
                for k, v in HARDCODED_TRACK_MAP.items():
                    if k in q:
                        url = v
                        break
            if url:
                tracks = await wavelink.Playable.search(url)
            else:
                tracks = await wavelink.Playable.search(query)

            if not tracks:
                embed = discord.Embed(title="No Results", description=f"Couldn't find any tracks for '{query}'.", color=0xED4245)
                await ctx.followup.send(embed=embed, ephemeral=True)
                return None if return_track else None

            if isinstance(tracks, wavelink.Playlist):
                added = len(tracks.tracks)
                self.queue.extend(tracks.tracks) 
                logger.info(f"Added playlist '{tracks.name}' ({added} songs) to queue.")
                embed = discord.Embed(title="Playlist Added", description=f"Added playlist **{tracks.name}** ({added} songs) to the queue.", color=0x1DB954)
                first_track = tracks.tracks[0] if added > 0 else None
            else:
                track: wavelink.Playable = tracks[0]
                self.queue.append(track)
                logger.info(f"Added to queue: {track.title}")
                embed = discord.Embed(title="Track Added", description=f"Added to queue: **{track.title}**", color=0x1DB954)
                first_track = track

            if not self.vc.playing:
                logger.info("VC is not playing, calling start_playback.")
                await self.start_playback() 
            else:
                logger.info(f"VC is already playing '{self.current_song.title if self.current_song else 'something'}', song/playlist added to queue.")

            await ctx.followup.send(embed=embed)

            if return_track:
                return first_track
            return None

        except Exception as e:
            logger.error(f"Error during search_and_play: {e}", exc_info=True)
            embed = discord.Embed(title="Error", description="An error occurred while searching or adding the song.", color=0xED4245)
            await ctx.followup.send(embed=embed, ephemeral=True)
            return None if return_track else None

    async def start_playback(self):
        logger.debug(f"[MusicPlayer] start_playback called. Queue: {[getattr(t, 'title', None) for t in self.queue]}, current_song={getattr(self.current_song, 'title', None)}, vc={self.vc}, vc.connected={getattr(self.vc, 'connected', None)}")
        logger.info("Attempting start_playback.")

        if not self.queue:
            logger.info("start_playback: Queue is empty. Playback stopped.")
            logger.debug(f"[MusicPlayer] No tracks left in queue. Setting current_song=None.")
            self.current_song = None
            return

        if not self.vc or not self.vc.connected:
            logger.warning("start_playback: VC is not valid or connected. Attempting to reconnect to last used channel.")
            channel = None
            try:
                if self.current_song and hasattr(self.current_song, 'guild') and self.current_song.guild:
                    guild = self.current_song.guild
                    if guild and guild.me and guild.me.voice and guild.me.voice.channel:
                        channel = guild.me.voice.channel
                if not channel and hasattr(self.bot, 'voice_clients'):
                    for vc in self.bot.voice_clients:
                        if vc and vc.channel:
                            channel = vc.channel
                            break
                if not channel:
                    logger.error("start_playback: Could not determine channel to reconnect. Aborting playback.")
                    self.current_song = None
                    return
                self.vc = await channel.connect(cls=wavelink.Player)
                await self.vc.set_volume(int(self.volume * 100))
                logger.info(f"Reconnected to voice channel: {channel.name}")
            except Exception as e:
                logger.error(f"start_playback: Failed to reconnect VC: {e}", exc_info=True)
                self.current_song = None
                return

        track = self.queue.pop(0)
        logger.info(f"start_playback: Popped track '{getattr(track, 'title', repr(track))}'. Queue size now: {len(self.queue)}")

        # Debug: Check track fields
        logger.info(f"Track debug: title={getattr(track, 'title', None)}, uri={getattr(track, 'uri', None)}, source={getattr(track, 'source', None)}, album={getattr(track, 'album', None)}")
        logger.info(f"VC debug: connected={self.vc.connected}, channel={getattr(self.vc, 'channel', None)}, player={repr(self.vc)}")

        # Extra: Check Lavalink node state
        try:
            node = getattr(self.vc, 'node', None)
            if node:
                logger.info(f"Lavalink node state: connected={getattr(node, 'connected', None)}, stats={getattr(node, 'stats', None)}")
        except Exception as e:
            logger.warning(f"Could not log Lavalink node state: {e}")

        try:
            logger.info("Calling self.vc.play(track)...")
            await self.vc.play(track)
            logger.info("self.vc.play(track) completed without exception.")
            self.current_song = track
            logger.info(f"start_playback: vc.play called for '{getattr(track, 'title', repr(track))}'")

            self.history.append(track)
            if len(self.history) > 20:
                self.history = self.history[-20:]
        except Exception as e:
            logger.error(f"start_playback: Error during vc.play for '{getattr(track, 'title', repr(track))}': {e}", exc_info=True)
            logger.debug(f"[MusicPlayer] Playback failed. Setting current_song=None.")
            self.current_song = None

    async def stop(self, ctx):
        response_method = ctx.followup.send if ctx.interaction.response.is_done() else ctx.respond

        if self.vc and self.vc.connected:
            logger.info(f"Stop command issued in {ctx.guild.name}")
            self.queue.clear()
            self.loop_mode = "off"
            await self.vc.stop()
            await self.vc.disconnect() 
            self.current_song = None
            self.vc = None 
        else:
            embed = discord.Embed(title="Not Connected", description="Not connected to a voice channel or already disconnected.", color=0xED4245)
            await response_method(embed=embed, ephemeral=True)

    async def add_audio_file(self, attachment: discord.Attachment, ctx) -> wavelink.Playable | None:
        """Download and convert a Discord attachment to a playable audio file."""
        import os
        import aiohttp
        
        try:
            os.makedirs('audio_files', exist_ok=True)
            
            filename = attachment.filename
            filepath = os.path.join('audio_files', filename)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to download attachment: {resp.status}")
                        return None
                    with open(filepath, 'wb') as f:
                        f.write(await resp.read())
            
            logger.info(f"Downloaded audio file: {filepath}")
            
            # Create a wavelink Playable from the local file
            # Use file:// URI for local files
            file_uri = f"file:///{os.path.abspath(filepath).replace(os.sep, '/')}"
            
            # Create a custom Playable object for local files
            playable = wavelink.Playable(
                source=filepath,
                identifier=filepath,
                isSeekable=True,
                author="Local File",
                length=0,
                isStream=False,
                title=filename,
                uri=file_uri
            )
            
            self.queue.append(playable)
            logger.info(f"Added audio file to queue: {filename}")
            return playable
            
        except Exception as e:
            logger.error(f"Error adding audio file: {e}", exc_info=True)
            return None
