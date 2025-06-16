import os
import random
import asyncio
import discord
from discord.ext import commands
from discord.ui import Button, View

AUTHORIZED_ROLE_ID = 1378164944666755242 
TRIGGER_EMOJI = "<:Happi:1381476760708714617>"
FISH_CHANNEL_ID = 1382936876985483337  
MEMBER_ROLE_ID = 1378204196477730836  
DEFAULT_BALANCE = 1000
MAX_BET = 500
SLOTS = [  "<a:3heartbeat:1383591912866451477>", "<a:3hearteye:1383587571862606007>", "<a:gunshoot:1383588234881143026>", "<:fawn:1383887212189450321>", "<a:2hearts:1383887085483724882>", "<a:look:1383587727416496130>"
]

FACTION_THREADS = {
    "SpecGru": 123456789012345678,
    "Shadow Company": 234567890123456789,
    "KorTac": 345678901234567890,
    "141": 456789012345678901,
    "Konni": 567890123456789012,
}

file_requests = {} 
user_balances = {} 

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)


def generate_random_serial():
    return ''.join(str(random.randint(0, 9)) for _ in range(7))


def generate_random_file_no():
    letters = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))
    numbers = ''.join(random.choices('0123456789', k=2))
    return f"{letters}-{numbers}"


def generate_masked_ssn():
    last_four = ''.join(str(random.randint(0, 9)) for _ in range(4))
    return f"***-**-{last_four}"


def format_file(answers):
    lines = [f"{key.upper()}: {value}" for key, value in answers.items()]
    return "\n".join(lines)


class EditButton(Button):
    def __init__(self, label: str, key: str):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.key = key

    async def callback(self, interaction: discord.Interaction):
        view: EditView = self.view
        user = interaction.user

        if user != view.user:
            await interaction.response.send_message("This isn't your edit menu.", ephemeral=True)
            return

        await interaction.response.send_message(f"Please enter a new value for **{self.key.upper()}**:", ephemeral=True)

        def check(m):
            return m.author == user and isinstance(m.channel, discord.DMChannel)

        try:
            msg = await bot.wait_for('message', check=check, timeout=120)
            view.answers[self.key] = msg.content.strip()
            await interaction.followup.send(f"Updated **{self.key.upper()}** to: {msg.content}", ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.followup.send("You took too long to respond. Edit cancelled.", ephemeral=True)


class EditView(View):
    def __init__(self, user, answers, timeout=120):
        super().__init__(timeout=timeout)
        self.user = user
        self.answers = answers
        for key in answers.keys():
            self.add_item(EditButton(label=key.upper(), key=key))


class SubmitView(View):
    def __init__(self, user, timeout=60):
        super().__init__(timeout=timeout)
        self.user = user
        self.confirmed = False

    @discord.ui.button(label="Submit File", style=discord.ButtonStyle.success)
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("This isn't your file to submit.", ephemeral=True)
            return

        self.confirmed = True
        await interaction.response.send_message("File submitted.", ephemeral=True)
        self.stop()


async def generate_personnel_file(user: discord.Member):
    answers = {
        "name": user.name,
        "serial": generate_random_serial(),
        "file_no": generate_random_file_no(),
        "ssn": generate_masked_ssn(),
        "faction": "141",
    }

    try:
        await user.send("**CREATING FILE...**")

        await user.send(f"Here is your current personnel file:\n```{format_file(answers)}```")


        await user.send("Would you like to edit any field? Click a button below to edit a specific field:")

        edit_view = EditView(user=user, answers=answers)
        await user.send(view=edit_view)
        
        await edit_view.wait()

        await user.send(f"Here’s your updated file:\n```{format_file(answers)}```")


        submit_view = SubmitView(user=user)
        await user.send("Click to submit file to the appropriate faction thread.", view=submit_view)
        await submit_view.wait()

        if submit_view.confirmed:
            faction_name = answers.get('faction', None)
            if faction_name:
                thread_id = FACTION_THREADS.get(faction_name)
                if thread_id:
                    thread = bot.get_channel(thread_id)
                    if thread:
                        await thread.send(f"```{format_file(answers)}```")
                        await user.send("Your file was sent to the faction thread.")
                    else:
                        await user.send("Could not find the thread. Check FACTION spelling or thread setup.")
                else:
                    await user.send("No thread mapped for that FACTION. Try again or recheck guidelines.")
            else:
                await user.send("Faction not specified in your file. Cannot send.")
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


bot.run(os.getenv("DISCORD_TOKEN"))
