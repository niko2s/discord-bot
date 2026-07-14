# Music Commands

Join a voice channel before using a music command. The bot joins your channel when you use `/play` or `/search`; other playback commands require you to be in the same voice channel as the bot.

## Start listening

| Command | Description |
|---|---|
| `/play query` | Play a URL or search YouTube. If nothing is playing, playback starts immediately; otherwise the track is added to the queue. |
| `/search query [source]` | Search YouTube, YouTube Music, or SoundCloud and choose from the top five results. |
| `/player` | Post a live player panel with playback controls. |

## Playback controls

| Command | Description |
|---|---|
| `/pause` | Pause the current track. |
| `/resume` | Resume the current track. |
| `/skip` | Skip to the next track. |
| `/stop` | Stop playback and clear the queue. |
| `/seek position` | Jump to a position such as `45`, `1:23`, or `1:02:30`. |
| `/replay` | Restart the current track. |
| `/volume level` | Set the volume from 0 to 1000 percent. |
| `/bassboost` | Toggle the bass boost filter. |
| `/nightcore` | Toggle the nightcore filter. |
| `/disconnect` | Clear the queue and make the bot leave the voice channel. |

## Queue controls

| Command | Description |
|---|---|
| `/queue` | Show the current track and up to 10 upcoming tracks. |
| `/loop mode` | Set looping to off, the current track, or the full queue. |
| `/shuffle` | Shuffle the upcoming tracks. |
| `/clear` | Clear the queue without stopping the current track. |
| `/remove position` | Remove a queued track by its position; `1` is the next track. |

## Track information

| Command | Description |
|---|---|
| `/nowplaying` | Show the current track, progress, loop mode, and volume. |
| `/grab` | Send the current track's link to you in a direct message. |
| `/musichelp` | Show a compact list of music commands in Discord. |

## Automatic disconnects

The bot leaves after the queue has been idle for five minutes. It also leaves after one minute when no non-bot users remain in its voice channel.
