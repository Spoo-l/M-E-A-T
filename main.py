import os
import random
import asyncio
import discord
from discord.ext import commands
from discord.ui import View, Button

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

AUTHORIZED_ROLE_ID = 1378164944666755242
TRIGGER_EMOJI = "✅"
FISH_CHANNEL_ID = 1382936876985483337
MEMBER_ROLE_ID = 1378204196477730836
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
def format_file():
    today = datetime.now().strftime("%Y-%m-%d")
    serial_no = generate_random_serial()
    file_no = generate_random_file_no()
    ssn = generate_masked_ssn()
    
    return f"""
===================================
 MILITARY PERSONNEL FILE 
===================================
  NAME:           {answers['name']}
  USERNAME:       {answers['username']}
  SERIAL NO.:     {serial_no}

  FACTION:        {answers['faction']}
-----------------------------------

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

-----------------------------------

  FILED BY:          MX-4719-E
  DATE FILED:        {today}
"""

class EditButton(Button):
    def __init__(self, label: str, key: str):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.key = key

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user
        await interaction.response.send_message(f"Please enter new value for **{self.key.upper()}**:", ephemeral=True)
        def check(m):
            return m.author == user and isinstance(m.channel, discord.DMChannel)
        try:
            msg = await bot.wait_for("message", timeout=120.0, check=check)
        except asyncio.TimeoutError:
            await user.send("You took too long to respond. Edit cancelled.")
            return
        if hasattr(interaction.client, "file_answers"):
            answers = interaction.client.file_answers.get(user.id, {})
            answers[self.key] = msg.content
            interaction.client.file_answers[user.id] = answers
        else:
            interaction.client.file_answers = {user.id: {self.key: msg.content}}
        await user.send(f"Updated **{self.key.upper()}** to: {msg.content}")

class EditView(View):
    def __init__(self, keys):
        super().__init__(timeout=120)
        for key in keys:
            self.add_item(EditButton(label=key.upper(), key=key))

class SubmitView(View):
    def __init__(self, user):
        super().__init__(timeout=60)
        self.confirmed = False
        self.user = user

    @discord.ui.button(label="Submit File", style=discord.ButtonStyle.success)
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("This isn't your file to submit.", ephemeral=True)
            return
        self.confirmed = True
        await interaction.response.send_message("File submitted.", ephemeral=True)
        self.stop()

async def generate_personnel_file(user: discord.Member):
    questions = [
        ("name", "What is your full name?"),
        ("age", "What is your age?"),
        ("rank", "What is your rank?"),
        ("faction", "What faction do you belong to? (SpecGru, Shadow Company, KorTac, 141, Konni)"),
    ]
    try:
        await user.send("**CREATING FILE...** Please answer the following questions:")
        answers = {}
        def check(m):
            return m.author == user and isinstance(m.channel, discord.DMChannel)
        for key, prompt in questions:
            await user.send(prompt)
            msg = await bot.wait_for("message", timeout=120.0, check=check)
            answers[key] = msg.content.strip()
        bot.file_answers = getattr(bot, "file_answers", {})
        bot.file_answers[user.id] = answers
        await user.send("Would you like to edit any field? If yes, click a button below. If no, wait for 2 minutes or type 'no'.")
        keys = [key for key, _ in questions]
        view = EditView(keys)
        await user.send("Click a button below to edit a specific field:", view=view)
        def edit_check(i):
            return i.user == user and i.message.channel.type == discord.ChannelType.private
        try:
            await view.wait()
            no_msg = await bot.wait_for("message", timeout=120.0, check=lambda m: m.author == user and m.channel.type == discord.ChannelType.private and m.content.lower() == "no")
            if no_msg:
                view.stop()
        except asyncio.TimeoutError:
            pass
        answers = bot.file_answers.get(user.id, answers)
        await user.send("Here’s your updated file:")
        await user.send(f"```{format_file(answers)}```")
        submit_view = SubmitView(user)
        await user.send("Click the button to submit your file to the appropriate faction thread.", view=submit_view)
        await submit_view.wait()
        if submit_view.confirmed:
            faction_name = answers.get('faction', '').lower()
            thread_id = FACTION_THREADS.get(faction_name)
            if thread_id:
                thread = bot.get_channel(thread_id)
                if thread:
                    await thread.send(f"```{format_file(answers)}```")
                    await user.send("Your file was sent to the faction thread.")
                else:
                    await user.send("Could not find the thread. Please check the faction spelling.")
            else:
                await user.send("No thread mapped for that faction. Try again or check spelling.")
        else:
            await user.send("You didn’t submit the file.")
    except asyncio.TimeoutError:
        await user.send("You took too long to respond. Try again later.")
    except discord.Forbidden:
        pass

@bot.event
async def on_ready():
    print(f"Bot is online! Logged in as {bot.user}")

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
        await message.channel.send(f"{message.author.mention} has requested a file.\n<@&{AUTHORIZED_ROLE_ID}> react with {TRIGGER_EMOJI} to accept.")
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
                await message.channel.send(f"{target_user.mention}, check your DMs.")
                await generate_personnel_file(target_user)
                del file_requests[message.id]
            except discord.Forbidden:
                await message.channel.send(f"{target_user.mention}, I couldn’t DM you. Please enable messages from server members.")

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
