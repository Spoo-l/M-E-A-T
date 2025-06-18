import os
import random
import asyncio
from datetime import datetime

import discord
from discord.ext import commands
from discord.ui import Button, View

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

AUTHORIZED_ROLE_ID = 1378164944666755242
MEMBER_ROLE_ID = 1378204196477730836
FISH_CHANNEL_ID = 1382936876985483337
TRIGGER_EMOJI = "<:check:1383527537640083556>"

file_requests = {}

FACTION_THREADS = {
    "specgru": 1382555575774220339,
    "shadow company": 1382555520388431964,
    "kortac": 1382555644502216744,
    "141": 1382555452772192399,
    "konni": 1382556557631426630
}

def generate_random_file_no():
    return f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))}-{''.join(random.choices('0123456789', k=2))}"

def generate_masked_ssn():
    return f"XXX-XX-{''.join([str(random.randint(0, 9)) for _ in range(4)])}"

async def generate_personnel_file(user):
    def check(m): return m.author == user and isinstance(m.channel, discord.DMChannel)

    questions = [
        ("Enter NAME:", "full name"),
        ("Enter FACTION:", "faction"),
        ("Enter USERNAME:", "username"),
        ("Enter DATE OF BIRTH:", "dob"),
        ("Enter PLACE OF BIRTH:", "place_of_birth"),
        ("Enter ACTIVE DUTY DATE:", "active_duty"),
        ("Enter DISCHARGE DATE:", "discharge"),
        ("Enter DISCHARGE TYPE:", "discharge_type"),
        ("Enter LAST RANK:", "last_rank"),
        ("Enter SERVICE STATUS:", "service_status"),
        ("Enter any NOTES:", "notes"),
    ]
    answers = {}

    class ConfirmView(View):
        def __init__(self):
            super().__init__(timeout=60)
            self.value = False

        @discord.ui.button(label="OK", style=discord.ButtonStyle.success)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == user:
                self.value = True
                await interaction.response.edit_message(content="✅ File creation started.", view=None)
                self.stop()

    await user.send("**CREATING FILE. . .** Click OK to begin.")
    confirm_view = ConfirmView()
    await user.send(view=confirm_view)
    await confirm_view.wait()
    if not confirm_view.value:
        await user.send("You didn’t confirm. File process cancelled.")
        return

    await user.send("Answer each question carefully. FACTION must match: SpecGru, Shadow Company, KorTac, 141, or Konni.")
    for prompt, key in questions:
        await user.send(prompt)
        try:
            msg = await bot.wait_for('message', check=check, timeout=120)
            answers[key] = msg.content
        except asyncio.TimeoutError:
            await user.send("Timeout. Try again later.")
            return

    serial_no = generate_random_file_no()
    ssn = generate_masked_ssn()
    today = datetime.today().strftime("%d %b %Y")

    def format_file():
        return f"""
===================================
 MILITARY PERSONNEL FILE 
===================================

  NAME:           {answers['full name']}
  SERIAL NO.:     {serial_no}

  FACTION:        {answers['faction']}
  ONLINE ALIAS:   {answers['username']}

-----------------------------------

  DATE OF BIRTH:     {answers['dob']}
  PLACE OF BIRTH:    {answers['place_of_birth']}
  ACTIVE DUTY:       {answers['active_duty']}
  DISCHARGE:         {answers['discharge']}
  DISCHARGE TYPE:    {answers['discharge_type']}
  LAST RANK:         {answers['last_rank']}
  SERVICE STATUS:    {answers['service_status']}

  FILE NO.:          {generate_random_file_no()}
  SOCIAL SECURITY:   {ssn}

  NOTES:
    {answers['notes']}

-----------------------------------

  FILED BY:          MX-4719-E
  DATE FILED:        {today}
"""

    class EditButton(Button):
        def __init__(self, label, key):
            super().__init__(label=label.upper(), style=discord.ButtonStyle.secondary)
            self.key = key

        async def callback(self, interaction: discord.Interaction):
            if interaction.user != user:
                await interaction.response.send_message("You can't edit someone else's file.", ephemeral=True)
                return
            await interaction.response.send_message(f"Send new value for {self.key.upper()}:", ephemeral=True)
            try:
                new_msg = await bot.wait_for("message", check=check, timeout=60)
                answers[self.key] = new_msg.content
                await interaction.followup.send(f"{self.key.upper()} updated.", ephemeral=True)
            except asyncio.TimeoutError:
                await interaction.followup.send("Timeout. Field unchanged.", ephemeral=True)

    class EditView(View):
        def __init__(self):
            super().__init__(timeout=180)
            for _, key in questions:
                self.add_item(EditButton(label=key, key=key))

    await user.send("Here’s your draft file:")
    await user.send(f"```{format_file()}```")
    await user.send("Want to edit anything? Choose a field below:", view=EditView())
    await asyncio.sleep(60)

    await user.send("Final version:")
    await user.send(f"```{format_file()}```")

    class SubmitView(View):
        def __init__(self):
            super().__init__(timeout=60)
            self.confirmed = False

        @discord.ui.button(label="Submit File", style=discord.ButtonStyle.success)
        async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == user:
                self.confirmed = True
                await interaction.response.send_message("File submitted.", ephemeral=True)
                self.stop()

    submit_view = SubmitView()
    await user.send("Submit this file to your FACTION thread?", view=submit_view)
    await submit_view.wait()

    if submit_view.confirmed:
        faction_key = answers["faction"].strip().lower()
        thread_id = FACTION_THREADS.get(faction_key)
        if thread_id:
            thread = bot.get_channel(thread_id)
            if thread:
                await thread.send(f"```{format_file()}```")
                await user.send("File posted to faction thread.")
            else:
                await user.send("Could not locate faction thread.")
        else:
            await user.send("Invalid FACTION. No thread mapped.")
    else:
        await user.send("File not submitted.")

@bot.event
async def on_ready():
    print(f"Bot is online! Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id == FISH_CHANNEL_ID and message.content.strip().lower() == "fish":
        member_role = discord.utils.get(message.guild.roles, id=MEMBER_ROLE_ID)
        unverified_role = discord.utils.get(message.guild.roles, name="Unverified")
        if member_role and member_role not in message.author.roles:
            try:
                await message.author.add_roles(member_role)
                if unverified_role in message.author.roles:
                    await message.author.remove_roles(unverified_role)
                await message.add_reaction("✅")
            except Exception as e:
                await message.channel.send(f"Error verifying: {e}", delete_after=10)

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
    if message.id in file_requests:
        target_user = message.guild.get_member(file_requests[message.id])
        if target_user:
            try:
                await message.channel.send(f"{target_user.mention}, check your DMs.")
                await generate_personnel_file(target_user)
            except discord.Forbidden:
                await message.channel.send(
                    f"{target_user.mention}, I couldn’t DM you. Enable messages from server members."
                )
            finally:
                del file_requests[message.id]

@bot.event
async def on_member_join(member):
    role = discord.utils.get(member.guild.roles, name="Unverified")
    if role:
        try:
            await member.add_roles(role, reason="Assigned Unverified role on join")
            print(f"Assigned 'Unverified' to {member.name}")
        except discord.Forbidden:
            print(f"Missing permissions to assign role to {member.name}")
        except discord.HTTPException as e:
            print(f"Failed to assign role to {member.name}: {e}")
    else:
        print("Role 'Unverified' not found.")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    FISH_CHANNEL_ID = 1382936876985483337
    MEMBER_ROLE_ID = 1378204196477730836

    if message.channel.id == FISH_CHANNEL_ID and message.content.strip().lower() == "fish":
        guild = message.guild
        member = message.author
        member_role = discord.utils.get(guild.roles, id=MEMBER_ROLE_ID)
        unverified_role = discord.utils.get(guild.roles, name="Unverified")

        if member_role and member_role not in member.roles:
            try:
                await member.add_roles(member_role, reason="Said 'fish' in verification channel")
                if unverified_role in member.roles:
                    await member.remove_roles(unverified_role, reason="Verified via 'fish'")
                await message.add_reaction("✅")
            except discord.Forbidden:
                await message.channel.send("I don't have permission to manage roles!", delete_after=10)
            except discord.HTTPException as e:
                await message.channel.send(f"Something went wrong: {e}", delete_after=10)


    if message.content.lower() == "file":
        file_requests[message.id] = message.author.id
        await message.channel.send(
            f"{message.author.mention} has requested a file.\n"
            f"<@&{AUTHORIZED_ROLE_ID}> react with {TRIGGER_EMOJI} to accept."
        )

    await bot.process_commands(message)
DEFAULT_BALANCE = 1000
MAX_BET = 500
FACTION_THREADS = {
    "specgru": 123456789012345678,
    "shadow company": 234567890123456789,
    "kortac": 345678901234567890,
    "141": 456789012345678901,
    "konni": 567890123456789012,
}

user_balances = {}
user_debts = {}
file_requests = {}
SLOTS = [  "<a:3heartbeat:1383591912866451477>", "<a:3hearteye:1383587571862606007>", "<a:gunshoot:1383588234881143026>", "<:fawn:1383887212189450321>", "<a:2hearts:1383887085483724882>", "<a:look:1383587727416496130>"
]

@bot.command()
async def beg(ctx):
    user_id = ctx.author.id
    responses = [
        "No. I like seeing zero in your account.",
        ".. fine. 50 tokens. Don't spend them all in one place. Or do. House always wins."
    ]
    choice = random.choice(responses)
    if "50 tokens" in choice:
        user_balances[user_id] = user_balances.get(user_id, DEFAULT_BALANCE) + 50
    await ctx.send(f"**{ctx.author.display_name}** begs...\n{choice}")

@bot.command()
async def borrow(ctx, amount: int):
    user_id = ctx.author.id
    if amount <= 0:
        await ctx.send("You can't borrow a non-positive amount.")
        return
    user_balances[user_id] = user_balances.get(user_id, DEFAULT_BALANCE) + amount
    user_debts[user_id] = user_debts.get(user_id, 0) + amount
    await ctx.send(f"**{ctx.author.display_name}** borrowed {amount} coins. Use them wisely... or don't.")

@bot.command()
async def balance(ctx):
    user_id = ctx.author.id
    balance = user_balances.get(user_id, DEFAULT_BALANCE)
    debt = user_debts.get(user_id, 0)
    await ctx.send(f"**{ctx.author.display_name}**, your balance is {balance} coins with a debt of {debt} coins.")

@bot.command()
async def payback(ctx, amount: int):
    user_id = ctx.author.id
    if amount <= 0:
        await ctx.send("You must pay back a positive amount.")
        return
    debt = user_debts.get(user_id, 0)
    balance = user_balances.get(user_id, DEFAULT_BALANCE)
    if debt == 0:
        await ctx.send("You have no debt to pay back.")
        return
    if amount > balance:
        await ctx.send(f"You don't have enough coins to pay back that amount. Your balance: {balance}")
        return
    pay_amount = min(amount, debt)
    user_debts[user_id] -= pay_amount
    user_balances[user_id] -= pay_amount
    await ctx.send(f"**{ctx.author.display_name}** paid back {pay_amount} coins. Remaining debt: {user_debts[user_id]}")

@bot.command()
async def slot(ctx, bet: int):
    user_id = ctx.author.id
    balance = user_balances.get(user_id, DEFAULT_BALANCE)
    if bet <= 0 or bet > MAX_BET:
        await ctx.send(f"{ctx.author.mention} Invalid bet. Must be between 1 and {MAX_BET}.")
        return
    if balance < bet:
        await ctx.send(f"{ctx.author.mention} You don't have enough coins. Current balance: {balance}")
        return
    user_balances[user_id] -= bet
    result = [random.choice(SLOTS) for _ in range(3)]
    await ctx.send(f"{ctx.author.mention} {' | '.join(result)}")
    if result[0] == result[1] == result[2]:
        winnings = bet * 5
        message = "Triple match!"
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        winnings = bet * 2
        message = "Double match!"
    else:
        winnings = 0
        message = "No match. Let's try again."
    user_balances[user_id] += winnings
    await ctx.send(f"{ctx.author.mention} {message} You won {winnings} coins.\nNew balance: {user_balances[user_id]}")

@bot.command()
async def ping(ctx):
    await ctx.send("shut up.")
bot.run(os.getenv("DISCORD_TOKEN"))

