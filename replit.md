# USO NFL Bot

A Discord bot with live NFL scores, player stats, game schedules, standings, news, and more.

## Architecture

- **Language**: Python 3.11
- **Framework**: discord.py with slash commands (app_commands)
- **Data Source**: ESPN public API (no API key required)

## Project Structure

```
bot.py          - Main bot entry point
nfl_api.py      - ESPN API wrapper functions
cogs/
  nfl.py        - NFL commands cog (slash commands)
```

## Commands

- `/scores` - Live NFL scores and today's games
- `/standings` - Current NFL standings by division
- `/news` - Latest NFL news headlines
- `/team <abbr>` - Info about a specific NFL team
- `/schedule <abbr>` - Upcoming schedule for a team
- `/help` - Show all commands

## Setup

1. Create a Discord bot at https://discord.com/developers/applications
2. Enable the "Message Content Intent" in the bot settings
3. Set the `DISCORD_TOKEN` environment variable/secret
4. Invite the bot to your server with the `applications.commands` scope

## Dependencies

- discord.py
- aiohttp
- requests
- python-dotenv
