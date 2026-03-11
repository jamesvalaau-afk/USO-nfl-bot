import aiohttp
import json


ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
ESPN_CORE = "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl"


async def get_scoreboard():
    url = f"{ESPN_BASE}/scoreboard"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
    return None


async def get_standings():
    url = f"{ESPN_BASE}/standings"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
    return None


async def search_player(name: str):
    url = f"{ESPN_BASE}/athletes"
    params = {"limit": 5, "search": name}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                return await resp.json()
    return None


async def get_team_info(team_abbr: str):
    url = f"{ESPN_BASE}/teams/{team_abbr.lower()}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
    return None


async def get_news():
    url = f"{ESPN_BASE}/news"
    params = {"limit": 5}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                return await resp.json()
    return None


async def get_schedule(team_abbr: str = None):
    if team_abbr:
        url = f"{ESPN_BASE}/teams/{team_abbr.lower()}/schedule"
    else:
        url = f"{ESPN_BASE}/scoreboard"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
    return None
