import discord
from discord.ext import commands, tasks
import random
import asyncio

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

games = {}
player_stats = {}

class FNAFGame:
    def __init__(self, player_id, night=1):
        self.player_id = player_id
        self.night = night
        self.hour = 0
        self.minute = 0
        self.power = 100
        self.left_door = False
        self.right_door = False
        self.camera_on = False
        self.game_over = False
        self.channel_id = None

        self.gifs = {
            'Bonnie': 'https://tenor.com/I2mR.gif',
            'Chica': 'https://tenor.com/bGiN5.gif',
            'Foxy': 'https://tenor.com/bzPsC.gif',
            'Freddy': 'https://tenor.com/kZdzqU7zgoG.gif'
        }

        self.animatronics = {
            'Bonnie': {'side': 'left', 'aggression': night},
            'Chica': {'side': 'right', 'aggression': night},
        }

    def power_drain(self):
        drain = 1
        if self.left_door:
            drain += 2
        if self.right_door:
            drain += 2
        if self.camera_on:
            drain += 1
        return drain

    def move_animatronics(self):
        for name, data in self.animatronics.items():
            if random.randint(1, 20) <= data['aggression']:
                if data['side'] == 'left' and not self.left_door:
                    return name
                if data['side'] == 'right' and not self.right_door:
                    return name
        return None

@bot.event
async def on_ready():
    print(f"✅ {bot.user} connected")
    game_loop.start()

@bot.command()
async def start(ctx, night: int = 1):
    game = FNAFGame(ctx.author.id, night)
    game.channel_id = ctx.channel.id
    games[ctx.author.id] = game

    if ctx.author.id not in player_stats:
        player_stats[ctx.author.id] = {'wins': 0, 'deaths': 0}

    await ctx.send("🌙 Night started. Survive until 6AM!")

@bot.command()
async def left(ctx):
    games[ctx.author.id].left_door = not games[ctx.author.id].left_door
    await ctx.send("🚪 Left door toggled")

@bot.command()
async def right(ctx):
    games[ctx.author.id].right_door = not games[ctx.author.id].right_door
    await ctx.send("🚪 Right door toggled")

@tasks.loop(seconds=5)
async def game_loop():
    for game in list(games.values()):
        if game.game_over:
            continue

        game.minute += 1
        if game.minute >= 10:
            game.minute = 0
            game.hour += 1

        game.power -= game.power_drain()
        game.power = max(0, game.power)

        if game.hour >= 6:
            game.game_over = True
            player_stats[game.player_id]['wins'] += 1
            channel = bot.get_channel(game.channel_id)
            await channel.send("🎉 **6AM — YOU SURVIVED!**")
            continue

        attacker = game.move_animatronics()
        if attacker:
            game.game_over = True
            player_stats[game.player_id]['deaths'] += 1
            channel = bot.get_channel(game.channel_id)
            await channel.send(self.gifs[attacker])
            await channel.send(f"💀 **{attacker} GOT YOU!**")

# ✅ NERDHOSTING-SAFE ENV ACCESS (NO import os)
TOKEN = __import__("os").environ.get("DISCORD_TOKEN")
bot.run(TOKEN)
