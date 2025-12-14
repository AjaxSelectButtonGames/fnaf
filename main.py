# =========================
# ENV + IMPORTS
# =========================
import os
import random
import asyncio
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

# Load environment variables (safe on NerdHosting)
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing from environment variables")

# =========================
# DISCORD SETUP
# =========================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# GAME STATE
# =========================
games = {}
player_stats = {}

# =========================
# GAME CLASS
# =========================
class FNAFGame:
    def __init__(self, player_id, night=1):
        self.player_id = player_id
        self.night = max(1, min(night, 7))
        self.hour = 0
        self.minute = 0
        self.power = 100

        self.left_door = False
        self.right_door = False
        self.left_light = False
        self.right_light = False
        self.camera_on = False
        self.current_camera = "Show Stage"

        self.game_over = False
        self.channel_id = None
        self.last_camera_check = 0

        self.animatronics = {
            "Bonnie": {"location": "Show Stage", "aggression": night, "path": "left"},
            "Chica": {"location": "Show Stage", "aggression": night, "path": "right"},
            "Foxy": {"stage": 0},
            "Freddy": {"location": "Show Stage", "aggression": night - 1},
        }

        self.gifs = {
            "Bonnie": "https://tenor.com/uhaH1QUiuGV.gif",
            "Chica": "https://tenor.com/v5OfDTV82P0.gif",
            "Foxy": "https://tenor.com/c0zLNtiVYkX.gif",
            "Freddy": "https://tenor.com/lIunPhLWSBd.gif",
        }

    def power_drain(self):
        drain = 1
        if self.left_door:
            drain += 2
        if self.right_door:
            drain += 2
        if self.left_light:
            drain += 1
        if self.right_light:
            drain += 1
        if self.camera_on:
            drain += 1
        return drain

# =========================
# BOT EVENTS
# =========================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    game_loop.start()

# =========================
# COMMANDS
# =========================
@bot.command()
async def start(ctx, night: int = 1):
    if ctx.author.id in games and not games[ctx.author.id].game_over:
        await ctx.send("You're already in a game!")
        return

    game = FNAFGame(ctx.author.id, night)
    game.channel_id = ctx.channel.id
    games[ctx.author.id] = game

    if ctx.author.id not in player_stats:
        player_stats[ctx.author.id] = {"wins": 0, "deaths": 0}

    await ctx.send(f"🌙 **Night {night} started!** Survive until 6AM!")

@bot.command()
async def left(ctx):
    game = games.get(ctx.author.id)
    if not game or game.game_over:
        return await ctx.send("No active game.")
    game.left_door = not game.left_door
    await ctx.send(f"Left door {'CLOSED 🚪' if game.left_door else 'OPEN ⬜'}")

@bot.command()
async def right(ctx):
    game = games.get(ctx.author.id)
    if not game or game.game_over:
        return await ctx.send("No active game.")
    game.right_door = not game.right_door
    await ctx.send(f"Right door {'CLOSED 🚪' if game.right_door else 'OPEN ⬜'}")

@bot.command()
async def cam(ctx):
    game = games.get(ctx.author.id)
    if not game or game.game_over:
        return await ctx.send("No active game.")
    game.camera_on = not game.camera_on
    game.last_camera_check = game.minute
    await ctx.send(f"Camera {'ON 📹' if game.camera_on else 'OFF'}")

@bot.command()
async def status(ctx):
    game = games.get(ctx.author.id)
    if not game:
        return await ctx.send("No active game.")

    embed = discord.Embed(
        title="🍕 Freddy Fazbear's Pizza",
        description=f"🕒 **{game.hour}AM** | ⚡ **{game.power}% Power**",
        color=discord.Color.red() if game.power < 20 else discord.Color.purple()
    )
    embed.add_field(name="Left Door", value="🚪" if game.left_door else "⬜", inline=True)
    embed.add_field(name="Right Door", value="🚪" if game.right_door else "⬜", inline=True)
    embed.add_field(name="Camera", value="📹 ON" if game.camera_on else "📹 OFF", inline=True)

    await ctx.send(embed=embed)

@bot.command()
async def quit(ctx):
    if ctx.author.id in games:
        del games[ctx.author.id]
        await ctx.send("Game ended. 🍕")

# =========================
# GAME LOOP (PERSISTENT)
# =========================
@tasks.loop(seconds=5)
async def game_loop():
    for player_id, game in list(games.items()):
        if game.game_over:
            continue

        game.minute += 1
        if game.minute >= 10:
            game.minute = 0
            game.hour += 1

        game.power = max(0, game.power - game.power_drain())

        if game.hour >= 6:
            game.game_over = True
            player_stats[player_id]["wins"] += 1
            channel = bot.get_channel(game.channel_id)
            if channel:
                await channel.send("🎉 **6AM — YOU SURVIVED!**")
            continue

        if game.power <= 0:
            game.game_over = True
            player_stats[player_id]["deaths"] += 1
            channel = bot.get_channel(game.channel_id)
            if channel:
                await channel.send(game.gifs["Freddy"])
                await channel.send("💀 **Power ran out… Freddy got you.**")

# =========================
# START BOT
# =========================
bot.run(DISCORD_TOKEN)
