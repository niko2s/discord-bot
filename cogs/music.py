"""
Music cog backed by Lavalink (lavalink.py 5.x).

Run a Lavalink server alongside the bot (Lavalink.jar + application.yaml in the
repo root) before loading this cog. Connection settings are read from env vars
LAVALINK_HOST / LAVALINK_PORT / LAVALINK_PASSWORD / LAVALINK_REGION and fall
back to the local defaults.
"""
from __future__ import annotations

import asyncio
import logging
import os
import random
import re

import discord
import lavalink
from discord import app_commands
from discord.ext import commands
from lavalink.errors import ClientError
from lavalink.events import (
    QueueEndEvent,
    TrackExceptionEvent,
    TrackStartEvent,
    TrackStuckEvent,
)
from lavalink.filters import Equalizer, Timescale
from lavalink.server import LoadType


LOOP_NONE = 0
LOOP_TRACK = 1
LOOP_QUEUE = 2
LOOP_LABELS = {LOOP_NONE: "off", LOOP_TRACK: "track", LOOP_QUEUE: "queue"}

ALONE_DISCONNECT_DELAY = 60  # seconds the bot waits alone in a VC before leaving
IDLE_DISCONNECT_DELAY = 300  # seconds after queue ends before the bot leaves on its own

BASSBOOST_BANDS = [(0, 0.25), (1, 0.20), (2, 0.15), (3, 0.10)]
NIGHTCORE_SPEED = 1.2
NIGHTCORE_PITCH = 1.2


log = logging.getLogger(__name__)

URL_RX = re.compile(r"https?://(?:www\.)?.+")

LAVALINK_HOST = os.environ.get("LAVALINK_HOST", "localhost")
LAVALINK_PORT = int(os.environ.get("LAVALINK_PORT", "2333"))
LAVALINK_PASSWORD = os.environ.get("LAVALINK_PASSWORD", "youshallnotpass")
LAVALINK_REGION = os.environ.get("LAVALINK_REGION", "us")


def _format_ms(ms: int) -> str:
    seconds, _ = divmod(int(ms), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


_SOURCE_THEMES = {
    "youtube": ("▶️", discord.Color.from_rgb(255, 0, 0)),
    "youtube_music": ("▶️", discord.Color.from_rgb(255, 0, 0)),
    "soundcloud": ("🟧", discord.Color.from_rgb(255, 119, 0)),
    "bandcamp": ("🎵", discord.Color.from_rgb(96, 158, 175)),
    "twitch": ("📺", discord.Color.from_rgb(145, 71, 255)),
    "vimeo": ("🎬", discord.Color.from_rgb(26, 183, 234)),
    "http": ("🔗", discord.Color.greyple()),
}


def _source_theme(track) -> tuple[str, discord.Color]:
    return _SOURCE_THEMES.get(track.source_name, ("🎵", discord.Color.blurple()))


def _progress_bar(position_ms: int, duration_ms: int, length: int = 18) -> str:
    if duration_ms <= 0:
        return ""
    filled = max(0, min(length - 1, int(length * position_ms / duration_ms)))
    return "▬" * filled + "🔘" + "▬" * (length - filled - 1)


def _track_embed(
    track,
    *,
    title_prefix: str,
    position_ms: int | None = None,
    extra_footer: str | None = None,
) -> discord.Embed:
    emoji, color = _source_theme(track)
    embed = discord.Embed(
        title=f"{emoji} {title_prefix}",
        description=f"**[{track.title}]({track.uri})**\nby {track.author}",
        color=color,
    )
    if track.artwork_url:
        embed.set_thumbnail(url=track.artwork_url)

    if track.is_stream:
        embed.add_field(name="Live", value="🔴 Streaming", inline=True)
    elif position_ms is not None and track.duration:
        bar = _progress_bar(position_ms, track.duration)
        embed.add_field(
            name="​",
            value=f"{bar}\n`{_format_ms(position_ms)} / {_format_ms(track.duration)}`",
            inline=False,
        )
    else:
        embed.add_field(name="Duration", value=_format_ms(track.duration), inline=True)

    if extra_footer:
        embed.set_footer(text=extra_footer)
    return embed


class LavalinkVoiceClient(discord.VoiceProtocol):
    """Bridges discord.py's voice protocol with the Lavalink player."""

    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        self.client = client
        self.channel = channel
        self.guild_id = channel.guild.id
        self._destroyed = False
        # The cog (or whoever owns the client) attaches `lavalink` to bot.
        self.lavalink: lavalink.Client = client.lavalink

    async def on_voice_server_update(self, data):
        await self.lavalink.voice_update_handler({"t": "VOICE_SERVER_UPDATE", "d": data})

    async def on_voice_state_update(self, data):
        channel_id = data["channel_id"]
        if not channel_id:
            await self._destroy()
            return
        self.channel = self.client.get_channel(int(channel_id))
        await self.lavalink.voice_update_handler({"t": "VOICE_STATE_UPDATE", "d": data})

    async def connect(
        self,
        *,
        timeout: float,
        reconnect: bool,
        self_deaf: bool = True,
        self_mute: bool = False,
    ) -> None:
        self.lavalink.player_manager.create(guild_id=self.channel.guild.id)
        await self.channel.guild.change_voice_state(
            channel=self.channel, self_mute=self_mute, self_deaf=self_deaf
        )

    async def disconnect(self, *, force: bool = False) -> None:
        player = self.lavalink.player_manager.get(self.channel.guild.id)
        if not force and (player is None or not player.is_connected):
            return
        await self.channel.guild.change_voice_state(channel=None)
        if player is not None:
            player.channel_id = None
        await self._destroy()

    async def _destroy(self):
        self.cleanup()
        if self._destroyed:
            return
        self._destroyed = True
        try:
            await self.lavalink.player_manager.destroy(self.guild_id)
        except ClientError:
            pass


class PlayerPanel:
    """Self-refreshing now-playing message in a single channel per guild."""

    REFRESH_SECONDS = 5

    def __init__(
        self,
        cog: "Music",
        guild_id: int,
        message: discord.Message,
    ):
        self.cog = cog
        self.guild_id = guild_id
        self.message = message
        self.view: PlayerControls | None = None
        self.task = asyncio.create_task(self._loop(), name=f"PlayerPanel-{guild_id}")

    async def _loop(self):
        try:
            while True:
                await asyncio.sleep(self.REFRESH_SECONDS)
                if not await self._render():
                    return
        except asyncio.CancelledError:
            pass

    async def _render(self) -> bool:
        """Render the current state. Returns False to end the loop."""
        player = self.cog.lavalink.player_manager.get(self.guild_id)
        if player is None or player.current is None:
            await self._render_idle()
            return False

        if self.view is None:
            self.view = PlayerControls(self.cog, self.guild_id, timeout=None)

        try:
            await self.message.edit(embed=self._build_embed(player), view=self.view)
        except discord.NotFound:
            self.cog._panels.pop(self.guild_id, None)
            return False
        except discord.HTTPException:
            log.exception("Panel edit failed")
        return True

    async def _render_idle(self):
        embed = discord.Embed(
            title="🎵 Player idle",
            description="Queue is empty. Run `/play` to start something.",
            color=discord.Color.greyple(),
        )
        try:
            await self.message.edit(embed=embed, view=None)
        except discord.HTTPException:
            pass
        if self.view is not None:
            self.view.stop()
        self.cog._panels.pop(self.guild_id, None)

    def _build_embed(self, player) -> discord.Embed:
        track = player.current
        loop_label = LOOP_LABELS.get(player.loop, "off")
        state = "⏸ Paused" if player.paused else "▶ Playing"
        bits = [state, f"loop: {loop_label}", f"vol: {player.volume}%"]
        if player.queue:
            bits.append(f"up next: {len(player.queue)}")
        return _track_embed(
            track,
            title_prefix="Live player",
            position_ms=player.position,
            extra_footer=" • ".join(bits),
        )

    def cancel(self):
        if not self.task.done():
            self.task.cancel()
        if self.view is not None:
            self.view.stop()


class PlayerControls(discord.ui.View):
    """Button row attached to the now-playing message or the live panel."""

    def __init__(self, cog: "Music", guild_id: int, *, timeout: float | None = 600):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.guild_id = guild_id

    async def _gate(self, interaction: discord.Interaction) -> "lavalink.DefaultPlayer | None":
        """Reject if the user isn't in the bot's VC; return the player otherwise."""
        guild = interaction.guild
        if guild is None:
            return None
        voice = guild.voice_client
        user_voice = interaction.user.voice
        if voice is None or user_voice is None or user_voice.channel != voice.channel:
            await interaction.response.send_message(
                "Join my voice channel to control playback.", ephemeral=True
            )
            return None
        return self.cog.lavalink.player_manager.get(self.guild_id)

    @discord.ui.button(emoji="⏯️", style=discord.ButtonStyle.primary)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = await self._gate(interaction)
        if player is None:
            return
        if player.current is None:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return
        await player.set_pause(not player.paused)
        await interaction.response.send_message(
            "⏸ Paused." if player.paused else "▶ Resumed.", ephemeral=True
        )

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = await self._gate(interaction)
        if player is None:
            return
        if player.current is None:
            await interaction.response.send_message("Nothing to skip.", ephemeral=True)
            return
        await player.skip()
        await interaction.response.send_message("⏭ Skipped.", ephemeral=True)

    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.secondary)
    async def loop_cycle(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = await self._gate(interaction)
        if player is None:
            return
        next_mode = (player.loop + 1) % 3
        player.set_loop(next_mode)
        await interaction.response.send_message(
            f"🔁 Loop: **{LOOP_LABELS[next_mode]}**.", ephemeral=True
        )

    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary)
    async def shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = await self._gate(interaction)
        if player is None:
            return
        if not player.queue:
            await interaction.response.send_message("Queue is empty.", ephemeral=True)
            return
        random.shuffle(player.queue)
        await interaction.response.send_message(
            f"🔀 Shuffled **{len(player.queue)}** tracks.", ephemeral=True
        )

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = await self._gate(interaction)
        if player is None:
            return
        player.queue.clear()
        await player.stop()
        if interaction.guild.voice_client is not None:
            await interaction.guild.voice_client.disconnect(force=True)
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send("⏹ Stopped and disconnected.", ephemeral=True)


class SearchView(discord.ui.View):
    """Dropdown picker bound to the user who triggered /search."""

    def __init__(
        self,
        cog: "Music",
        owner_id: int,
        tracks: list,
    ):
        super().__init__(timeout=60)
        self.cog = cog
        self.owner_id = owner_id
        self.tracks = tracks
        self.add_item(self._build_select())

    def _build_select(self) -> discord.ui.Select:
        options = [
            discord.SelectOption(
                label=(t.title[:97] + "…") if len(t.title) > 100 else t.title,
                description=f"{t.author} • {_format_ms(t.duration)}"[:100],
                value=str(i),
            )
            for i, t in enumerate(self.tracks)
        ]
        select = discord.ui.Select(placeholder="Pick a track…", options=options)
        select.callback = self._on_select
        return select

    async def _on_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "Only the user who ran /search can pick.", ephemeral=True
            )
            return

        index = int(interaction.data["values"][0])
        track = self.tracks[index]

        try:
            player = await self.cog._ensure_voice(interaction, should_connect=True)
        except app_commands.AppCommandError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        player.add(track=track, requester=interaction.user.id)

        embed = _track_embed(track, title_prefix="Track enqueued")
        # Disable the dropdown after selection.
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

        if not player.is_playing:
            await player.play()


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        if not hasattr(bot, "lavalink"):
            bot.lavalink = lavalink.Client(bot.user.id)
            bot.lavalink.add_node(
                host=LAVALINK_HOST,
                port=LAVALINK_PORT,
                password=LAVALINK_PASSWORD,
                region=LAVALINK_REGION,
                name="default-node",
            )

        self.lavalink: lavalink.Client = bot.lavalink
        self.lavalink.add_event_hooks(self)
        self._panels: dict[int, PlayerPanel] = {}
        self._idle_tasks: dict[int, asyncio.Task] = {}

    def cog_unload(self):
        for panel in list(self._panels.values()):
            panel.cancel()
        self._panels.clear()
        for task in self._idle_tasks.values():
            task.cancel()
        self._idle_tasks.clear()
        self.lavalink._event_hooks.clear()

    def _cancel_idle_timer(self, guild_id: int):
        task = self._idle_tasks.pop(guild_id, None)
        if task is not None and not task.done():
            task.cancel()

    async def _idle_disconnect(self, guild_id: int):
        try:
            await asyncio.sleep(IDLE_DISCONNECT_DELAY)
        except asyncio.CancelledError:
            return
        # Re-check: a new track may have started, or someone may have disconnected manually.
        player = self.lavalink.player_manager.get(guild_id)
        if player is not None and player.current is not None:
            return
        guild = self.bot.get_guild(guild_id)
        if guild is None or guild.voice_client is None:
            return
        await guild.voice_client.disconnect(force=True)
        panel = self._panels.get(guild_id)
        if panel is not None:
            await panel._render_idle()
        await self.bot.change_presence(activity=None)
        self._idle_tasks.pop(guild_id, None)

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        original = getattr(error, "original", error)
        message = str(original) or "Something went wrong."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    async def _ensure_voice(
        self, interaction: discord.Interaction, *, should_connect: bool
    ) -> lavalink.DefaultPlayer:
        """Verify the user/bot voice state and return a ready player."""
        if interaction.guild is None:
            raise app_commands.AppCommandError("This command only works in a server.")

        user_voice = interaction.user.voice
        if user_voice is None or user_voice.channel is None:
            raise app_commands.AppCommandError("Join a voice channel first.")

        voice_client: LavalinkVoiceClient | None = interaction.guild.voice_client  # type: ignore[assignment]
        voice_channel = user_voice.channel

        if voice_client is None:
            if not should_connect:
                raise app_commands.AppCommandError("I'm not in a voice channel.")

            permissions = voice_channel.permissions_for(interaction.guild.me)
            if not permissions.connect or not permissions.speak:
                raise app_commands.AppCommandError(
                    "I need the `Connect` and `Speak` permissions in your voice channel."
                )
            if (
                voice_channel.user_limit
                and len(voice_channel.members) >= voice_channel.user_limit
                and not interaction.guild.me.guild_permissions.move_members
            ):
                raise app_commands.AppCommandError("Your voice channel is full.")

            player = self.lavalink.player_manager.create(interaction.guild.id)
            player.store("channel", interaction.channel.id)
            await voice_channel.connect(cls=LavalinkVoiceClient, self_deaf=True)
        elif voice_client.channel.id != voice_channel.id:
            raise app_commands.AppCommandError("You must be in my voice channel.")

        return self.lavalink.player_manager.get(interaction.guild.id)

    # ---------------------------------------------------------------- events
    @lavalink.listener(TrackStartEvent)
    async def on_track_start(self, event: TrackStartEvent):
        track = event.track
        # If we were about to leave because the queue had ended, cancel that.
        self._cancel_idle_timer(event.player.guild_id)
        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=track.title[:128],
            )
        )

        guild = self.bot.get_guild(event.player.guild_id)
        if guild is None:
            await self.lavalink.player_manager.destroy(event.player.guild_id)
            return
        channel_id = event.player.fetch("channel")
        channel = guild.get_channel(channel_id) if channel_id else None
        if channel is None:
            return

        # If a live panel is active in this guild, skip the per-track announcement
        # — the panel already shows current state and refreshes itself.
        if guild.id in self._panels:
            return

        requester = guild.get_member(track.requester) if track.requester else None
        footer = f"Requested by {requester.display_name}" if requester else None
        embed = _track_embed(track, title_prefix="Now playing", extra_footer=footer)
        view = PlayerControls(self, guild.id, timeout=max(60.0, track.duration / 1000 + 30))
        try:
            await channel.send(embed=embed, view=view)
        except discord.HTTPException:
            log.exception("Failed to send now-playing message")

    @lavalink.listener(QueueEndEvent)
    async def on_queue_end(self, event: QueueEndEvent):
        await self.bot.change_presence(activity=None)
        panel = self._panels.get(event.player.guild_id)
        if panel is not None:
            await panel._render_idle()
        # Stay in voice for IDLE_DISCONNECT_DELAY seconds so a quick /play resumes
        # without the bot leaving and rejoining.
        self._cancel_idle_timer(event.player.guild_id)
        self._idle_tasks[event.player.guild_id] = asyncio.create_task(
            self._idle_disconnect(event.player.guild_id),
            name=f"idle-disconnect-{event.player.guild_id}",
        )

    @lavalink.listener(TrackExceptionEvent)
    async def on_track_exception(self, event: TrackExceptionEvent):
        log.warning(
            "Lavalink track exception in guild %s: %s (severity=%s) — %s",
            event.player.guild_id,
            event.message,
            event.severity,
            event.cause,
        )

    @lavalink.listener(TrackStuckEvent)
    async def on_track_stuck(self, event: TrackStuckEvent):
        log.warning("Lavalink track stuck in guild %s, skipping", event.player.guild_id)
        await event.player.skip()

    # -------------------------------------------------------------- commands
    @app_commands.command(name="play", description="Play a song from a URL or search query")
    @app_commands.describe(query="A YouTube URL, other supported URL, or a search query")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        player = await self._ensure_voice(interaction, should_connect=True)

        query = query.strip("<>")
        if not URL_RX.match(query):
            query = f"ytsearch:{query}"

        results = await player.node.get_tracks(query)

        if results.load_type == LoadType.EMPTY:
            await interaction.followup.send("No tracks found for that query.")
            return
        if results.load_type == LoadType.ERROR:
            await interaction.followup.send(
                f"Failed to load track: {results.error.message}"
            )
            return

        if results.load_type == LoadType.PLAYLIST:
            for track in results.tracks:
                player.add(track=track, requester=interaction.user.id)
            total_ms = sum(t.duration for t in results.tracks if not t.is_stream)
            embed = discord.Embed(
                title="📃 Playlist enqueued",
                description=f"**{results.playlist_info.name}**\n{len(results.tracks)} tracks • {_format_ms(total_ms)}",
                color=discord.Color.blurple(),
            )
        else:
            track = results.tracks[0]
            player.add(track=track, requester=interaction.user.id)
            position_in_queue = len(player.queue) if player.is_playing else 0
            footer = (
                f"Up next (#{position_in_queue})" if position_in_queue > 0 else "Starting now"
            )
            embed = _track_embed(track, title_prefix="Track enqueued", extra_footer=footer)

        await interaction.followup.send(embed=embed)

        if not player.is_playing:
            await player.play()

    @app_commands.command(name="pause", description="Pause the current track")
    async def pause(self, interaction: discord.Interaction):
        player = await self._ensure_voice(interaction, should_connect=False)
        if not player.is_playing:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return
        await player.set_pause(True)
        await interaction.response.send_message("⏸ Paused.")

    @app_commands.command(name="resume", description="Resume the current track")
    async def resume(self, interaction: discord.Interaction):
        player = await self._ensure_voice(interaction, should_connect=False)
        if not player.paused:
            await interaction.response.send_message("Nothing is paused.", ephemeral=True)
            return
        await player.set_pause(False)
        await interaction.response.send_message("▶ Resumed.")

    @app_commands.command(name="skip", description="Skip the current track")
    async def skip(self, interaction: discord.Interaction):
        player = await self._ensure_voice(interaction, should_connect=False)
        if not player.is_playing:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return
        await player.skip()
        await interaction.response.send_message("⏭ Skipped.")

    @app_commands.command(name="stop", description="Stop playback and clear the queue")
    async def stop(self, interaction: discord.Interaction):
        player = await self._ensure_voice(interaction, should_connect=False)
        player.queue.clear()
        await player.stop()
        await interaction.response.send_message("⏹ Stopped and cleared the queue.")

    @app_commands.command(name="nowplaying", description="Show the current track")
    async def nowplaying(self, interaction: discord.Interaction):
        player = self.lavalink.player_manager.get(interaction.guild.id)
        if player is None or player.current is None:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return
        track = player.current
        loop_label = LOOP_LABELS.get(player.loop, "off")
        state = "⏸ Paused" if player.paused else "▶ Playing"
        footer_bits = [state, f"loop: {loop_label}", f"vol: {player.volume}%"]
        if track.requester:
            requester = interaction.guild.get_member(track.requester)
            if requester:
                footer_bits.append(f"req: {requester.display_name}")
        embed = _track_embed(
            track,
            title_prefix="Now playing",
            position_ms=player.position,
            extra_footer=" • ".join(footer_bits),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="queue", description="Show the upcoming tracks")
    async def queue(self, interaction: discord.Interaction):
        player = self.lavalink.player_manager.get(interaction.guild.id)
        if player is None or (not player.queue and player.current is None):
            await interaction.response.send_message("The queue is empty.", ephemeral=True)
            return

        emoji, color = _source_theme(player.current) if player.current else ("🎵", discord.Color.blurple())
        embed = discord.Embed(title=f"{emoji} Queue", color=color)

        if player.current is not None:
            t = player.current
            state = "⏸" if player.paused else "▶"
            embed.add_field(
                name="Now playing",
                value=(
                    f"{state} **[{t.title}]({t.uri})**\n"
                    f"`{_format_ms(player.position)} / {_format_ms(t.duration)}` • by {t.author}"
                ),
                inline=False,
            )
        if player.queue:
            upcoming = "\n".join(
                f"`{i + 1}.` [{t.title}]({t.uri}) — `{_format_ms(t.duration)}`"
                for i, t in enumerate(player.queue[:10])
            )
            extra = len(player.queue) - 10
            if extra > 0:
                upcoming += f"\n…and **{extra}** more"
            total_ms = sum(t.duration for t in player.queue if not t.is_stream)
            embed.add_field(
                name=f"Up next — {len(player.queue)} tracks • {_format_ms(total_ms)}",
                value=upcoming,
                inline=False,
            )
        loop_label = LOOP_LABELS.get(player.loop, "off")
        embed.set_footer(text=f"loop: {loop_label} • vol: {player.volume}%")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="volume", description="Set the playback volume (0-1000)")
    @app_commands.describe(level="Volume percentage (default 100, max 1000)")
    async def volume(
        self,
        interaction: discord.Interaction,
        level: app_commands.Range[int, 0, 1000],
    ):
        player = await self._ensure_voice(interaction, should_connect=False)
        await player.set_volume(level)
        await interaction.response.send_message(f"🔊 Volume set to **{level}%**.")

    @app_commands.command(name="disconnect", description="Disconnect and clear the queue")
    async def disconnect(self, interaction: discord.Interaction):
        player = await self._ensure_voice(interaction, should_connect=False)
        player.queue.clear()
        await player.stop()
        self._cancel_idle_timer(interaction.guild.id)
        if interaction.guild.voice_client is not None:
            await interaction.guild.voice_client.disconnect(force=True)
        panel = self._panels.get(interaction.guild.id)
        if panel is not None:
            await panel._render_idle()
        await self.bot.change_presence(activity=None)
        await interaction.response.send_message("👋 Disconnected.")

    @app_commands.command(name="player", description="Post a live, self-updating player panel in this channel")
    async def player(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "This command only works in a server.", ephemeral=True
            )
            return

        # Replace any existing panel in this guild.
        existing = self._panels.pop(interaction.guild.id, None)
        if existing is not None:
            existing.cancel()
            try:
                await existing.message.delete()
            except discord.HTTPException:
                pass

        embed = discord.Embed(
            title="🎵 Live player",
            description="Loading…",
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()

        panel = PlayerPanel(self, interaction.guild.id, message)
        self._panels[interaction.guild.id] = panel
        # Render once immediately so the user doesn't wait 5s.
        await panel._render()

    @app_commands.command(name="search", description="Search and pick from the top results")
    @app_commands.describe(query="What to search for", source="Where to search (default: YouTube)")
    @app_commands.choices(
        source=[
            app_commands.Choice(name="YouTube", value="ytsearch"),
            app_commands.Choice(name="YouTube Music", value="ytmsearch"),
            app_commands.Choice(name="SoundCloud", value="scsearch"),
        ]
    )
    async def search(
        self,
        interaction: discord.Interaction,
        query: str,
        source: app_commands.Choice[str] | None = None,
    ):
        await interaction.response.defer()
        # Validate voice up-front so we don't show results we can't enqueue.
        await self._ensure_voice(interaction, should_connect=True)
        node = self.lavalink.player_manager.get(interaction.guild.id).node

        prefix = source.value if source else "ytsearch"
        source_label = source.name if source else "YouTube"

        results = await node.get_tracks(f"{prefix}:{query}")
        if results.load_type in (LoadType.EMPTY, LoadType.ERROR) or not results.tracks:
            await interaction.followup.send(f"No results on {source_label} for `{query}`.")
            return

        top = results.tracks[:5]
        embed = discord.Embed(
            title=f"{source_label} results for: {query}",
            description="\n".join(
                f"`{i + 1}.` [{t.title}]({t.uri}) — {_format_ms(t.duration)}"
                for i, t in enumerate(top)
            ),
            color=discord.Color.blurple(),
        )
        view = SearchView(self, interaction.user.id, top)
        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(name="seek", description="Seek to a position in the current track")
    @app_commands.describe(position="Position like 1:23, 45, or 1:02:30")
    async def seek(self, interaction: discord.Interaction, position: str):
        player = await self._ensure_voice(interaction, should_connect=False)
        if player.current is None:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return

        ms = _parse_position(position)
        if ms is None:
            await interaction.response.send_message(
                "Position must look like `45`, `1:23`, or `1:02:30`.", ephemeral=True
            )
            return
        ms = max(0, min(ms, player.current.duration))

        await player.seek(ms)
        await interaction.response.send_message(f"⏩ Seeked to **{_format_ms(ms)}**.")

    @app_commands.command(name="replay", description="Restart the current track from the beginning")
    async def replay(self, interaction: discord.Interaction):
        player = await self._ensure_voice(interaction, should_connect=False)
        if player.current is None:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return
        await player.seek(0)
        await interaction.response.send_message("🔁 Replaying from the start.")

    @app_commands.command(name="loop", description="Set the loop mode")
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="Off", value=LOOP_NONE),
            app_commands.Choice(name="Track", value=LOOP_TRACK),
            app_commands.Choice(name="Queue", value=LOOP_QUEUE),
        ]
    )
    async def loop(
        self,
        interaction: discord.Interaction,
        mode: app_commands.Choice[int],
    ):
        player = await self._ensure_voice(interaction, should_connect=False)
        player.set_loop(mode.value)
        await interaction.response.send_message(
            f"🔁 Loop mode: **{LOOP_LABELS[mode.value]}**."
        )

    @app_commands.command(name="shuffle", description="Shuffle the upcoming queue")
    async def shuffle(self, interaction: discord.Interaction):
        player = await self._ensure_voice(interaction, should_connect=False)
        if not player.queue:
            await interaction.response.send_message("Queue is empty.", ephemeral=True)
            return
        random.shuffle(player.queue)
        await interaction.response.send_message(f"🔀 Shuffled **{len(player.queue)}** tracks.")

    @app_commands.command(name="clear", description="Clear the queue (keeps current track playing)")
    async def clear(self, interaction: discord.Interaction):
        player = await self._ensure_voice(interaction, should_connect=False)
        count = len(player.queue)
        player.queue.clear()
        await interaction.response.send_message(f"🧹 Cleared **{count}** queued tracks.")

    @app_commands.command(name="remove", description="Remove a track from the queue by position")
    @app_commands.describe(position="Position in the queue (1 = next up)")
    async def remove(
        self,
        interaction: discord.Interaction,
        position: app_commands.Range[int, 1, 1000],
    ):
        player = await self._ensure_voice(interaction, should_connect=False)
        if position > len(player.queue):
            await interaction.response.send_message(
                f"Queue only has **{len(player.queue)}** tracks.", ephemeral=True
            )
            return
        track = player.queue.pop(position - 1)
        await interaction.response.send_message(
            f"❌ Removed `{position}.` [{track.title}]({track.uri})"
        )

    @app_commands.command(name="grab", description="DM yourself the link to the current track")
    async def grab(self, interaction: discord.Interaction):
        player = self.lavalink.player_manager.get(interaction.guild.id)
        if player is None or player.current is None:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return
        track = player.current
        embed = discord.Embed(
            title=track.title,
            url=track.uri,
            description=f"by {track.author} • {_format_ms(track.duration)}",
            color=discord.Color.blurple(),
        )
        try:
            await interaction.user.send(embed=embed)
            await interaction.response.send_message("📬 Sent you a DM.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(
                "I can't DM you — check your privacy settings.", ephemeral=True
            )

    @app_commands.command(name="bassboost", description="Toggle the bass boost filter")
    async def bassboost(self, interaction: discord.Interaction):
        player = await self._ensure_voice(interaction, should_connect=False)
        if player.fetch("bassboost"):
            await player.remove_filter("equalizer")
            player.store("bassboost", False)
            await interaction.response.send_message("🎚 Bass boost **off**.")
        else:
            eq = Equalizer()
            eq.update(bands=BASSBOOST_BANDS)
            await player.set_filter(eq)
            player.store("bassboost", True)
            await interaction.response.send_message("🔊 Bass boost **on**.")

    @app_commands.command(name="nightcore", description="Toggle the nightcore filter")
    async def nightcore(self, interaction: discord.Interaction):
        player = await self._ensure_voice(interaction, should_connect=False)
        if player.fetch("nightcore"):
            await player.remove_filter("timescale")
            player.store("nightcore", False)
            await interaction.response.send_message("🎚 Nightcore **off**.")
        else:
            ts = Timescale()
            ts.update(speed=NIGHTCORE_SPEED, pitch=NIGHTCORE_PITCH)
            await player.set_filter(ts)
            player.store("nightcore", True)
            await interaction.response.send_message("🌙 Nightcore **on**.")

    @app_commands.command(name="musichelp", description="List all music commands")
    async def musichelp(self, interaction: discord.Interaction):
        commands_list = [
            ("/play", "Play a song from a URL or search query"),
            ("/player", "Post a live, self-updating player panel"),
            ("/search", "Search and pick from a list of results"),
            ("/pause", "Pause the current track"),
            ("/resume", "Resume playback"),
            ("/skip", "Skip to the next track"),
            ("/stop", "Stop and clear the queue"),
            ("/seek", "Jump to a position in the current track"),
            ("/replay", "Restart the current track"),
            ("/loop", "Set loop mode (off / track / queue)"),
            ("/shuffle", "Shuffle the upcoming queue"),
            ("/clear", "Clear the queue (keeps playing)"),
            ("/remove", "Remove a track by queue position"),
            ("/queue", "Show the upcoming tracks"),
            ("/nowplaying", "Show the current track"),
            ("/grab", "DM yourself a link to the current track"),
            ("/volume", "Set the playback volume (0–1000)"),
            ("/bassboost", "Toggle the bass boost filter"),
            ("/nightcore", "Toggle the nightcore filter"),
            ("/disconnect", "Leave the voice channel"),
        ]
        embed = discord.Embed(
            title="🎵 Music commands",
            description="\n".join(f"**{name}** — {desc}" for name, desc in commands_list),
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ------------------------------------------------ auto-leave when alone
    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if member.bot:
            return
        voice_client = member.guild.voice_client
        if not isinstance(voice_client, LavalinkVoiceClient):
            return
        bot_channel = voice_client.channel
        # Only act if the user left or arrived at the bot's channel.
        if before.channel != bot_channel and after.channel != bot_channel:
            return
        if any(not m.bot for m in bot_channel.members):
            return

        await asyncio.sleep(ALONE_DISCONNECT_DELAY)

        # Re-check after the grace period — someone may have rejoined.
        voice_client = member.guild.voice_client
        if not isinstance(voice_client, LavalinkVoiceClient):
            return
        if any(not m.bot for m in voice_client.channel.members):
            return

        player = self.lavalink.player_manager.get(member.guild.id)
        if player is not None:
            player.queue.clear()
            await player.stop()
        await voice_client.disconnect(force=True)


def _parse_position(value: str) -> int | None:
    """Parse '45', '1:23', '1:02:30' (or with .ms) into milliseconds. Returns None on invalid input."""
    parts = value.strip().split(":")
    if not 1 <= len(parts) <= 3:
        return None
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        return None
    if any(n < 0 for n in nums):
        return None
    seconds = 0.0
    for n in nums:
        seconds = seconds * 60 + n
    return int(seconds * 1000)


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
