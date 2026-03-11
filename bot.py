import os
import aiohttp
import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime

TOKEN = os.getenv("DISCORD_TOKEN")

# Put your channel IDs here if you want auto-posting
SCORES_CHANNEL_ID = 0
NEWS_CHANNEL_ID = 0
ALERTS_CHANNEL_ID = 0

ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
ESPN_NEWS_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/news"
ESPN_SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={event_id}"
ESPN_ATHLETES_URL = "https://sports.core.api.espn.com/v3/sports/football/nfl/athletes?limit=20000&active=true"
ESPN_ATHLETES_ALL_URL = "https://sports.core.api.espn.com/v3/sports/football/nfl/athletes?limit=20000&active=false"
ESPN_ATHLETE_OVERVIEW_URL = "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{athlete_id}/overview"
ESPN_ATHLETE_OVERVIEW_SEASON_URL = "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{athlete_id}/overview?season={season}"
ESPN_ATHLETE_GAMELOG_URL = "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{athlete_id}/gamelog"
ESPN_ATHLETE_GAMELOG_SEASON_URL = "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{athlete_id}/gamelog?season={season}"

CURRENT_SEASON = datetime.now().year
VALID_SEASONS = list(range(2000, CURRENT_SEASON + 1))

TEAM_LOGOS = {
    "ARI": "https://a.espncdn.com/i/teamlogos/nfl/500/ari.png",
    "ATL": "https://a.espncdn.com/i/teamlogos/nfl/500/atl.png",
    "BAL": "https://a.espncdn.com/i/teamlogos/nfl/500/bal.png",
    "BUF": "https://a.espncdn.com/i/teamlogos/nfl/500/buf.png",
    "CAR": "https://a.espncdn.com/i/teamlogos/nfl/500/car.png",
    "CHI": "https://a.espncdn.com/i/teamlogos/nfl/500/chi.png",
    "CIN": "https://a.espncdn.com/i/teamlogos/nfl/500/cin.png",
    "CLE": "https://a.espncdn.com/i/teamlogos/nfl/500/cle.png",
    "DAL": "https://a.espncdn.com/i/teamlogos/nfl/500/dal.png",
    "DEN": "https://a.espncdn.com/i/teamlogos/nfl/500/den.png",
    "DET": "https://a.espncdn.com/i/teamlogos/nfl/500/det.png",
    "GB": "https://a.espncdn.com/i/teamlogos/nfl/500/gb.png",
    "HOU": "https://a.espncdn.com/i/teamlogos/nfl/500/hou.png",
    "IND": "https://a.espncdn.com/i/teamlogos/nfl/500/ind.png",
    "JAX": "https://a.espncdn.com/i/teamlogos/nfl/500/jax.png",
    "KC": "https://a.espncdn.com/i/teamlogos/nfl/500/kc.png",
    "LV": "https://a.espncdn.com/i/teamlogos/nfl/500/lv.png",
    "LAC": "https://a.espncdn.com/i/teamlogos/nfl/500/lac.png",
    "LAR": "https://a.espncdn.com/i/teamlogos/nfl/500/lar.png",
    "MIA": "https://a.espncdn.com/i/teamlogos/nfl/500/mia.png",
    "MIN": "https://a.espncdn.com/i/teamlogos/nfl/500/min.png",
    "NE": "https://a.espncdn.com/i/teamlogos/nfl/500/ne.png",
    "NO": "https://a.espncdn.com/i/teamlogos/nfl/500/no.png",
    "NYG": "https://a.espncdn.com/i/teamlogos/nfl/500/nyg.png",
    "NYJ": "https://a.espncdn.com/i/teamlogos/nfl/500/nyj.png",
    "PHI": "https://a.espncdn.com/i/teamlogos/nfl/500/phi.png",
    "PIT": "https://a.espncdn.com/i/teamlogos/nfl/500/pit.png",
    "SEA": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png",
    "SF": "https://a.espncdn.com/i/teamlogos/nfl/500/sf.png",
    "TB": "https://a.espncdn.com/i/teamlogos/nfl/500/tb.png",
    "TEN": "https://a.espncdn.com/i/teamlogos/nfl/500/ten.png",
    "WAS": "https://a.espncdn.com/i/teamlogos/nfl/500/wsh.png",
}

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

session: aiohttp.ClientSession | None = None
scores_message_id: int | None = None
news_message_id: int | None = None
previous_scores: dict[str, tuple[str, str, str]] = {}

PLAYER_INDEX: list[dict] = []
PLAYER_LOOKUP: dict[str, dict] = {}


def normalize_name(name: str) -> str:
    return " ".join(name.lower().strip().split())


async def fetch_json(url: str) -> dict:
    global session
    if session is None:
        raise RuntimeError("HTTP session not started.")
    async with session.get(url, timeout=25) as resp:
        resp.raise_for_status()
        return await resp.json()


async def get_live_scoreboard() -> list[dict]:
    data = await fetch_json(ESPN_SCOREBOARD_URL)
    games = []

    for event in data.get("events", []):
        competition = event.get("competitions", [{}])[0]
        competitors = competition.get("competitors", [])

        away = next((c for c in competitors if c.get("homeAway") == "away"), {})
        home = next((c for c in competitors if c.get("homeAway") == "home"), {})

        status = competition.get("status", {})
        status_type = status.get("type", {})
        situation = competition.get("situation", {})

        games.append({
            "id": event.get("id"),
            "name": event.get("shortName", event.get("name", "NFL Game")),
            "away_team": away.get("team", {}).get("abbreviation", "AWAY"),
            "home_team": home.get("team", {}).get("abbreviation", "HOME"),
            "away_score": away.get("score", "0"),
            "home_score": home.get("score", "0"),
            "state": status_type.get("shortDetail", "Status unavailable"),
            "completed": status_type.get("completed", False),
            "possession": situation.get("possession"),
            "down_distance": situation.get("downDistanceText", ""),
        })

    return games


async def get_game_summary(event_id: str) -> dict:
    return await fetch_json(ESPN_SUMMARY_URL.format(event_id=event_id))


async def get_news_items(limit: int = 5) -> list[dict]:
    data = await fetch_json(ESPN_NEWS_URL)
    items = []
    for article in data.get("articles", [])[:limit]:
        url = article.get("links", {}).get("web", {}).get("href", "")
        items.append({
            "headline": article.get("headline", "No headline"),
            "description": article.get("description", "No description"),
            "url": url,
        })
    return items


async def build_player_index() -> None:
    global PLAYER_INDEX, PLAYER_LOOKUP

    fresh_lookup = {}

    for url in (ESPN_ATHLETES_URL, ESPN_ATHLETES_ALL_URL):
        try:
            data = await fetch_json(url)
        except Exception:
            continue

        for item in data.get("items", []):
            athlete_id = str(item.get("id", ""))
            display_name = item.get("displayName") or item.get("fullName")
            if not athlete_id or not display_name:
                continue

            if athlete_id in fresh_lookup:
                continue

            position = item.get("position", {}).get("abbreviation", "UNK")
            team = item.get("team", {}).get("abbreviation", "FA")
            active = item.get("active", True)
            status_label = "" if active else " • Retired"

            player = {
                "id": athlete_id,
                "name": display_name,
                "position": position,
                "team": team,
                "active": active,
                "search": normalize_name(display_name),
                "label": f"{display_name} ({team}, {position}{status_label})",
            }
            fresh_lookup[athlete_id] = player

    PLAYER_INDEX = list(fresh_lookup.values())
    PLAYER_LOOKUP = fresh_lookup


def search_players(query: str, limit: int = 25) -> list[dict]:
    q = normalize_name(query)
    if not q:
        return PLAYER_INDEX[:limit]

    starts = [p for p in PLAYER_INDEX if p["search"].startswith(q)]
    contains = [p for p in PLAYER_INDEX if q in p["search"] and not p["search"].startswith(q)]
    return (starts + contains)[:limit]


def resolve_player_by_name(query: str) -> dict | None:
    matches = search_players(query, limit=10)
    if not matches:
        return None

    q = normalize_name(query)
    exact = next((p for p in matches if p["search"] == q), None)
    return exact or matches[0]


async def get_player_overview(athlete_id: str, season: int | None = None) -> dict:
    if season:
        url = ESPN_ATHLETE_OVERVIEW_SEASON_URL.format(athlete_id=athlete_id, season=season)
    else:
        url = ESPN_ATHLETE_OVERVIEW_URL.format(athlete_id=athlete_id)
    return await fetch_json(url)


async def get_player_gamelog(athlete_id: str, season: int | None = None) -> dict:
    if season:
        url = ESPN_ATHLETE_GAMELOG_SEASON_URL.format(athlete_id=athlete_id, season=season)
    else:
        url = ESPN_ATHLETE_GAMELOG_URL.format(athlete_id=athlete_id)
    return await fetch_json(url)


def build_scoreboard_embed(games: list[dict]) -> discord.Embed:
    embed = discord.Embed(
        title="🏈 NFL LIVE SCOREBOARD",
        description=f"Updated {datetime.now().strftime('%b %d, %Y • %I:%M %p')}",
        color=0x7A5C2E,
    )

    if not games:
        embed.add_field(name="No Games", value="No live or scheduled NFL games found.", inline=False)
        return embed

    for game in games[:10]:
        extra = ""
        if game["possession"]:
            extra += f"\nPossession: **{game['possession']}**"
        if game["down_distance"]:
            extra += f"\n{game['down_distance']}"

        embed.add_field(
            name=f"{game['away_team']} @ {game['home_team']}",
            value=f"**{game['away_score']} - {game['home_score']}**\n{game['state']}{extra}",
            inline=False,
        )

    first_logo = TEAM_LOGOS.get(games[0]["away_team"])
    if first_logo:
        embed.set_thumbnail(url=first_logo)

    embed.set_footer(text="USO NFL Bot")
    return embed


def build_news_embed(items: list[dict]) -> discord.Embed:
    embed = discord.Embed(
        title="📰 NFL Headlines",
        description="Latest ESPN NFL stories",
        color=0x7A5C2E,
    )

    if not items:
        embed.add_field(name="No News", value="No headlines available.", inline=False)
        return embed

    for item in items:
        value = f"{item['description'][:180]}\n{item['url']}" if item["url"] else item["description"][:180]
        embed.add_field(name=item["headline"][:256], value=value[:1024], inline=False)

    return embed


def build_game_stats_embed(game_name: str, summary: dict) -> discord.Embed:
    embed = discord.Embed(
        title=f"📊 {game_name}",
        color=0x7A5C2E,
    )

    leaders = summary.get("leaders", [])
    if not leaders:
        embed.description = "No leader stats available yet."
        return embed

    for group in leaders[:4]:
        leader_list = group.get("leaders", [])
        if not leader_list:
            continue
        leader = leader_list[0]
        athlete = leader.get("athlete", {}).get("displayName", "Unknown")
        display_value = leader.get("displayValue", "No stats")
        name = group.get("name", "Leaders")
        embed.add_field(name=name, value=f"**{athlete}** — {display_value}", inline=False)

    return embed


def build_player_stats_embed(player: dict, overview: dict) -> discord.Embed:
    embed = discord.Embed(
        title=f"👤 {player['name']}",
        description=f"**Team:** {player['team']} • **Pos:** {player['position']}",
        color=0x7A5C2E,
    )

    logo = TEAM_LOGOS.get(player["team"])
    if logo:
        embed.set_thumbnail(url=logo)

    statistics = overview.get("statistics", {})
    added = 0

    if isinstance(statistics, dict):
        season_label = statistics.get("displayName", "Stats")
        labels = statistics.get("labels", [])
        splits = statistics.get("splits", [])

        for split in splits[:4]:
            split_name = split.get("displayName", "Stats")
            stats_vals = split.get("stats", [])
            lines = []
            for label, val in zip(labels, stats_vals):
                if val not in ("0", "0.0", "0.00", "--", ""):
                    lines.append(f"**{label}:** {val}")
            if lines:
                embed.add_field(
                    name=f"{season_label} — {split_name}"[:256],
                    value="\n".join(lines[:12])[:1024],
                    inline=False,
                )
                added += 1

    elif isinstance(statistics, list):
        for section in statistics[:4]:
            label = section.get("displayName") or section.get("name") or "Stats"
            stats = section.get("stats", [])
            lines = []
            for stat in stats[:6]:
                if isinstance(stat, dict):
                    stat_name = stat.get("displayName") or stat.get("name")
                    stat_value = stat.get("displayValue") or stat.get("value")
                    if stat_name and stat_value is not None:
                        lines.append(f"**{stat_name}:** {stat_value}")
            if lines:
                embed.add_field(name=label[:256], value="\n".join(lines)[:1024], inline=False)
                added += 1

    if added == 0:
        embed.add_field(name="Stats", value="No stats available for this player/season.", inline=False)

    return embed


def extract_gamelog_entries(gamelog: dict) -> list[dict]:
    entries = []

    labels = gamelog.get("labels", [])
    events_dict = gamelog.get("events", {})
    season_types = gamelog.get("seasonTypes", [])

    if isinstance(events_dict, dict) and season_types:
        for season_type in season_types:
            season_name = season_type.get("displayName", "")
            for category in season_type.get("categories", []):
                for ev in category.get("events", []):
                    event_id = str(ev.get("eventId", ""))
                    stats_vals = ev.get("stats", [])

                    event_info = events_dict.get(event_id, {})
                    opponent = event_info.get("opponent", {}).get("abbreviation", "?")
                    at_vs = event_info.get("atVs", "vs")
                    game_date = event_info.get("gameDate", "")[:10]
                    result = event_info.get("gameResult", "")
                    score = event_info.get("score", "")
                    week = event_info.get("week", "")

                    stat_parts = []
                    for label, val in zip(labels, stats_vals):
                        if val not in ("0", "0.0", "--", ""):
                            stat_parts.append(f"{label}: {val}")

                    title = f"{at_vs} {opponent}"
                    if week:
                        title = f"Wk {week} {title}"
                    if game_date:
                        title = f"{game_date} {title}"
                    if result and score:
                        title += f" ({result} {score})"

                    entries.append({
                        "title": f"{season_name} | {title}"[:256],
                        "value": " • ".join(stat_parts[:10]) or "No stats recorded",
                    })

    if not entries:
        entries.append({
            "title": "No game log data",
            "value": "No game log data found for this player/season.",
        })

    return entries


class GameLogView(discord.ui.View):
    def __init__(self, player: dict, entries: list[dict]):
        super().__init__(timeout=180)
        self.player = player
        self.entries = entries
        self.page = 0

    def build_embed(self) -> discord.Embed:
        current = self.entries[self.page]
        embed = discord.Embed(
            title=f"📋 {self.player['name']} Game Log",
            description=f"**Team:** {self.player['team']} • **Pos:** {self.player['position']}",
            color=0x7A5C2E,
        )
        logo = TEAM_LOGOS.get(self.player["team"])
        if logo:
            embed.set_thumbnail(url=logo)

        embed.add_field(name=current["title"][:256], value=current["value"][:1024], inline=False)
        embed.set_footer(text=f"Game {self.page + 1}/{len(self.entries)}")
        return embed

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < len(self.entries) - 1:
            self.page += 1
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


async def player_name_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> list[app_commands.Choice[str]]:
    matches = search_players(current, limit=25)
    return [app_commands.Choice(name=p["label"][:100], value=p["name"]) for p in matches]


async def upsert_message(channel_id: int, message_id: int | None, embed: discord.Embed) -> int | None:
    if not channel_id:
        return message_id

    channel = bot.get_channel(channel_id)
    if channel is None:
        return message_id

    if message_id:
        try:
            msg = await channel.fetch_message(message_id)
            await msg.edit(embed=embed)
            return msg.id
        except discord.NotFound:
            pass

    msg = await channel.send(embed=embed)
    return msg.id


@tasks.loop(seconds=45)
async def scores_loop():
    global scores_message_id, previous_scores

    games = await get_live_scoreboard()
    scores_message_id = await upsert_message(
        SCORES_CHANNEL_ID,
        scores_message_id,
        build_scoreboard_embed(games),
    )

    if not ALERTS_CHANNEL_ID:
        return

    alerts_channel = bot.get_channel(ALERTS_CHANNEL_ID)
    if alerts_channel is None:
        return

    for game in games:
        key = game["id"]
        current = (game["away_score"], game["home_score"], game["state"])
        old = previous_scores.get(key)

        if old and old[:2] != current[:2]:
            await alerts_channel.send(
                f"🚨 Score Update: {game['away_team']} {game['away_score']} - "
                f"{game['home_team']} {game['home_score']} ({game['state']})"
            )

        if old and old[2] != current[2] and "Final" in game["state"]:
            await alerts_channel.send(
                f"✅ Final: {game['away_team']} {game['away_score']} - "
                f"{game['home_team']} {game['home_score']}"
            )

        previous_scores[key] = current


@tasks.loop(minutes=10)
async def news_loop():
    global news_message_id
    items = await get_news_items()
    news_message_id = await upsert_message(
        NEWS_CHANNEL_ID,
        news_message_id,
        build_news_embed(items),
    )


@bot.tree.command(name="scoreboard", description="Show the current NFL scoreboard")
async def scoreboard(interaction: discord.Interaction):
    await interaction.response.defer()
    games = await get_live_scoreboard()
    await interaction.followup.send(embed=build_scoreboard_embed(games))


@bot.tree.command(name="gamestats", description="Show stat leaders for a live game")
@app_commands.describe(team="Team abbreviation like SEA, SF, KC, DAL")
async def gamestats(interaction: discord.Interaction, team: str):
    await interaction.response.defer()
    team = team.upper().strip()

    games = await get_live_scoreboard()
    target = next((g for g in games if team in (g["away_team"], g["home_team"])), None)

    if target is None:
        await interaction.followup.send(f"No live or listed game found for `{team}`.")
        return

    summary = await get_game_summary(target["id"])
    await interaction.followup.send(embed=build_game_stats_embed(target["name"], summary))


@bot.tree.command(name="playerstats", description="Search a player by name and show stats")
@app_commands.describe(
    name="Start typing a player name",
    season="Season year (e.g. 2023). Leave blank for current season."
)
@app_commands.autocomplete(name=player_name_autocomplete)
async def playerstats(interaction: discord.Interaction, name: str, season: int | None = None):
    await interaction.response.defer()

    if season and season not in VALID_SEASONS:
        await interaction.followup.send(f"Invalid season `{season}`. Please enter a year between 2000 and {CURRENT_SEASON}.")
        return

    player = resolve_player_by_name(name)
    if player is None:
        await interaction.followup.send(f"No player found for `{name}`.")
        return

    try:
        overview = await get_player_overview(player["id"], season=season)
    except Exception:
        label = f" for the {season} season" if season else ""
        await interaction.followup.send(f"Could not fetch stats for **{player['name']}**{label}. They may not have data for that year.")
        return

    embed = build_player_stats_embed(player, overview)
    if season:
        embed.title += f" — {season} Season"
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="gamelog", description="Search a player by name and show game log")
@app_commands.describe(
    name="Start typing a player name",
    season="Season year (e.g. 2023). Leave blank for current season."
)
@app_commands.autocomplete(name=player_name_autocomplete)
async def gamelog(interaction: discord.Interaction, name: str, season: int | None = None):
    await interaction.response.defer()

    if season and season not in VALID_SEASONS:
        await interaction.followup.send(f"Invalid season `{season}`. Please enter a year between 2000 and {CURRENT_SEASON}.")
        return

    player = resolve_player_by_name(name)
    if player is None:
        await interaction.followup.send(f"No player found for `{name}`.")
        return

    try:
        gamelog_data = await get_player_gamelog(player["id"], season=season)
    except Exception:
        label = f" for the {season} season" if season else ""
        await interaction.followup.send(f"Could not fetch game log for **{player['name']}**{label}. They may not have data for that year.")
        return

    entries = extract_gamelog_entries(gamelog_data)
    view = GameLogView(player, entries)
    embed = view.build_embed()
    if season:
        embed.title += f" — {season} Season"
    await interaction.followup.send(embed=embed, view=view)


@bot.tree.command(name="seahawks", description="Quick Seahawks game update")
async def seahawks(interaction: discord.Interaction):
    await interaction.response.defer()

    games = await get_live_scoreboard()
    game = next((g for g in games if "SEA" in (g["away_team"], g["home_team"])), None)

    if game is None:
        await interaction.followup.send("No Seahawks game found right now.")
        return

    embed = discord.Embed(
        title="💙 Seahawks Update",
        description=(
            f"**{game['away_team']} {game['away_score']} - "
            f"{game['home_team']} {game['home_score']}**\n{game['state']}"
        ),
        color=0x2C6DB2,
    )
    embed.set_thumbnail(url=TEAM_LOGOS["SEA"])
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="headlines", description="Show latest NFL headlines")
async def headlines(interaction: discord.Interaction):
    await interaction.response.defer()
    items = await get_news_items()
    await interaction.followup.send(embed=build_news_embed(items))


@bot.event
async def on_ready():
    global session

    if session is None:
        session = aiohttp.ClientSession()

    if not PLAYER_INDEX:
        try:
            await build_player_index()
            print(f"Loaded {len(PLAYER_INDEX)} players.")
        except Exception as e:
            print(f"Could not load player index: {e}")

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Command sync error: {e}")

    if not scores_loop.is_running():
        scores_loop.start()

    if not news_loop.is_running():
        news_loop.start()

    print(f"BOT READY - Logged in as {bot.user}")


async def shutdown_session():
    global session
    if session and not session.closed:
        await session.close()


if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing. Add it in Replit Secrets.")

try:
    bot.run(TOKEN)
finally:
    import asyncio
    asyncio.run(shutdown_session())
