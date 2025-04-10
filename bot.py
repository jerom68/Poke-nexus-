import os
import discord
import asyncio
import random
import datetime
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
tree = bot.tree

TOKEN = os.getenv("DISCORD_TOKEN")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
VOUCH_CHANNEL_ID = int(os.getenv("VOUCH_CHANNEL_ID"))
SUPPORT_CHANNEL_ID = int(os.getenv("SUPPORT_CHANNEL_ID"))
INFINITE_ROLE_ID = int(os.getenv("INFINITE_ROLE_ID"))
DEFAULT_ROLE_ID = int(os.getenv("DEFAULT_ROLE_ID"))
STAFF_ROLE_ID = int(os.getenv("STAFF_ROLE_ID"))

coin_balances = {}
gambling_wins = {}

# ----------- EVENTS -----------
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        synced = await tree.sync()
        print(f'Synced {len(synced)} slash commands.')
    except Exception as e:
        print(e)

@bot.event
async def on_member_join(member):
    role = member.guild.get_role(DEFAULT_ROLE_ID)
    if role:
        await member.add_roles(role)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=discord.Embed(title="Missing Permissions", description="You don’t have permission to run this command.", color=discord.Color.red()))
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(embed=discord.Embed(title="Cooldown", description=f"This command is on cooldown. Try again in {round(error.retry_after, 2)}s.", color=discord.Color.orange()))
    else:
        await ctx.send(embed=discord.Embed(title="Error", description=str(error), color=discord.Color.dark_red()))

# ----------- CORE COMMANDS -----------
@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

@tree.command(name="ping", description="Check latency")
async def ping_slash(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

@bot.command()
async def botinfo(ctx):
    uptime = datetime.datetime.utcnow() - bot.launch_time
    embed = discord.Embed(title="Bot Info", color=discord.Color.blue())
    embed.add_field(name="Uptime", value=str(uptime).split('.')[0])
    embed.add_field(name="Ping", value=f"{round(bot.latency * 1000)}ms")
    await ctx.send(embed=embed)

@bot.command()
async def say(ctx, *, msg):
    await ctx.send(msg)

# ----------- MODERATION -----------
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.kick(reason=reason)
    await ctx.send(embed=discord.Embed(title="User Kicked", description=f"{member.mention} has been kicked.", color=discord.Color.orange()))

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.ban(reason=reason)
    await ctx.send(embed=discord.Embed(title="User Banned", description=f"{member.mention} has been banned.", color=discord.Color.red()))

@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(embed=discord.Embed(title="Channel Locked", color=discord.Color.dark_red()))

@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(embed=discord.Embed(title="Channel Unlocked", color=discord.Color.green()))

@bot.command()
@commands.has_permissions(manage_channels=True)
async def hide(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, view_channel=False)
    await ctx.send(embed=discord.Embed(title="Channel Hidden", color=discord.Color.dark_gray()))

@bot.command()
@commands.has_permissions(manage_channels=True)
async def unhide(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, view_channel=True)
    await ctx.send(embed=discord.Embed(title="Channel Unhidden", color=discord.Color.green()))

# ----------- ECONOMY SYSTEM -----------
@bot.command()
async def balance(ctx):
    coins = coin_balances.get(ctx.author.id, 0)
    await ctx.send(f"**{ctx.author.name}** has **{coins}** coins.")

@bot.command()
async def givecoin(ctx, member: discord.Member, amount: int):
    sender_id = ctx.author.id
    receiver_id = member.id
    if INFINITE_ROLE_ID in [role.id for role in ctx.author.roles] or coin_balances.get(sender_id, 0) >= amount:
        coin_balances[sender_id] = coin_balances.get(sender_id, 0) - amount
        coin_balances[receiver_id] = coin_balances.get(receiver_id, 0) + amount
        await ctx.send(f"Gave {amount} coins to {member.mention}.")
    else:
        await ctx.send("You don’t have enough coins.")

@bot.command()
async def transfer(ctx, member: discord.Member, amount: int):
    await givecoin(ctx, member, amount)

# ----------- GAMBLING GAMES (with cooldown) -----------
from discord.ext.commands import cooldown, BucketType

@bot.command(aliases=["cf"])
@cooldown(1, 600, BucketType.user)
async def coinflip(ctx, amount: int):
    if coin_balances.get(ctx.author.id, 0) < amount:
        return await ctx.send("Not enough coins.")
    result = random.choice(["win", "lose"])
    if result == "win":
        coin_balances[ctx.author.id] += amount
        gambling_wins[ctx.author.id] = gambling_wins.get(ctx.author.id, 0) + 1
        await ctx.send(f"You won! Gained {amount} coins.")
    else:
        coin_balances[ctx.author.id] -= amount
        await ctx.send(f"You lost! Lost {amount} coins.")

@bot.command()
@cooldown(1, 600, BucketType.user)
async def slots(ctx, amount: int):
    if coin_balances.get(ctx.author.id, 0) < amount:
        return await ctx.send("Not enough coins.")
    result = [random.choice(["🍒", "🍋", "🍊"]) for _ in range(3)]
    await ctx.send(f"Result: {' '.join(result)}")
    if len(set(result)) == 1:
        coin_balances[ctx.author.id] += amount * 2
        gambling_wins[ctx.author.id] = gambling_wins.get(ctx.author.id, 0) + 1
        await ctx.send("Jackpot! You won.")
    else:
        coin_balances[ctx.author.id] -= amount
        await ctx.send("You lost.")

@bot.command(aliases=["ttt"])
@cooldown(1, 600, BucketType.user)
async def tictactoe(ctx, member: discord.Member, amount: int):
    await ctx.send("Tic Tac Toe is under development.")

@bot.command()
@cooldown(1, 600, BucketType.user)
async def rps(ctx, member: discord.Member, amount: int):
    await ctx.send("Rock Paper Scissors is under development.")

# ----------- LEADERBOARDS -----------
@bot.command()
async def topgamblers(ctx):
    top = sorted(gambling_wins.items(), key=lambda x: x[1], reverse=True)[:5]
    desc = "\n".join([f"<@{user}>: {wins} wins" for user, wins in top])
    await ctx.send(embed=discord.Embed(title="Top Gamblers", description=desc, color=discord.Color.gold()))

@bot.command()
async def richest(ctx):
    top = sorted(coin_balances.items(), key=lambda x: x[1], reverse=True)[:5]
    desc = "\n".join([f"<@{user}>: {coins} coins" for user, coins in top])
    await ctx.send(embed=discord.Embed(title="Richest Users", description=desc, color=discord.Color.gold()))

# ----------- GIVEAWAY SYSTEM -----------
giveaways = {}

@bot.command()
@commands.has_permissions(manage_guild=True)
async def gstart(ctx, duration, *, prize):
    try:
        secs = sum(int(x[:-1]) * {"d": 86400, "h": 3600, "m": 60}[x[-1]] for x in duration.split())
    except:
        return await ctx.send("Invalid duration format.")

    embed = discord.Embed(
        title=f"<a:giveaway:1349650638262501426> Giveaway Started!",
        description=f"<:prize:1358327679476306090> Prize: **{prize}**\n<a:clockk:1358328773161910315> Ends in: **{duration}**",
        color=discord.Color.dark_gold()
    )
    embed.set_footer(text="React with 🎉 to enter!")
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")
    giveaways[msg.id] = {"prize": prize, "message": msg, "channel": ctx.channel.id}
    await asyncio.sleep(secs)

    new_msg = await ctx.channel.fetch_message(msg.id)
    users = await new_msg.reactions[0].users().flatten()
    users = [u for u in users if not u.bot]
    if users:
        winner = random.choice(users)
        await ctx.send(f"<a:crownn:1358327932027932744> Winner: {winner.mention} | Prize: **{prize}**")
    else:
        await ctx.send("No valid entries, no winner selected.")

@bot.command()
@commands.has_permissions(manage_guild=True)
async def gend(ctx, msg_id: int):
    if msg_id in giveaways:
        await ctx.send("Giveaway force ended.")
    else:
        await ctx.send("Giveaway not found.")

@bot.command()
@commands.has_permissions(manage_guild=True)
async def reroll(ctx, msg_id: int):
    if msg_id in giveaways:
        data = giveaways[msg_id]
        msg = await bot.get_channel(data["channel"]).fetch_message(msg_id)
        users = await msg.reactions[0].users().flatten()
        users = [u for u in users if not u.bot]
        winner = random.choice(users)
        await ctx.send(f"New winner: {winner.mention}")
    else:
        await ctx.send("Invalid giveaway.")

# ----------- TICKET SYSTEM -----------
from discord.ui import View, Button

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(emoji="<:golden_ticket:1358342514150477928>", label="Open Ticket", style=discord.ButtonStyle.primary, custom_id="ticket_main"))

@bot.command()
async def ticketpanel(ctx):
    embed = discord.Embed(title="Support Panel", description="Click below to open a ticket!", color=discord.Color.blurple())
    await ctx.send(embed=embed, view=TicketView())

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.data["custom_id"] == "ticket_main":
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            interaction.guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(view_channel=True)
        }
        ticket = await interaction.guild.create_text_channel(f"ticket-{interaction.user.name}", overwrites=overwrites)
        await ticket.send(f"{interaction.user.mention} Ticket created. Staff will assist shortly.")
        await interaction.response.send_message("Ticket created!", ephemeral=True)
        await ticket.send(f"<@&{STAFF_ROLE_ID}>")

# ----------- POKÉTWO SHINY CHECK -----------
@bot.command()
async def shinycheck(ctx, *, text):
    shiny_keywords = ["shiny", "sparkle", "gleam"]
    if any(word in text.lower() for word in shiny_keywords):
        await ctx.send("It might be shiny!")
    else:
        await ctx.send("Doesn’t look shiny.")

# ----------- LUCK COMMAND -----------
@bot.command()
async def luck(ctx):
    value = random.randint(1, 100)
    await ctx.send(f"Your luck today is: {value}%")

# ----------- PAID + VOUCH -----------
@bot.command()
async def paid(ctx, member: discord.Member):
    embed = discord.Embed(title="Payment Confirmation", description="Hey, You have been paid in **Arched Vibes**.", color=discord.Color.green())
    embed.add_field(name="Vouch Here", value=f"<#{VOUCH_CHANNEL_ID}>")
    embed.add_field(name="Need Help?", value=f"Open a ticket in <#{SUPPORT_CHANNEL_ID}>")
    try:
        await member.send(embed=embed)
        await ctx.send(f"{member.mention} has been DMed.")
    except:
        await ctx.send("Couldn't DM the user.")

@bot.command()
async def vouch(ctx, member: discord.Member, *, reason="No reason provided"):
    vouch_channel = bot.get_channel(VOUCH_CHANNEL_ID)
    embed = discord.Embed(title="Vouch", description=f"{ctx.author.mention} vouched for {member.mention}\nReason: {reason}", color=discord.Color.blue())
    await vouch_channel.send(embed=embed)
    await ctx.send("Vouch sent!")

# ----------- PORT HANDLING -----------
import threading
from flask import Flask
app = Flask('')

@app.route('/')
def home():
    return "Bot is Alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run).start()

# ----------- RUN BOT -----------
bot.launch_time = datetime.datetime.utcnow()
bot.run(TOKEN)
