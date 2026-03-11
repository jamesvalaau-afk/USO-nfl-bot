import discord
from discord.ext import commands
from discord import app_commands
import nfl_api


NFL_TEAMS = {
    "ARI": "Arizona Cardinals",
    "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers",
    "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos",
    "DET": "Detroit Lions",
    "GB": "Green Bay Packers",
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs",
    "LAC": "Los Angeles Chargers",
    "LAR": "Los Angeles Rams",
    "LV": "Las Vegas Raiders",
    "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",
    "NE": "New England Patriots",
    "NO": "New Orleans Saints",
    "NYG": "New York Giants",
    "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers",
    "SEA": "Seattle Seahawks",
    "SF": "San Francisco 49ers",
    "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders",
}


class NFL(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="scores", description="Get current NFL scores and today's games")
    async def scores(self, interaction: discord.Interaction):
        await interaction.response.defer()
        data = await nfl_api.get_scoreboard()
        if not data:
            await interaction.followup.send("Could not fetch scores right now. Try again later.")
            return

        events = data.get("events", [])
        if not events:
            await interaction.followup.send("No games found for today.")
            return

        embed = discord.Embed(title="NFL Scores", color=discord.Color.blue())

        for event in events[:10]:
            comps = event.get("competitions", [{}])[0]
            competitors = comps.get("competitors", [])
            status = event.get("status", {})
            status_type = status.get("type", {})
            status_desc = status_type.get("shortDetail", status_type.get("description", ""))

            if len(competitors) >= 2:
                home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
                away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

                home_team = home.get("team", {}).get("abbreviation", "?")
                away_team = away.get("team", {}).get("abbreviation", "?")
                home_score = home.get("score", "-")
                away_score = away.get("score", "-")

                field_name = f"{away_team} @ {home_team}"
                field_value = f"**{away_score} - {home_score}** | {status_desc}"
                embed.add_field(name=field_name, value=field_value, inline=False)

        embed.set_footer(text="Data from ESPN")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="standings", description="Get current NFL standings")
    async def standings(self, interaction: discord.Interaction):
        await interaction.response.defer()
        data = await nfl_api.get_standings()
        if not data:
            await interaction.followup.send("Could not fetch standings right now. Try again later.")
            return

        embed = discord.Embed(title="NFL Standings", color=discord.Color.green())

        children = data.get("children", [])
        for conference in children[:2]:
            conf_name = conference.get("name", "Conference")
            divisions = conference.get("children", [])
            conf_lines = []
            for division in divisions:
                div_name = division.get("name", "Division")
                entries = division.get("standings", {}).get("entries", [])
                conf_lines.append(f"**{div_name}**")
                for entry in entries[:4]:
                    team = entry.get("team", {}).get("abbreviation", "?")
                    stats = {s["name"]: s["value"] for s in entry.get("stats", [])}
                    wins = int(stats.get("wins", 0))
                    losses = int(stats.get("losses", 0))
                    ties = int(stats.get("ties", 0))
                    record = f"{wins}-{losses}" + (f"-{ties}" if ties else "")
                    conf_lines.append(f"  {team}: {record}")
            embed.add_field(name=conf_name, value="\n".join(conf_lines), inline=True)

        embed.set_footer(text="Data from ESPN")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="news", description="Get the latest NFL news")
    async def news(self, interaction: discord.Interaction):
        await interaction.response.defer()
        data = await nfl_api.get_news()
        if not data:
            await interaction.followup.send("Could not fetch news right now. Try again later.")
            return

        articles = data.get("articles", [])
        if not articles:
            await interaction.followup.send("No news found.")
            return

        embed = discord.Embed(title="Latest NFL News", color=discord.Color.orange())
        for article in articles[:5]:
            headline = article.get("headline", "No title")
            description = article.get("description", "")
            link = article.get("links", {}).get("web", {}).get("href", "")
            if description and len(description) > 150:
                description = description[:147] + "..."
            value = description if description else "No description"
            if link:
                value += f"\n[Read more]({link})"
            embed.add_field(name=headline, value=value, inline=False)

        embed.set_footer(text="Data from ESPN")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="team", description="Get info about an NFL team")
    @app_commands.describe(abbreviation="Team abbreviation (e.g., KC, DAL, SF)")
    async def team(self, interaction: discord.Interaction, abbreviation: str):
        await interaction.response.defer()
        abbr = abbreviation.upper().strip()
        if abbr not in NFL_TEAMS:
            teams_list = ", ".join(sorted(NFL_TEAMS.keys()))
            await interaction.followup.send(f"Unknown team `{abbr}`. Valid abbreviations: {teams_list}")
            return

        data = await nfl_api.get_team_info(abbr)
        if not data:
            await interaction.followup.send("Could not fetch team info right now. Try again later.")
            return

        team_data = data.get("team", {})
        name = team_data.get("displayName", NFL_TEAMS[abbr])
        location = team_data.get("location", "")
        nickname = team_data.get("nickname", "")
        color = team_data.get("color", "003399")
        logo_url = None
        logos = team_data.get("logos", [])
        if logos:
            logo_url = logos[0].get("href")

        record_data = team_data.get("record", {}).get("items", [])
        record_str = "N/A"
        if record_data:
            summary = record_data[0].get("summary", "")
            record_str = summary if summary else "N/A"

        try:
            embed_color = discord.Color(int(color, 16))
        except Exception:
            embed_color = discord.Color.blue()

        embed = discord.Embed(title=name, color=embed_color)
        embed.add_field(name="Location", value=location or "N/A", inline=True)
        embed.add_field(name="Nickname", value=nickname or "N/A", inline=True)
        embed.add_field(name="Record", value=record_str, inline=True)
        if logo_url:
            embed.set_thumbnail(url=logo_url)
        embed.set_footer(text="Data from ESPN")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="schedule", description="Get upcoming schedule for a team")
    @app_commands.describe(abbreviation="Team abbreviation (e.g., KC, DAL, SF)")
    async def schedule(self, interaction: discord.Interaction, abbreviation: str):
        await interaction.response.defer()
        abbr = abbreviation.upper().strip()
        if abbr not in NFL_TEAMS:
            teams_list = ", ".join(sorted(NFL_TEAMS.keys()))
            await interaction.followup.send(f"Unknown team `{abbr}`. Valid abbreviations: {teams_list}")
            return

        data = await nfl_api.get_schedule(abbr)
        if not data:
            await interaction.followup.send("Could not fetch schedule right now. Try again later.")
            return

        team_name = NFL_TEAMS[abbr]
        embed = discord.Embed(title=f"{team_name} Schedule", color=discord.Color.purple())

        events = data.get("events", [])
        if not events:
            embed.description = "No upcoming games found."
        else:
            shown = 0
            for event in events:
                if shown >= 8:
                    break
                status_type = event.get("status", {}).get("type", {})
                state = status_type.get("state", "")
                if state == "post":
                    continue
                name_str = event.get("name", "")
                date_str = event.get("date", "")
                short_date = date_str[:10] if date_str else "TBD"
                embed.add_field(name=short_date, value=name_str or "TBD", inline=False)
                shown += 1

            if shown == 0:
                embed.description = "No upcoming games in the schedule."

        embed.set_footer(text="Data from ESPN")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="help", description="Show all available NFL bot commands")
    async def help_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="USO NFL Bot - Commands",
            description="Here are all available commands:",
            color=discord.Color.gold()
        )
        embed.add_field(name="/scores", value="Get current NFL scores and live game updates", inline=False)
        embed.add_field(name="/standings", value="Get current NFL standings by division", inline=False)
        embed.add_field(name="/news", value="Get the latest NFL news headlines", inline=False)
        embed.add_field(name="/team <abbreviation>", value="Get details about a specific NFL team (e.g., `/team KC`)", inline=False)
        embed.add_field(name="/schedule <abbreviation>", value="Get upcoming schedule for a team (e.g., `/schedule DAL`)", inline=False)
        embed.add_field(
            name="Team Abbreviations",
            value="ARI, ATL, BAL, BUF, CAR, CHI, CIN, CLE, DAL, DEN, DET, GB, HOU, IND, JAX, KC, LAC, LAR, LV, MIA, MIN, NE, NO, NYG, NYJ, PHI, PIT, SEA, SF, TB, TEN, WAS",
            inline=False
        )
        embed.set_footer(text="USO NFL Bot | Data from ESPN")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(NFL(bot))
