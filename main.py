import discord
from discord.ext import commands, tasks
import os
import random
import asyncio

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

AUTHORIZED_ROLE_ID = 1378164944666755242  
TRIGGER_EMOJI = "<:Happi:1381476760708714617>"

file_requests = {}

def generate_random_serial():
    return ''.join([str(random.randint(0, 9)) for _ in range(7)])

def generate_random_file_no():
    letters = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))
    numbers = ''.join(random.choices('0123456789', k=2))
    return f"{letters}-{numbers}"

def generate_masked_ssn():
    last_four = ''.join([str(random.randint(0, 9)) for _ in range(4)])
    return f"XXX-XX-{last_four}"

async def generate_personnel_file(user):
    def check(m):
        return m.author == user and isinstance(m.channel, discord.DMChannel)

    questions = [
        ("Enter NAME:", "name"),
        ("Enter FACTION:", "faction"),
        ("Enter DATE OF BIRTH:", "dob"),
        ("Enter PLACE OF BIRTH:", "pob"),
        ("Enter ACTIVE DUTY DATE:", "active_duty"),
        ("Enter DISCHARGE DATE:", "discharge"),
        ("Enter DISCHARGE TYPE:", "discharge_type"),
        ("Enter LAST RANK:", "last_rank"),
        ("Enter SERVICE STATUS:", "service_status"),
        ("Enter any NOTES:", "notes"),
    ]

    answers = {}

    try:
        await user.send("Let's build your MILITARY PERSONNEL FILE. Answer each question below:")

        for question, key in questions:
            await user.send(question)
            msg = await bot.wait_for('message', check=check, timeout=120)
            answers[key] = msg.content

        serial_no = generate_random_serial()
        file_no = generate_random_file_no()
        ssn = generate_masked_ssn()
        today = datetime.today().strftime("%d %b %Y")

        result = f"""
===========================================
 MILITARY PERSONNEL FILE 
===========================================

  NAME:           {answers['name']}

  SERIAL NO.:     {serial_no}

  FACTION:        {answers['faction']}

-------------------------------------------

  DATE OF BIRTH:     {answers['dob']}

  PLACE OF BIRTH:    {answers['pob']}

  ACTIVE DUTY:       {answers['active_duty']}

  DISCHARGE:         {answers['discharge']}

  DISCHARGE TYPE:    {answers['discharge_type']}

  LAST RANK:         {answers['last_rank']}

  SERVICE STATUS:    {answers['service_status']}

  FILE NO.:          {file_no}

  SOCIAL SECURITY:   {ssn}

  NOTES:
    {answers['notes']}

-------------------------------------------

  FILED BY:          MX-4719-E

  DATE FILED:        {today}
"""
        await user.send("Here is your generated file:")
        await user.send(f"```{result}```")

    except asyncio.TimeoutError:
        await user.send("You took too long to respond. Please try again later.")

@bot.event
async def on_ready():
    print(f"Bot is online! Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.lower() == "file":
        file_requests[message.id] = message.author.id
        await message.channel.send(
            f"{message.author.mention} has requested a file.\n"
            f"<@&{AUTHORIZED_ROLE_ID}> react with {TRIGGER_EMOJI} to accept."
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
             
                await generate_personnel_file(target_user)
                await message.channel.send(f"{target_user.mention}, check your DMs!")
                del file_requests[message.id]
            except discord.Forbidden:
                await message.channel.send(
                    f"{target_user.mention}, I couldn’t DM you. "
                    f"Please enable messages from server members."
                )

@bot.command()
async def ping(ctx):
    await ctx.send("shut up.")

bot.run(os.getenv("DISCORD_TOKEN"))
 