import discord
from discord.ext import commands, tasks
import random
import asyncio
from datetime import datetime
import json
import os  # ✅ REQUIRED for environment variables

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Game state storage
games = {}
player_stats = {}  # Persistent stats

class FNAFGame:
    def __init__(self, player_id, night=1):
        self.player_id = player_id
        self.night = night
        self.hour = 0
        self.minute = 0
        self.power = 100
        self.left_door = False
        self.right_door = False
        self.left_light = False
        self.right_light = False
        self.camera_on = False
        self.current_camera = "Show Stage"
        self.alive = True
        self.game_over = False
        self.jumpscare_cooldown = 0
        self.ventilation_error = False
        self.oxygen = 100

        self.gifs = {
            'Bonnie': {
                'jumpscare': 'https://tenor.com/I2mR.gif',
                'sighting': 'https://tenor.com/uhaH1QUiuGV.gif',
                'door': 'https://tenor.com/uhaH1QUiuGV.gif'
            },
            'Chica': {
                'jumpscare': 'https://tenor.com/bGiN5.gif',
                'sighting': 'https://tenor.com/v5OfDTV82P0.gif',
                'door': 'https://tenor.com/v5OfDTV82P0.gif'
            },
            'Foxy': {
                'jumpscare': 'https://tenor.com/bzPsC.gif',
                'sighting': 'https://tenor.com/c0zLNtiVYkX.gif',
                'running': 'https://tenor.com/c0zLNtiVYkX.gif'
            },
            'Freddy': {
                'jumpscare': 'https://tenor.com/kZdzqU7zgoG.gif',
                'sighting': 'https://tenor.com/s2beXocU0Np.gif',
                'power_out': 'https://tenor.com/lIunPhLWSBd.gif'
            },
            'office': 'https://tenor.com/bGmQX.gif',
            'static': 'https://tenor.com/VC1x.gif',
            'stage': 'https://tenor.com/bwf7M.gif'
        }

        self.channel_id = None

        self.animatronics = {
            'Bonnie': {'location': 'Show Stage', 'aggression': night, 'path': 'left'},
            'Chica': {'location': 'Show Stage', 'aggression': night, 'path': 'right'},
            'Foxy': {'location': 'Pirate Cove', 'aggression': night + 1, 'stage': 0, 'path': 'left'},
            'Freddy': {'location': 'Show Stage', 'aggression': max(1, night - 1), 'path': 'right'}
        }

        self.camera_rooms = {
            "Show Stage": {},
            "Dining Area": {},
            "Backstage": {},
            "Kitchen": {'audio_only': True},
            "Left Hall": {},
            "Right Hall": {},
            "Supply Closet": {},
            "Left Door": {},
            "Right Door": {},
            "Pirate Cove": {}
        }

        self.last_camera_check = 0

    def calculate_power_drain(self):
        drain = 1
        drain += 2 if self.left_door else 0
        drain += 2 if self.right_door else 0
        drain += 1 if self.left_light else 0
        drain += 1 if self.right_light else 0
        drain += 1 if self.camera_on else 0
        return drain

    def move_animatronics(self):
        for name, data in self.animatronics.items():
            if random.randint(1, 20) <= data['aggression']:
                if data['location'] == 'Show Stage':
                    data['location'] = 'Dining Area'
                elif data['location'] == 'Dining Area':
                    data['location'] = 'Left Door' if data['path'] == 'left' else 'Right Door'

        for name, data in self.animatronics.items():
            if data['location'] == 'Left Door' and not self.left_door:
                return f"💀 **{name} attacked from the LEFT!**", self.gifs[name]['jumpscare']
            if data['location'] == 'Right Door' and not self.right_door:
                return f"💀 **{name} attacked from the RIGHT!**", self.gifs[name]['jumpscare']

        return None, None

    def get_status_embed(self):
        embed = discord.Embed(
            title=f"🍕 Night {self.night}",
            description=f"**{self.hour}AM** | Power: **{self.power}%**",
            color=discord.Color.dark_red() if self.power <= 20 else discord.Color.dark_purple()
        )

        embed.add_field(name="Left Door", value="🚪" if self.left_door else "⬜", inline=True)
        embed.add_field(name="Right Door", value="🚪" if self.right_door else "⬜", inline=True)
        embed.add_field(name="Camera", value="📹 ON" if self.camera_on else "📹 OFF", inline=True)

        return embed

@bot.event
async def on_ready():
    print(f'✅ {bot.user} is online')
    game_loop.start()

@bot.command()
async def start(ctx, night: int = 1):
    game = FNAFGame(ctx.author.id, max(1, min(night, 7)))
    game.channel_id = ctx.channel.id
    games[ctx.author.id] = game

    if ctx.author.id not in player_stats:
        player_stats[ctx.author.id] = {'wins': 0, 'deaths': 0}

    await ctx.send(embed=game.get_status_embed())

@bot.command()
async def left(ctx):
    games[ctx.author.id].left_door = not games[ctx.author.id].left_door
    await ctx.send("Left door toggled")

@bot.command()
async def right(ctx):
    games[ctx.author.id].right_door = not games[ctx.author.id].right_door
    await ctx.send("Right door toggled")

@bot.command()
async def status(ctx):
    await ctx.send(embed=games[ctx.author.id].get_status_embed())

@tasks.loop(seconds=5)
async def game_loop():
    for game in list(games.values()):
        if game.game_over:
            continue

        game.minute += 1
        if game.minute >= 10:
            game.minute = 0
            game.hour += 1

        game.power = max(0, game.power - game.calculate_power_drain())

        if game.hour >= 6:
            game.game_over = True
            player_stats[game.player_id]['wins'] += 1
            channel = bot.get_channel(game.channel_id)
            await channel.send("🎉 **6AM — YOU SURVIVED!**")
            continue

        result, gif = game.move_animatronics()
        if result:
            game.game_over = True
            player_stats[game.player_id]['deaths'] += 1
            channel = bot.get_channel(game.channel_id)
            await channel.send(gif)
            await channel.send(result)

# ✅ NERDHOSTING SAFE TOKEN USAGE
bot.run(os.getenv("DISCORD_TOKEN"))
