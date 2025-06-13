import os
from dotenv import load_dotenv
import discord
from discord.ext import commands


load_dotenv()


TOKEN = os.getenv("DISCORD_TOKEN")


intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True


bot = commands.Bot(command_prefix='!', intents=intents)


AUTHORIZED_ROLE_ID = 1378164944666755242  
TRIGGER_EMOJI = "<:Happi:1381476760708714617>" 


file_requests = {}

@bot.event
async def on_ready():
    print(f"✅ Bot is online! Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.lower() == "file":
        file_requests[message.id] = message.author.id
        await message.channel.send(
            f"{message.author.mention} has requested a file.\n"
            f"Moderators, please react with {TRIGGER_EMOJI} to approve."
        )

    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    if str(reaction.emoji) != TRIGGER_EMOJI:
        return

    message = reaction.message
    guild = message.guild
    if not guild:
        return

    role = discord.utils.get(guild.roles, id=AUTHORIZED_ROLE_ID)
    if role not in user.roles:
        return

    if message.id in file_requests:
        target_user_id = file_requests[message.id]
        target_user = guild.get_member(target_user_id)
        if target_user:
            try:
                await target_user.send("CURRENTLY A W.I.P, PLEASE IGNORE")
                await message.channel.send(f"{target_user.mention}, check your DMs!")
                del file_requests[message.id]
            except discord.Forbidden:
                await message.channel.send(
                    f"{target_user.mention}, I couldn’t DM you. "
                    f"Please enable messages from server members."
                )


if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ DISCORD_TOKEN not found in environment.")

