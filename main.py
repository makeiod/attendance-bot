import discord
import os
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv
import database
import datetime
from typing import Literal, Optional
import analytics

# load the environment variables 
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# enable the bot to view messages and members 
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# initialize the bot with the above intents 
bot = commands.Bot(command_prefix='!', intents=intents)

guild_id = os.getenv('GUILD_ID')
GUILD_ID = discord.Object(id=guild_id)

# modal class for optional end of practice notes
class CloseWindow(discord.ui.Modal, title='Practice Notes'):
    notes = discord.ui.TextInput(
        label = "Notes:",
        style = discord.TextStyle.long,
        required = False
    )
    # if practice was started, log all absences along with the coach's name and their notes into the database
    async def on_submit(self, interaction: discord.Interaction):
        name = interaction.user.nick or interaction.user.name
        notes = self.notes.value
        await database.absence_roundup()
        status = await database.log_notes(name, notes)
        if not status:
            await interaction.response.send_message('Window was never opened.', ephemeral=True)
        else:
            await interaction.response.send_message("Window has been closed.", ephemeral=True)

# modal class for athlete attendance form
class FeedbackForm(discord.ui.Modal, title='Feedback or Question'): 
        feedback = discord.ui.TextInput(
             label = "What is your feedback or question from today?", 
             style = discord.TextStyle.short, 
             placeholder = "Why doesn't my cancel work?", 
             required = True)
        # logs the users data in the database if their attempted attendance was valid, if so indicate this in a response message, if there was an invalid attempt at logging, indicate this
        async def on_submit(self, interaction: discord.Interaction):
            user_id = interaction.user.id
            name = interaction.user.nick or interaction.user.name
            timestamp = datetime.datetime.now().isoformat()
            feedback = self.feedback.value
            status = await database.attend(user_id, name, timestamp, feedback)
            if status == 'success':
                await interaction.response.send_message('Your attendance has been logged.', ephemeral=True)
            elif status == 'duplicate':
                 await interaction.response.send_message('You sent the same feedback twice!', ephemeral=True)
            elif status == 'no prac':
                await interaction.response.send_message('There is no practice right now.', ephemeral=True)
            elif status == 'excess':
                 await interaction.response.send_message("You can only log your attendance once.", ephemeral=True)

# infinite button for the athletes to log their attendance, sends the feedback/attendance form when pressed
class InfiniteButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label='Attend', style=discord.ButtonStyle.green, custom_id='tkd_attendance_btn')
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FeedbackForm())

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    # setup the database the moment the bot logs in
    await database.setup_db()
    try: 
        bot.tree.copy_global_to(guild=GUILD_ID)
        synced = await bot.tree.sync(guild=GUILD_ID)
        view = InfiniteButton()
        bot.add_view(view)
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'failed to sync commands: {e}')
    # setup the auto window checker the second the bot logs in
    if not check_window.is_running():
        try:
            check_window.start()
        except RuntimeError:
            print(f'Failed to start attendnace window loop.')

# bot command for coaches to open practice window, ensures that they input a valid session ID from the available choices, logging the session ID in the database when the window opens
@bot.tree.command(name='open_window', description='Open attendance window.')
@app_commands.default_permissions(administrator=True)
@app_commands.choices(term=[app_commands.Choice(name='Fall',value='FALL'), app_commands.Choice(name='Winter', value='WINTER'), 
                            app_commands.Choice(name='Spring Break', value='SPRING_BREAK'), app_commands.Choice(name='Spring',value='SPRING')])
@app_commands.choices(type=[app_commands.Choice(name='Sparring',value='SPARRING'), app_commands.Choice(name='Poomsae', value='POOMSAE'), app_commands.Choice(name='Split', value='SPARRING_POOMSAE')])
async def open_window(interaction: discord.Interaction, term: str, type : str, topic: str):
    timestamp = datetime.datetime.now().isoformat()
    is_active = 1
    status = await database.log_practice(term, type, is_active, timestamp, topic)
    if status:
        await interaction.response.send_message('Success', ephemeral=True)
    else:
        await interaction.response.send_message('There is already an open window.', ephemeral=True)

# automated task for the bot to check whether or not the coach forgot to close the window
@tasks.loop(minutes=30)
async def check_window():
    current = datetime.datetime.now()
    if await database.check_window(current):
        await database.absence_roundup()
        await database.log_notes('Auto-Close', 'None')

# bot command for coaches to close the window, sends a modal with space for notes using the closewindow class 
@bot.tree.command(name='close_window', description='Close attendance window. WAIT UNTIL 30+ MINUTES AFTER PRACTICE OFFICIALLY ENDS.')
@app_commands.default_permissions(administrator=True)
async def close_window(interaction: discord.Interaction):
    await interaction.response.send_modal(CloseWindow())

# bot command for coaches to spawn an attendance button, should only need to be used once
@bot.tree.command(name='attend_button', description='Spawn an attendance button. COACH ONLY')
@app_commands.default_permissions(administrator=True)
async def attend_button(interaction: discord.Interaction):
    view = InfiniteButton()
    await interaction.response.send_message('Log your attendance at practice.', view = view)

async def timeframe_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete a coach's command when asking for a report"""
    year = datetime.date.today().year
    quarters = [
        app_commands.Choice(name='Fall Quarter', value=f'FALL'),
        app_commands.Choice(name='Winter Quarter', value=f'WINTER'),
        app_commands.Choice(name='Spring Quarter', value=f'SPRING'),
        ]
    months = [
        app_commands.Choice(name='January', value=f'{year}-01'),
        app_commands.Choice(name='February', value=f'{year}-02'),
        app_commands.Choice(name='March', value=f'{year}-03'),
        app_commands.Choice(name='April', value=f'{year}-04'),
        app_commands.Choice(name='May', value=f'{year}-05'),
        app_commands.Choice(name='June', value=f'{year}-06'),
        app_commands.Choice(name='September', value=f'{year}-09'),
        app_commands.Choice(name='October', value=f'{year}-10'),
        app_commands.Choice(name='November', value=f'{year}-11'),
        app_commands.Choice(name='December', value=f'{year}-12'),
        ]
    other = [app_commands.Choice(name='Spring Break', value='SPRING_BREAK'), app_commands.Choice(name='Academic Year')]
    all_choices = quarters + months + other
    return [choice for choice in all_choices if current.lower() in choice.name.lower()]

# bot command for coaches to generate an attendnace summary
@bot.tree.command(name='attendance_summary', description='Get a report on an athletes attendance.')
@app_commands.default_permissions(administrator=True)
# coaches can choose from poomsae or sparring, along with the timeframe specified in the autocomplete function
@app_commands.autocomplete(timeframe=timeframe_autocomplete)
@app_commands.choices(type=[app_commands.Choice(name='Sparring',value='SPARRING'), app_commands.Choice(name='Poomsae', value='POOMSAE')])
async def report(
     interaction: discord.Interaction, 
     athlete: discord.Member, 
     timeframe: str,
     type: str,
     format: Optional[Literal['summary', 'graph', 'both']]
     ):
    await interaction.response.defer(ephemeral=True)
    year = datetime.date.today().year
    user_id = athlete.id
    display_name = athlete.nick or athlete.name
    m_name_mapping = {
        f'{year}-01': 'January',
        f'{year}-02': 'February',
        f'{year}-03': 'March',
        f'{year}-04': 'April',
        f'{year}-05': 'May',
        f'{year}-06': 'June',
        f'{year}-09': 'September',
        f'{year}-10': 'October',
        f'{year}-11': 'November',
        f'{year}-12': 'December',
    }
    quarters = ['FALL', 'WINTER', 'SPRING']
    attended, total, attendance_percent = await database.mean_count(timeframe, user_id, type)
    if timeframe in m_name_mapping:
        friendly_name = m_name_mapping.get(timeframe, timeframe)
    elif timeframe in quarters:
        friendly_name = timeframe.title()
    else:
        friendly_name = 'Spring Break'
    if format == 'summary':
        await interaction.followup.send(f'{display_name} attended {attended} practices out of {total} practices and had {attendance_percent} during {friendly_name}.')
    if format == 'graph':
        try:
            file_path = await analytics.simple(user_id, timeframe, type)
            discord_file = discord.File(file_path)
            await interaction.followup.send(file=discord_file)
            os.remove(file_path)
        except FileNotFoundError:
            await interaction.followup.send(f'Could not generate a graph.')
    if format == 'both':
        try:
            file_path = await analytics.simple(user_id, timeframe, type)
            discord_file = discord.File(file_path)
            await interaction.followup.send(file=discord_file)
            os.remove(file_path)
            await interaction.followup.send(f'{display_name} attended {attended} practices out of {total} practices and had {attendance_percent} during {friendly_name}.')
        except FileNotFoundError:
            await interaction.followup.send(f'{display_name} attended {attended} practices out of {total} practices and had {attendance_percent} during {friendly_name}.')



if __name__ == '__main__':
    bot.run(TOKEN)

