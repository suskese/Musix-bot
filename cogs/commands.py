# cogs/commands.py
import discord
from discord.ext import commands
from discord import option
import logging
import asyncio
from core.config import DISCORD_GUILD_IDS

logger = logging.getLogger(__name__)

class QueueControlsView(discord.ui.View):

    def __init__(self, music_player, ctx):
        super().__init__(timeout=60)
        self.music = music_player
        self.ctx = ctx

    @discord.ui.button(label="⏯️ Play/Pause", style=discord.ButtonStyle.primary, custom_id="playpause")
    async def playpause(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not self.music.vc or not self.music.vc.connected:
            embed = discord.Embed(title="Not Connected", description="Not connected to a voice channel.", color=0xED4245)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if self.music.vc._paused:
            await self.music.vc.pause(False)
            embed = discord.Embed(title="Resumed", description="Resumed playback.", color=0x1DB954)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif self.music.vc.playing:
            await self.music.vc.pause(True)
            embed = discord.Embed(title="Paused", description="Paused playback.", color=0x1DB954)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(title="Nothing to Play/Pause", description="Nothing is currently playing.", color=0xED4245)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.secondary, custom_id="skip")
    async def skip(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.music.vc and self.music.vc.playing:
            await self.music.vc.stop()
            if self.music.queue:
                await self.music.start_playback()
            embed = discord.Embed(title="Skipped", description="Skipped the current song.", color=0x1DB954)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(title="Nothing Playing", description="Nothing is currently playing.", color=0xED4245)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.danger, custom_id="stop")
    async def stop(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.music.vc:
            self.music.queue.clear()
            await self.music.stop(self.ctx)
            embed = discord.Embed(title="Stopped & Disconnected", color=0x1DB954)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(title="Not Connected", description="Not connected to a voice channel.", color=0xED4245)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🔀 Shuffle", style=discord.ButtonStyle.success, custom_id="shuffle")
    async def shuffle(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.music.shuffle_queue()
        embed = discord.Embed(title="Queue Shuffled", color=0x1DB954)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🔁 Loop", style=discord.ButtonStyle.secondary, custom_id="loop")
    async def loop(self, button: discord.ui.Button, interaction: discord.Interaction):
        # Toggle loop mode: off -> queue -> single -> off
        current = getattr(self.music, 'loop_mode', 'off')
        if current == 'off':
            self.music.loop_mode = 'queue'
            desc = "Loop mode set to queue."
        elif current == 'queue':
            self.music.loop_mode = 'single'
            desc = "Loop mode set to single."
        else:
            self.music.loop_mode = 'off'
            desc = "Loop mode off."
        embed = discord.Embed(title="Loop Mode", description=desc, color=0x1DB954)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class CommandsCog(commands.Cog):

    @discord.slash_command(description="Bassboost: off or 1-100")
    async def bassboost(self, ctx: discord.ApplicationContext, value: str):
        """Set bassboost filter. Value: 'off' or 1-100."""
        await ctx.defer(ephemeral=True)
        # Accept both int and 'off'
        if value.lower() == 'off':
            ok = await self.music.set_bassboost('off')
            if ok:
                embed = discord.Embed(title="Bassboost Off", description="Bassboost filter disabled.", color=0x1DB954)
            else:
                embed = discord.Embed(title="Error", description="Failed to disable bassboost. Is the bot in a voice channel?", color=0xED4245)
            return await ctx.followup.send(embed=embed)
        try:
            level = int(value)
        except Exception:
            embed = discord.Embed(title="Invalid Value", description="Value must be 'off' or a number 1-100.", color=0xED4245)
            return await ctx.followup.send(embed=embed)
        if not (1 <= level <= 100):
            embed = discord.Embed(title="Invalid Value", description="Bassboost value must be 1-100.", color=0xED4245)
            return await ctx.followup.send(embed=embed)
        ok = await self.music.set_bassboost(level)
        if ok:
            embed = discord.Embed(title="Bassboost Enabled", description=f"Bassboost set to {level}.", color=0x1DB954)
        else:
            embed = discord.Embed(title="Error", description="Failed to set bassboost. Is the bot in a voice channel?", color=0xED4245)
        await ctx.followup.send(embed=embed)

    @discord.slash_command(description="Show all bot commands and their descriptions")
    async def help(self, ctx: discord.ApplicationContext):
        embed1 = discord.Embed(
            color=3447003,
            title="🎵 Music / DJ 🎵",
            description="🎧 **/play [query]  ‎ ‎ ‎ ‎  /skip ‎ ‎  ‎ ‎  /stop** - Basic commands\n➡️ **/playnext [query]** - Adds song as next in the queue\n📃 **/queue**‎ ‎ & ‎‎  **/clearqueue** - Queue magnagment\n🔁 **/loop [single | queue | off]** - Loop song / queue\n⏱️ **/nowplaying** ‎ ‎ or‎ ‎ ** /np** - Displays current playing song\n🔎 **/search [query]** - Advanced play command\n📁 **/play_audio [file]** - Play local audio files (MP3, WAV, OGG, FLAC)",
        )
        embed2 = discord.Embed(
            color=10181046,
            title="💎Fun & Experimental (WIP) 💎 ",
            description="🔈** /volume [1-100]** - Sets music volume (default 20)\n🔊 **/bassboost [off | 1-100]** - Bass boosts music \n⌛ ** /seek [seconds]** - Sets song to the specific timestamp\n\n🎇 ** /nightcore [on | off]** -Toggle nightcore effect on or off\n🕸️ ** /normalize** - Set default volume and turn off nightcore\n\n📜 ** /shuffle** - Mixes queue's song order \n📒 ** /history [count] [replay]** - Show last played songs and replay.\n🚘 ** /autoplay [on|off]** - play random track after queue ends",
        )
        embed3 = discord.Embed(
            color=15158332,
            title="⚠️ ADMIN ONLY COMMANDS ⚠️",
            description="🟢 **/spotify_stalk** -Stalks and plays songs from client (OAuth)\n🟢 **/spotify_stopplaying** - Stops /spotify_stalk",
        )
        await ctx.respond(embeds=[embed1, embed2, embed3], ephemeral=True)
    # Store stalk tasks per user
    spotify_stalk_tasks = {}

    @discord.slash_command(description="Continuously sync Discord music with your Spotify playback (play/pause/seek/track change)")
    async def spotify_stalk(self, ctx: discord.ApplicationContext):
        import core.spotify_oauth as spotify_oauth
        await ctx.defer(ephemeral=True)
        user_id = str(ctx.author.id)

        if not ctx.author.voice or not ctx.author.voice.channel:
            embed = discord.Embed(
                title="Not in Voice Channel",
                description="You must be in a voice channel to use this command!",
                color=0xED4245
            )
            await ctx.followup.send(embed=embed, ephemeral=True)
            return
        if not self.music.vc or not self.music.vc.connected:
            await self.music.join(ctx)

        if user_id in self.spotify_stalk_tasks:
            await ctx.followup.send("Spotify stalk is already running for you! Use /spotify_stopplaying to stop.", ephemeral=True)
            return

        # DEBUG: Log user_id and token presence
        logger.info(f"[SpotifyStalk] Invoked by user_id={user_id}, has_token={bool(spotify_oauth.spotify_oauth.tokens.get(user_id))}")
        access_token = spotify_oauth.spotify_oauth.get_access_token(user_id)
        logger.info(f"[SpotifyStalk] get_access_token returned: {bool(access_token)}")
        if not access_token:
            import threading
            auth_done = threading.Event()
            result_holder = {'ok': False}
            def run_oauth():
                def send_link(url):
                    embed = discord.Embed(
                        title="Spotify Authorization Required",
                        description=f"[Click here to authorize with Spotify]({url})\n\nAfter authorizing, please wait for confirmation.",
                        color=0x1DB954
                    )
                    asyncio.run_coroutine_threadsafe(ctx.followup.send(embed=embed, ephemeral=True), ctx.bot.loop)
                ok = spotify_oauth.spotify_oauth.authorize_user(user_id, send_link_callback=send_link)
                result_holder['ok'] = ok
                auth_done.set()
            threading.Thread(target=run_oauth, daemon=True).start()
            while not auth_done.is_set():
                await asyncio.sleep(1)
            if not result_holder['ok']:
                await ctx.followup.send("Spotify authorization failed or timed out. Please try again.", ephemeral=True)
                return
            access_token = spotify_oauth.spotify_oauth.get_access_token(user_id)
            if not access_token:
                await ctx.followup.send("Spotify authorization did not complete. Please try again.", ephemeral=True)
                return

        # Start background stalk task
        logger.info(f"[SpotifyStalk] Starting stalk task for user_id={user_id}")
        async def stalk_task():
            import logging
            import os

            spotify_log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cache', 'logs', 'spotify.log')
            os.makedirs(os.path.dirname(spotify_log_path), exist_ok=True)
            spotify_logger = logging.getLogger('spotify_logger')
            spotify_logger.setLevel(logging.INFO)
            if not spotify_logger.handlers:
                handler = logging.FileHandler(spotify_log_path, encoding='utf-8')
                formatter = logging.Formatter('%(asctime)s - %(message)s')
                handler.setFormatter(formatter)
                spotify_logger.addHandler(handler)

            last_track_id = None
            last_is_playing = None
            last_position = None
            error_count = 0
            try:
                while True:
                    try:
                        data = await asyncio.wait_for(
                            asyncio.to_thread(spotify_oauth.spotify_oauth.get_currently_playing, user_id),
                            timeout=10
                        )
                    except asyncio.TimeoutError:
                        spotify_logger.warning(f"[SpotifyStalk] Spotify API timeout for user_id={user_id}. Retrying in 8s.")
                        await asyncio.sleep(8)
                        continue
                    except Exception as e:
                        spotify_logger.error(f"[SpotifyStalk] Spotify API error: {e}", exc_info=True)
                        error_count += 1
                        await asyncio.sleep(8)
                        if error_count > 5:
                            await ctx.followup.send("Spotify stalk stopped due to repeated errors.", ephemeral=True)
                            self.spotify_stalk_tasks.pop(user_id, None)
                            return
                        continue
                    error_count = 0
                    spotify_logger.info(f"[SpotifyStalk] Spotify data for user_id={user_id}: {repr(data)}")
                    if not data:
                        spotify_logger.warning(f"[SpotifyStalk] get_currently_playing returned None for user_id={user_id}. This usually means the access token is invalid, expired, or the Spotify account is not actively playing on a device.")
                        await asyncio.sleep(4)
                        continue
                    if 'error' in data:
                        spotify_logger.warning(f"[SpotifyStalk] Spotify API error for user_id={user_id}: {data['error']}")
                        await asyncio.sleep(8)
                        continue
                    if not data.get("item"):
                        spotify_logger.info(f"[SpotifyStalk] No track playing for user_id={user_id}. Full data: {repr(data)}")
                        await asyncio.sleep(3)
                        continue
                    item = data["item"]
                    track_id = item.get("id")
                    track_name = item.get("name")
                    artists = ", ".join([a["name"] for a in item.get("artists", [])])
                    is_playing = data.get("is_playing", False)
                    position_ms = data.get("progress_ms", 0)

                    #+0.5s offset for better sync
                    seek_ms = max(0, position_ms + 1000)

                    spotify_logger.info(f"[SpotifyStalk] Track: {track_name}, Artists: {artists}, Playing: {is_playing}, Position: {position_ms}, Seek: {seek_ms}")

                    # Always seek to correct position after any play/pause/track change
                    if track_id != last_track_id:
                        author = item["artists"][0]["name"] if item.get("artists") else ""
                        query = f"{track_name} {artists} {author}".strip()
                        spotify_logger.info(f"[SpotifyStalk] New track detected. Query: {query}")
                        if self.music.vc and self.music.vc.playing:
                            spotify_logger.info(f"[SpotifyStalk] Stopping current playback for new track.")
                            await self.music.vc.stop()
                        self.music.queue.clear()
                        track = await self.music.play_next(ctx, query)
                        spotify_logger.info(f"[SpotifyStalk] play_next returned: {track}")
                        await asyncio.sleep(0.5)
                        await self.music.seek(seek_ms)
                        last_track_id = track_id
                        last_position = seek_ms
                        last_is_playing = is_playing
                    else:
                        seek_needed = False
                        if last_position is not None and abs(seek_ms - last_position) > 1800:
                            seek_needed = True
                        if is_playing != last_is_playing:
                            seek_needed = True
                        if seek_needed:
                            spotify_logger.info(f"[SpotifyStalk] Seeking to {seek_ms}")
                            await self.music.seek(seek_ms)
                        if is_playing != last_is_playing:
                            if self.music.vc and self.music.vc.connected:
                                spotify_logger.info(f"[SpotifyStalk] Pausing/Resuming: {not is_playing}")
                                await self.music.vc.pause(not is_playing)
                            last_is_playing = is_playing
                        last_position = seek_ms

                    await asyncio.sleep(2.5)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                spotify_logger.error(f"[SpotifyStalk] Error: {e}", exc_info=True)
                error_count += 1
                if error_count > 5:
                    await ctx.followup.send("Spotify stalk stopped due to repeated errors.", ephemeral=True)
                    self.spotify_stalk_tasks.pop(user_id, None)
            finally:
                self.spotify_stalk_tasks.pop(user_id, None)

        task = asyncio.create_task(stalk_task())
        self.spotify_stalk_tasks[user_id] = task
        await ctx.followup.send("Spotify stalk started! Use /spotify_stopplaying to stop.", ephemeral=True)

    @discord.slash_command(description="Stop Spotify-based playback and stalk mode (stops music in Discord)")
    async def spotify_stopplaying(self, ctx: discord.ApplicationContext):
        user_id = str(ctx.author.id)
        # Cancel stalk task if running
        task = self.spotify_stalk_tasks.pop(user_id, None)
        if task:
            task.cancel()
            await asyncio.sleep(0)
        if self.music.vc:
            self.music.queue.clear()
            await self.music.stop(ctx)
            embed = discord.Embed(title="Stopped Spotify Playback & Stalk", color=0x1DB954)
            view = QueueControlsView(self.music, ctx)
            await ctx.respond(embed=embed, view=view, ephemeral=True)
        else:
            embed = discord.Embed(title="Not Connected", description="Not connected to a voice channel.", color=0xED4245)
            await ctx.respond(embed=embed, ephemeral=True)

    def __init__(self, bot):
        self.bot = bot
        self.music = bot.music_player

    def _song_line(self, song, show_length=False):
        title = getattr(song, 'title', 'Unknown')
        url = getattr(song, 'uri', None) or getattr(song, 'url', None)
        if url:
            title = f"[{title}]({url})"
        length = ""
        if show_length and hasattr(song, 'length') and song.length:
            mins = song.length // 60000
            secs = (song.length // 1000) % 60
            length = f" `{mins}:{secs:02d}`"
        return f"{title}{length}"

    def _song_embed(self, song, title="Song"):
        embed = discord.Embed(title=title, color=0x1DB954)
        song_title = getattr(song, 'title', 'Unknown')
        url = getattr(song, 'uri', None) or getattr(song, 'url', None)
        if url:
            embed.description = f"[{song_title}]({url})"
        else:
            embed.description = song_title
        if hasattr(song, 'length') and song.length:
            mins = song.length // 60000
            secs = (song.length // 1000) % 60
            embed.add_field(name="Length", value=f"{mins}:{secs:02d}", inline=True)
        if hasattr(song, 'author') and song.author:
            embed.add_field(name="Artist", value=song.author, inline=True)

        album = getattr(song, 'album', None)
        if album and isinstance(album, str):
            embed.add_field(name="Album", value=album, inline=True)

        thumb = getattr(song, 'artwork_url', None) or getattr(song, 'thumbnail', None)
        if not thumb:

            uri = getattr(song, 'uri', None) or getattr(song, 'url', None)
            if uri and 'youtube' in uri and hasattr(song, 'identifier'):
                thumb = f"https://img.youtube.com/vi/{song.identifier}/hqdefault.jpg"
        if thumb:
            embed.set_thumbnail(url=thumb)
        return embed

    @discord.slash_command(description="Add a track to the front of the queue and play next.")
    async def playnext(self, ctx: discord.ApplicationContext, query: str):
        await ctx.defer()
        track = await self.music.play_next(ctx, query)
        if track:
            embed = self._song_embed(track, title="Track Added to Front of Queue")
            view = QueueControlsView(self.music, ctx)
            await ctx.followup.send(embed=embed, view=view)

    @discord.slash_command(description="Shuffle the current queue.")
    async def shuffle(self, ctx: discord.ApplicationContext):
        self.music.shuffle_queue()
        embed = discord.Embed(title="Queue Shuffled", color=0x1DB954)
        view = QueueControlsView(self.music, ctx)
        await ctx.respond(embed=embed, view=view)

    @discord.slash_command(description="Show the currently playing track.")
    async def nowplaying(self, ctx: discord.ApplicationContext):
        song = self.music.get_nowplaying()
        if song:
            embed = self._song_embed(song, title="Now Playing")
            view = QueueControlsView(self.music, ctx)
            await ctx.respond(embed=embed, view=view)
        else:
            embed = discord.Embed(title="Now Playing", description="Nothing is currently playing.", color=0xED4245)
            await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(name="np", description="Alias for nowplaying.")
    async def np(self, ctx: discord.ApplicationContext):
        await self.nowplaying(ctx)

    @discord.slash_command(description="Clear the song queue (admin only).")
    async def clearqueue(self, ctx: discord.ApplicationContext):
        if not ctx.author.guild_permissions.administrator:
            embed = discord.Embed(title="Permission Denied", description="Only admins can clear the queue.", color=0xED4245)
            return await ctx.respond(embed=embed, ephemeral=True)
        self.music.clear_queue()
        embed = discord.Embed(title="Queue Cleared", color=0x1DB954)
        view = QueueControlsView(self.music, ctx)
        await ctx.respond(embed=embed, view=view)

    @discord.slash_command(description="Seek to a specific timestamp in the current track (in seconds).")
    async def seek(self, ctx: discord.ApplicationContext, seconds: int):
        ms = seconds * 1000
        ok = await self.music.seek(ms)
        if ok:
            embed = discord.Embed(title="Seeked", description=f"Seeked to {seconds} seconds.", color=0x1DB954)
            view = QueueControlsView(self.music, ctx)
            await ctx.respond(embed=embed, view=view)
        else:
            embed = discord.Embed(title="Seek Failed", description="Failed to seek. Is something playing?", color=0xED4245)
            await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(description="Save the current queue as a playlist.")
    async def saveplaylist(self, ctx: discord.ApplicationContext, name: str):
        ok = self.music.save_playlist(ctx.author.id, name, include_nowplaying=True)
        if ok:
            embed = discord.Embed(title="Playlist Saved", description=f"Playlist '{name}' saved (including current song).", color=0x1DB954)
        else:
            embed = discord.Embed(title="Playlist Not Saved", description="No songs to save in the playlist.", color=0xED4245)
        view = QueueControlsView(self.music, ctx)
        await ctx.respond(embed=embed, view=view)
    @discord.slash_command(description="Show your saved playlists.")
    async def playlists(self, ctx: discord.ApplicationContext):
        playlists = self.music.get_playlists(ctx.author.id)
        if playlists:
            desc = '\n'.join(f"- {name}" for name in playlists)
            embed = discord.Embed(title="Your Playlists", description=desc, color=0x1DB954)
        else:
            embed = discord.Embed(title="Your Playlists", description="You have no saved playlists.", color=0xED4245)
        await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(description="Delete one of your playlists by name.")
    async def deleteplaylist(self, ctx: discord.ApplicationContext, name: str):
        ok = self.music.delete_playlist(ctx.author.id, name)
        if ok:
            embed = discord.Embed(title="Playlist Deleted", description=f"Deleted playlist '{name}'.", color=0x1DB954)
        else:
            embed = discord.Embed(title="Delete Failed", description=f"No playlist named '{name}' found for you.", color=0xED4245)
        await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(description="Load a playlist into the queue.")
    async def loadplaylist(self, ctx: discord.ApplicationContext, name: str):
        await ctx.defer()
        try:
            added_tracks = await self.music.load_playlist(ctx, name, return_tracks=True)
            if added_tracks:
                desc = "\n".join([self._song_line(t, show_length=True) for t in added_tracks])
                embed = discord.Embed(title="Playlist Loaded", description=f"Loaded playlist '{name}':\n{desc}", color=0x1DB954)
            else:
                embed = discord.Embed(title="Playlist Loaded", description=f"Loaded playlist '{name}', but no tracks found.", color=0xED4245)
            view = QueueControlsView(self.music, ctx)
            await ctx.followup.send(embed=embed, view=view)
        except Exception as e:
            embed = discord.Embed(title="Playlist Load Failed", description=f"Failed to load playlist '{name}': {e}", color=0xED4245)
            await ctx.followup.send(embed=embed, ephemeral=True)

    @discord.slash_command(description="Search for tracks by name, artist, or album.")
    async def  search(self, ctx: discord.ApplicationContext, *, query: str):
        await ctx.defer()
        if not ctx.author.voice or not ctx.author.voice.channel:
            embed = discord.Embed(title="Not in Voice Channel", description="You must be in a voice channel to use this command!", color=0xED4245)
            await ctx.followup.send(embed=embed, ephemeral=True)
            return
        # If bot is not in a VC, join user's VC
        if not self.music.vc or not self.music.vc.connected:
            await self.music.join(ctx)


        # Check hardcoded map first (case-insensitive, strip)
        from core.config import HARDCODED_TRACK_MAP
        q = query.lower().strip()
        url = HARDCODED_TRACK_MAP.get(q)
        if not url:
            for k, v in HARDCODED_TRACK_MAP.items():
                if k in q:
                    url = v
                    break
        if url:
            tracks = await self.music.search_tracks(url)
            if not tracks:
                tracks = await self.music.search_tracks(query)
        else:
            tracks = await self.music.search_tracks(query)
        if not tracks:
            embed = discord.Embed(title="No Results", description=f"No results for '{query}'.", color=0xED4245)
            await ctx.followup.send(embed=embed, ephemeral=True)
            return

        def format_track(track):
            title = getattr(track, 'title', 'Unknown')
            author = getattr(track, 'author', 'Unknown')
            url = getattr(track, 'uri', None) or getattr(track, 'url', None) or "https://youtube.com"
            length = getattr(track, 'length', None)
            if length:
                mins = length // 60000
                secs = (length // 1000) % 60
                duration = f"{mins}:{secs:02d}"
            else:
                duration = "?"
            return f"[{title} - {author} - {duration}]({url})"

        options = []
        for i, t in enumerate(tracks[:10]):
            label = f"{t.title} - {getattr(t, 'author', 'Unknown')}"
            if len(label) > 95:
                label = label[:95] + "..."
            url = getattr(t, 'uri', None) or getattr(t, 'url', None) or "https://youtube.com"
            length = getattr(t, 'length', None)
            if length:
                mins = length // 60000
                secs = (length // 1000) % 60
                desc = f"{mins}:{secs:02d}"
            else:
                desc = "?"
            options.append(discord.SelectOption(label=label, description=desc, value=str(i)))

        class SearchDropdown(discord.ui.View):
            def __init__(self, music, ctx, tracks):
                super().__init__(timeout=30)
                self.music = music
                self.ctx = ctx
                self.tracks = tracks

            @discord.ui.select(placeholder="Choose a song to play", min_values=1, max_values=1, options=options)
            async def select_callback(self, select, interaction):
                idx = int(select.values[0])
                track = self.tracks[idx]
                # Play the selected track immediately
                # Clear queue and stop current
                if self.music.vc and self.music.vc.playing:
                    await self.music.vc.stop()
                self.music.queue.clear()
                self.music.queue.insert(0, track)
                await self.music.start_playback()
                embed = self.ctx.cog._song_embed(track, title="Now Playing (from Search)")
                await interaction.response.edit_message(embed=embed, view=None)

        desc = "\n".join([f"{i+1}. {format_track(t)}" for i, t in enumerate(tracks[:10])])
        embed = discord.Embed(title="Search Results", description=desc, color=0x1DB954)
        view = SearchDropdown(self.music, ctx, tracks[:10])
        await ctx.followup.send(embed=embed, view=view, ephemeral=True)


    @discord.slash_command(description="Toggle autoplay (play random/recommended track after queue ends)")
    @option("mode", choices=["on", "off"])
    async def autoplay(self, ctx: discord.ApplicationContext, mode: str):
        mode = mode.lower()
        self.music.autoplay_enabled = (mode == "on")
        embed = discord.Embed(title="Autoplay", description=f"{'Enabled' if mode == 'on' else 'Disabled'}.", color=0x1DB954)
        view = QueueControlsView(self.music, ctx)
        await ctx.respond(embed=embed, view=view)

    @discord.slash_command(description="Show last X played songs and replay")
    async def history(self, ctx: discord.ApplicationContext, count: int = 10, replay: int = None):
        # Clamp count
        count = max(1, min(count, 20))
        if not self.music.history:
            embed = discord.Embed(title="Song History", description="No song history yet.", color=0xED4245)
            await ctx.respond(embed=embed, ephemeral=True)
            return
        if replay is not None:
            idx = replay - 1
            if 0 <= idx < len(self.music.history):
                track = self.music.history[idx]
                self.music.queue.insert(0, track)
                embed = discord.Embed(title="Replayed from History", description=f"Queued **{track.title}** to play next from history.", color=0x1DB954)
                view = QueueControlsView(self.music, ctx)
                await ctx.respond(embed=embed, view=view, ephemeral=True)
                return
            else:
                embed = discord.Embed(title="Invalid Replay Number", description="Invalid song number to replay.", color=0xED4245)
                await ctx.respond(embed=embed, ephemeral=True)
                return
        # Show history
        lines = []
        for i, t in enumerate(self.music.history[-count:][::-1], 1):
            lines.append(f"{i}. {t.title} [{t.author if hasattr(t, 'author') else ''}]")
        desc = "\n".join(lines)
        embed = discord.Embed(title="Last Played Songs", description=desc, color=0x1DB954)
        view = QueueControlsView(self.music, ctx)
        await ctx.respond(embed=embed, view=view, ephemeral=True)

    @discord.slash_command(description="Toggle nightcore effect on or off")
    @option("mode", choices=["on", "off"])
    async def nightcore(self, ctx: discord.ApplicationContext, mode: str):
        mode = mode.lower()
        await self.music.set_nightcore(mode == "on")
        embed = discord.Embed(title="Nightcore", description=f"{'Enabled' if mode == 'on' else 'Disabled'}.", color=0x1DB954)
        view = QueueControlsView(self.music, ctx)
        await ctx.respond(embed=embed, view=view)

    @discord.slash_command(description="Set default volume and turn off nightcore")
    async def normalize(self, ctx: discord.ApplicationContext):
        await self.music.normalize()
        embed = discord.Embed(title="Normalized", description="Volume set to default (20%) and nightcore turned off.", color=0x1DB954)
        view = QueueControlsView(self.music, ctx)
        await ctx.respond(embed=embed, view=view)


    @discord.slash_command(description="Set bot activity mode for this server")
    @option("mode", choices=["Off", "Only on mentions", "Always"])
    async def enable(self, ctx: discord.ApplicationContext, mode: str):
        if not ctx.author.guild_permissions.administrator:
            embed = discord.Embed(title="Permission Denied", description="Only server administrators can use this command!", color=0xED4245)
            return await ctx.respond(embed=embed, ephemeral=True)
        self.memory.set_server_mode(str(ctx.guild.id), mode)
        embed = discord.Embed(title="Bot Mode Set", description=f"Bot mode set to `{mode}` for this server.", color=0x1DB954)
        await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(description="Play a song or playlist from YouTube/SoundCloud etc.")
    async def play(self, ctx: discord.ApplicationContext, query: str):
        await ctx.defer()
        if not ctx.author.voice or not ctx.author.voice.channel:
            embed = discord.Embed(title="Not in Voice Channel", description="You need to be in a voice channel first!", color=0xED4245)
            return await ctx.followup.send(embed=embed, ephemeral=True)
        track_or_playlist = await self.music.search_and_play(ctx, query, return_track=True)
        if track_or_playlist:
            if isinstance(track_or_playlist, list):
                # Playlist
                desc = "\n".join([self._song_line(t, show_length=True) for t in track_or_playlist])
                embed = discord.Embed(title="Playlist Added", description=desc, color=0x1DB954)
            else:
                embed = self._song_embed(track_or_playlist, title="Now Playing")
            view = QueueControlsView(self.music, ctx)
            await ctx.followup.send(embed=embed, view=view)

    @discord.slash_command(description="Skip the current song")
    async def skip(self, ctx: discord.ApplicationContext):
        if self.music.vc and self.music.vc.playing:
            old_song = self.music.get_nowplaying()
            await self.music.vc.stop()
            if self.music.queue:
                await self.music.start_playback()
                new_song = self.music.get_nowplaying()
                if new_song:
                    embed = discord.Embed(title="Skipped", description=f"Skipped **{getattr(old_song, 'title', 'Unknown')}**. Now playing: **{getattr(new_song, 'title', 'Unknown')}**.", color=0x1DB954)
                else:
                    embed = discord.Embed(title="Skipped", description=f"Skipped **{getattr(old_song, 'title', 'Unknown')}**. No more songs in queue.", color=0x1DB954)
            else:
                embed = discord.Embed(title="Skipped", description=f"Skipped **{getattr(old_song, 'title', 'Unknown')}**. No more songs in queue.", color=0x1DB954)
            view = QueueControlsView(self.music, ctx)
            return await ctx.respond(embed=embed, view=view)
        embed = discord.Embed(title="Skip Failed", description="Nothing is playing.", color=0xED4245)
        await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(description="Stop and disconnect")
    async def stop(self, ctx: discord.ApplicationContext):
        if self.music.vc:
            self.music.queue.clear()
            await self.music.stop(ctx)
            embed = discord.Embed(title="Stopped & Disconnected", color=0x1DB954)
            view = QueueControlsView(self.music, ctx)
            await ctx.respond(embed=embed, view=view)
        else:
            embed = discord.Embed(title="Not Connected", description="Not connected to a voice channel.", color=0xED4245)
            await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(description="Set volume (1–100)")
    async def volume(self, ctx: discord.ApplicationContext, level: int):
        if not (1 <= level <= 100):
            embed = discord.Embed(title="Invalid Volume", description="Volume must be between 1 and 100.", color=0xED4245)
            return await ctx.respond(embed=embed, ephemeral=True)
        if not self.music.vc or not self.music.vc.playing:
            embed = discord.Embed(title="Nothing Playing", description="Nothing is playing!", color=0xED4245)
            return await ctx.respond(embed=embed, ephemeral=True)
        self.music.volume = level / 100
        await self.music.vc.set_volume(level)
        embed = discord.Embed(title="Volume Set", description=f"Volume set to {level}%", color=0x1DB954)
        view = QueueControlsView(self.music, ctx)
        await ctx.respond(embed=embed, view=view)

    @discord.slash_command(description="Loop song or queue")
    @option("mode", choices=["single", "queue", "off"])
    async def loop(self, ctx: discord.ApplicationContext, mode: str):
        if not self.music.vc or not self.music.vc.connected: # Check connection
            embed = discord.Embed(title="Not Connected", description="I'm not connected to a voice channel!", color=0xED4245)
            return await ctx.respond(embed=embed, ephemeral=True)
        if not self.music.vc.playing:
            embed = discord.Embed(title="Nothing Playing", description="Nothing is currently playing!", color=0xED4245)
            return await ctx.respond(embed=embed, ephemeral=True)

        self.music.loop_mode = mode
        logger.info(f"Loop mode set to '{mode}' for MusicPlayer instance (ID: {id(self.music)})")
        embed = discord.Embed(title="Loop Mode Set", description=f"Loop mode set to `{mode}`.", color=0x1DB954)
        await ctx.respond(embed=embed)

    @discord.slash_command(description="Show the song queue")
    async def queue(self, ctx: discord.ApplicationContext):
        nowplaying = self.music.get_nowplaying()
        queue = self.music.queue
        if not nowplaying and not queue:
            embed = discord.Embed(title="Queue", description="Queue is empty.", color=0xED4245)
            return await ctx.respond(embed=embed, ephemeral=True)

        desc = ""
        if nowplaying:
            desc += f"**Now Playing:** {self._song_line(nowplaying, show_length=True)}\n\n"
        if queue:
            max_display = 15
            lines = [f"{i+1}. {self._song_line(s, show_length=True)}" for i, s in enumerate(queue[:max_display])]
            desc += "\n".join(lines)
            if len(queue) > max_display:
                desc += f"\n...and {len(queue) - max_display} more."
            total_ms = sum(getattr(s, 'length', 0) or 0 for s in queue)
            if total_ms:
                mins = total_ms // 60000
                secs = (total_ms // 1000) % 60
                desc += f"\n**Total remaining:** {mins}:{secs:02d}"
        embed = discord.Embed(title="Current Queue", description=desc, color=0x1DB954)
        view = QueueControlsView(self.music, ctx)
        await ctx.respond(embed=embed, view=view, ephemeral=True)

    @discord.slash_command(
        description="Play an audio file from your device (supports MP3, WAV, OGG, FLAC)",
        guild_ids=DISCORD_GUILD_IDS if DISCORD_GUILD_IDS else None
    )
    async def play_audio(
        self, 
        ctx: discord.ApplicationContext,
        audio_file: discord.Attachment = option(name="audio_file", description="Upload an audio file to play", required=True)
    ):
        """Play a local audio file with drag-and-drop support."""
        await ctx.defer(ephemeral=True)
        
        # Validate voice channel
        if not ctx.author.voice or not ctx.author.voice.channel:
            embed = discord.Embed(
                title="Not in Voice Channel",
                description="You must be in a voice channel to use this command!",
                color=0xED4245
            )
            await ctx.followup.send(embed=embed, ephemeral=True)
            return
        
        # Validate file type
        supported_formats = ('.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac')
        if not any(audio_file.filename.lower().endswith(fmt) for fmt in supported_formats):
            embed = discord.Embed(
                title="Unsupported Format",
                description=f"Supported formats: {', '.join(supported_formats)}",
                color=0xED4245
            )
            await ctx.followup.send(embed=embed, ephemeral=True)
            return
        
        # Validate file size (25MB limit)
        if audio_file.size > 26214400:  # 25MB in bytes
            embed = discord.Embed(
                title="File Too Large",
                description="Maximum file size is 25MB.",
                color=0xED4245
            )
            await ctx.followup.send(embed=embed, ephemeral=True)
            return
        
        try:
            # Join voice channel if not already connected
            current_vc = await self.music.join(ctx)
            if not current_vc:
                embed = discord.Embed(
                    title="Failed to Connect",
                    description="Could not connect to your voice channel.",
                    color=0xED4245
                )
                await ctx.followup.send(embed=embed, ephemeral=True)
                return
            
            self.music.vc = current_vc
            
            # Download and add audio file to queue
            track = await self.music.add_audio_file(audio_file, ctx)
            if not track:
                embed = discord.Embed(
                    title="Error",
                    description="Failed to process audio file.",
                    color=0xED4245
                )
                await ctx.followup.send(embed=embed, ephemeral=True)
                return
            
            if not self.music.vc.playing and not self.music.queue:
                await self.music.start_playback()
            
            embed = discord.Embed(
                title="🎵 Added to Queue",
                description=f"**{audio_file.filename}** has been added to the queue.",
                color=0x1DB954
            )
            embed.set_footer(text=f"Queued by {ctx.author.name}")
            await ctx.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in play_audio command: {e}", exc_info=True)
            embed = discord.Embed(
                title="Error",
                description=f"An error occurred: {str(e)[:100]}",
                color=0xED4245
            )
            await ctx.followup.send(embed=embed, ephemeral=True)

def setup(bot):
    bot.add_cog(CommandsCog(bot))
