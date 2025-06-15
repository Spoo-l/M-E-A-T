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
    "SpecGru": 1382555575774220339,
    "Shadow Company": 1382555520388431964,
    "KorTac": 1382555644502216744,
    "141": 1382555452772192399,
    "Konni": 1382556557631426630
}

user_balances = {}
DEFAULT_BALANCE = 100
MAX_BET = 8000
SLOTS = [
    "<a:3heartbeat:1383591912866451477>", "<a:3hearteye:1383587571862606007>", "<a:gunshoot:1383588234881143026>", "<:fawn:1383887212189450321>", "<a:2hearts:1383887085483724882>", "<a:look:1383587727416496130>"
]

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

    class ConfirmView(View):
        def __init__(self):
            super().__init__(timeout=60)
            self.value = None

        @discord.ui.button(label="OK", style=discord.ButtonStyle.success)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == user:
                self.value = True
                await interaction.response.edit_message(content="**File creation started.**", view=None)
                self.stop()
            else:
                await interaction.response.send_message("You are not authorized to confirm this.", ephemeral=True)

    try:
        await user.send("**CREATING FILE. . .** Click the button below to proceed.")
        view = ConfirmView()
        await user.send(view=view)
        await view.wait()

        if not view.value:
            await user.send("You didn’t click OK. Process canceled.")
            return

        await user.send("Building your MILITARY PERSONNEL FILE. Answer each question below. Make sure FACTION is spelled exactly like one of: SpecGru, Shadow Company, KorTac, 141, or Konni.")

        for question, key in questions:
            await user.send(question)
            msg = await bot.wait_for('message', check=check, timeout=120)
            answers[key] = msg.content

        serial_no = generate_random_serial()
        file_no = generate_random_file_no()
        ssn = generate_masked_ssn()
        today = datetime.today().strftime("%d %b %Y")

        def format_file():
            return f"""
===================================
 MILITARY PERSONNEL FILE 
===================================

  NAME:           {answers['name']}
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

        await user.send("Here is your generated file:")
        await user.send(f"```{format_file()}```")

        class EditButton(Button):
            def __init__(self, label, key):
                super().__init__(label=label, style=discord.ButtonStyle.primary)
                self.key = key

            async def callback(self, interaction: discord.Interaction):
                if interaction.user != user:
                    await interaction.response.send_message("This isn't your file to edit.", ephemeral=True)
                    return
                await interaction.response.send_message(f"Re-enter value for {self.key.upper()}:", ephemeral=True)
                try:
                    new_msg = await bot.wait_for('message', check=check, timeout=60)
                    answers[self.key] = new_msg.content
                    await interaction.followup.send(f"{self.key.upper()} updated.", ephemeral=True)
                except asyncio.TimeoutError:
                    await interaction.followup.send("You took too long. Field unchanged.", ephemeral=True)

        class EditView(View):
            def __init__(self):
                super().__init__(timeout=120)
                for _, key in questions:
                    self.add_item(EditButton(label=key.upper(), key=key))

        await user.send("Would you like to edit any field?")
        view = EditView()
        await user.send("Click a button below to edit a specific field:", view=view)
        await asyncio.sleep(60)

        await user.send("Here’s your updated file:")
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
                else:
                    await interaction.response.send_message("This isn't your file to submit.", ephemeral=True)

        submit_view = SubmitView()
        await user.send("Click to submit file to the appropriate faction thread.", view=submit_view)
        await submit_view.wait()

        if submit_view.confirmed:
            faction_name = answers['faction']
            thread_id = FACTION_THREADS.get(faction_name)
            if thread_id:
                thread = bot.get_channel(thread_id)
                if thread:
                    await thread.send(f"```{format_file()}```")
                    await user.send("Your file was sent to the faction thread.")
                else:
                    await user.send("Could not find the thread. Check FACTION spelling.")
            else:
                await user.send("No thread mapped for that FACTION. Try again or recheck guidelines.")
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
async def on_message(message):
    if message.author.bot:
        return


    if message.channel.id == FISH_CHANNEL_ID and message.content.strip().lower() == "fish":
        member_role = discord.utils.get(message.guild.roles, id=MEMBER_ROLE_ID)
        if member_role:
            try:
                await message.author.add_roles(member_role, reason="Said 'Fish' in the designated channel")
                await message.channel.send(f"{message.author.mention} has been assigned the Member role.")
            except discord.Forbidden:
                await message.channel.send("I don’t have permission to assign roles.")
            except discord.HTTPException as e:
                await message.channel.send(f"Role assignment failed: {e}")


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
                await message.channel.send(f"{target_user.mention}, check your DMs.")
                await generate_personnel_file(target_user)
                del file_requests[message.id]
            except discord.Forbidden:
                await message.channel.send(
                    f"{target_user.mention}, I couldn’t DM you. "
                    f"Please enable messages from server members."
                )


@bot.command()
async def ping(ctx):
    await ctx.send("shut up.")


@bot.command()
async def slot(ctx, bet: int):
    user = ctx.author

    if bet <= 0 or bet > MAX_BET:
        await ctx.send(f"{user.mention} Invalid bet. Must be between 1 and {MAX_BET}.")
        return

    if user.id not in user_balances:
        user_balances[user.id] = DEFAULT_BALANCE

    if user_balances[user.id] < bet:
        await ctx.send(f"{user.mention} You don't have enough coins. Current balance: {user_balances[user.id]}")
        return

    user_balances[user.id] -= bet
    result = [random.choice(SLOTS) for _ in range(3)]
    await ctx.send(f"{user.mention} {' | '.join(result)}")

    if result[0] == result[1] == result[2]:
        if result[0] == "7️":
            winnings = bet * 10
            message = "JACKPOT! Triple 7s!"
        else:
            winnings = bet * 5
            message = "Triple match."
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        winnings = bet * 2
        message = "Double match."
    else:
        winnings = 0
        message = "No match. Let's try again."

    user_balances[user.id] += winnings
    await ctx.send(f"{user.mention} {message} You won {winnings} coins.\nNew balance: {user_balances[user.id]}")


@bot.command()
async def balance(ctx):
    balance = user_balances.get(ctx.author.id, DEFAULT_BALANCE)
    await ctx.send(f"{ctx.author.mention} You have {balance} coins.")


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

bot.run(os.getenv("DISCORD_TOKEN"))
