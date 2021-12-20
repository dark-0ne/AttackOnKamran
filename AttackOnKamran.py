import asyncio
import random
import discord
import yaml
import os
import logging
import csv

from helpers import PseudoRandomGenerator

from dotenv import load_dotenv
from pymongo import MongoClient


# Have to set intents so bot can see users in voice channels
intents = discord.Intents.default()
intents.members = True

bot = discord.Client(intents=intents)


async def find_and_exterminate_kamran(caller) -> bool:
    """
    Joins the channel kamran is in, and will either kick him or the person who called the bot.

    Args:
        User (discord.User): User object that invoked the command

    Returns:
        Result (bool): Returns true kamran found in any channels, false otherwise
    """

    # Retrieve active voice channel
    voice_channel = await retrieve_kamran_channel()

    # Return false if kamran is not in any channels
    if voice_channel is None:
        return False

    # Join kamran's channel
    logging.info("Joining %s",voice_channel.name)
    voice_client: discord.VoiceClient = await voice_channel.connect()

    async def kick_and_disconnect() -> None:
        """
        Kick the victim and disconnect from voice channel

        Victim's id should be set before running this function in user_to_kick_id outer variable 
        """

        user_to_kick = voice_channel.guild.get_member(user_to_kick_id)

        # Disconnect user (Move to none channel)
        logging.info("Kicking %s",user_to_kick.name)
        await user_to_kick.edit(voice_channel=None)

        # Update database depeding on whether kamran was kicked or not
        if user_to_kick_id == kamran_uid:
            logging.info("Increasing %s's kills by 1",caller)
            database.stat.update_one(
                {"username": caller.name+"#"+caller.discriminator}, {"$inc": {"kills": 1}}, upsert=True)
        else:
            logging.info("Increasing %s's deaths by 1",caller)
            database.stat.update_one(
                {"username": caller.name+"#"+caller.discriminator}, {"$inc": {"deaths": 1}}, upsert=True)

        # Leave the channel
        logging.info("Leaving %s",voice_channel.name)
        await voice_client.disconnect()

    def after_play(e):
        # We have to hook into asyncio here as voice_client.play
        # runs the Callable it's given without await'ing it
        # Basically this just calls `kick_and_disconnect`
        asyncio.run_coroutine_threadsafe(
            kick_and_disconnect(), bot.loop)

    # Determine if kamran is getting kicked or not

    logging.info("Chance to kick kamran: %f",PRG.current_chance)
    if PRG.get_bool():
        logging.info("Should kick %s",caller.name)
        user_to_kick_id = caller.id
        audio_to_play = os.path.join(
            os.getcwd(), "audio", kick_caller_audio_file)
    else:
        logging.info("Should kick Kamran")
        user_to_kick_id = kamran_uid
        random_audio_file = random.choice(kick_kamran_audio_files)
        #random_audio_file = kick_kamran_audio_files[-1]
        audio_to_play = os.path.join(os.getcwd(), "audio", random_audio_file)

    # Play the audio
    # Runs `after_play` when audio has finished playing
    logging.info("Playing audio: %s",audio_to_play)
    voice_client.play(discord.FFmpegPCMAudio(audio_to_play), after=after_play)
    return True


async def celebrate(caller) -> None:
    """
    Joins the channel caller is in, and will play a celebration audio

    Args:
        caller (discord.User): User object that invoked the command

    Returns:
        None
    """
    async def disconnect() -> None:
        logging.info("Leaving %s",voice_channel.name)
        await voice_client.disconnect()

    def after_play(e):
        asyncio.run_coroutine_threadsafe(
            disconnect(), bot.loop)
    # Retrieve caller channel
    voice_channel = await retrieve_caller_channel(caller)

    logging.info("Joining %s",voice_channel.name)
    voice_client: discord.VoiceClient = await voice_channel.connect()

    audio_to_play = os.path.join(os.getcwd(), "audio", celebration_audio_file)

    # Play the audio, and disconnect from channel after it's over
    logging.info("Playing audio: %s",audio_to_play)
    voice_client.play(discord.FFmpegPCMAudio(audio_to_play),
            after=after_play)


async def retrieve_kamran_channel() -> discord.VoiceChannel:
    """
    Retrieves the voice channel kamran is in

    Returns:
        channel (discord.VoiceChannel): Channel that kamran is in, will return None if kamran not found
    """
    channels = [c for c in bot.get_all_channels()]

    for channel in channels:
        # Check only voice channels
        if isinstance(channel, discord.VoiceChannel):
            members_in_channel = [user.id for user in channel.members]
            if kamran_uid in members_in_channel:
                logging.info("Found Kamran in %s",channel.name)
                return channel


    logging.info("Kamran not found in any channels")


async def retrieve_caller_channel(caller) -> discord.VoiceChannel:
    """
    Retrieves the voice channel caller is in

    Args:
        caller (discord.User): User object for caller

    Returns:
        channel (discord.VoiceChannel): Channel that kamran is in, will return None if caller not found
    """
    
    channels = [c for c in bot.get_all_channels()]

    for channel in channels:
        # Check only voice channels
        if isinstance(channel, discord.VoiceChannel):
            members_in_channel = [user.id for user in channel.members]
            if caller.id in members_in_channel:
                logging.info("Found %s in %s",caller.name,channel.name)
                return channel

    logging.info("%s not found in any channels",caller.name)

async def show_leaderboard(target_channel) -> None:
    """
    Send a message containing leaderboard to a target channel

    Args:
        target_channel (discord.TextChannel): Channel object which bot should send the message to 
    
    Returns:
        None
    """

    # Retrieve all user records from database
    result = list(database.stat.find())
    logging.info("Retrieved %d records from database",len(result))

    total_kills = 0
    total_deaths = 0

    # Dict for storing each user record in the format of {username: (kills,deaths)}
    user_kd = {}
    for user in result:
        # In case there is no kills or deaths record for user (KeyError), just assume 0
        try:
            user_kills = user["kills"]
            total_kills += user_kills
        except KeyError:
            user_kills = 0
        try:
            user_deaths = user["deaths"]
            total_deaths += user_deaths
        except KeyError:
            user_deaths = 0

        user_kd[user['username']] = (user_kills, user_deaths)

    # Message header
    message_to_send = "⠀\nIn our battle to save humanity, we have slain Kamran {} times, and {} of our comrades have fallen to his evil!\n\nMost exterminations have been achieved by:\n".format(
        total_kills, total_deaths)
    
    # Sort dict keys based on their values to find top users
    top_killers = sorted(user_kd, key=lambda x: user_kd[x][0], reverse=True)
    top_deaths = sorted(user_kd, key=lambda x: user_kd[x][1], reverse=True)
    top_kd = sorted(
        user_kd, key=lambda x: user_kd[x][0]/(user_kd[x][1]+0.001), reverse=True)

    # Add top killers to message
    for user in top_killers[:3]:
        message_to_send += "\t\t-- **{}**: {}\n".format(
            user.split("#")[0], user_kd[user][0])

    # Add top deaths to message
    message_to_send += "\nMost sacrifices have been made by: \n"
    for user in top_deaths[:3]:
        message_to_send += "\t\t-- *{}*: {}\n".format(
            user.split("#")[0], user_kd[user][1])

    # Add top kd to message
    message_to_send += "\nHighest K/D Ratio: \n"
    for user in top_kd[:3]:
        try:
            message_to_send += "\t\t-- {}: {:.2f}\n".format(
                user.split("#")[0], user_kd[user][0]/user_kd[user][1])
        # Assign Immortal value to people with 0 deaths
        except ZeroDivisionError:
            message_to_send += "\t\t-- ***{}: Immortal***\n".format(
                user.split("#")[0])

    logging.info("Sending leaderboard to %s",target_channel.name)
    await target_channel.send(message_to_send)


async def show_stats(user,target_channel)->None:
    """
    Send a message containing stats of a user to a target channel

    Args:
        caller (discord.User): User object whom to show stats for 
        target_channel (discord.TextChannel): Channel object which bot should send the message to 
    
    Returns: 
        None
    """

    # Retrieve user record from database
    result = database.stat.find_one(
        {"username":user.name+"#"+user.discriminator})
    if result is None:
        message_to_send = "⠀\nYou have not contributed to exterminating Kamran so far. To get started, send !kamran next time you see him in any channel!"
        await target_channel.send(message_to_send)
        return 

    # Assign default values if user does not have them
    if "kills" not in result:
        result["kills"] = 0
    if "deaths" not in result:
        result["deaths"] = 0

    # Construct message to be shown
    try:
        message_to_send = "⠀\nYou have slain Kamran **{}** times, and sacrificed yourself *{}* times. Your K/D ratio is {:.2f}. Keep up the good work!".format(
            result['kills'], result['deaths'], result['kills']/result['deaths'])
    except ZeroDivisionError:
        # Assign Immortal value to user's kd if they have no death
        message_to_send = "⠀\nYou have slain Kamran **{}** times, and sacrificed yourself *{}* times. You are ***Immortal***, so keep up the good work!".format(
            result['kills'], result['deaths'])

    await target_channel.send(message_to_send)


async def show_quote(target_channel)->None:
    """
    Send a message containing a quote

    Quotes are read from quote.yaml file

    Args:
        target_channel (discord.TextChannel): Channel object which bot should send the message to 
    
    Returns: 
        None
    """

    # Get a random quote from quotes list
    quote, quotee = random.choice(quotes)

    # Construct and format message
    message_to_send = "⠀\n" + quote + " *-" + quotee + "*"

    await target_channel.send(message_to_send)


async def handle_webhook(token,caller_id) -> None:
    """
    Handles incoming webhook

    Will check token sent by webhook, and if it is confirmed, will call find_and_exterminate_kamran with appropriate parameters

    Args:
        token (str): Token provided by webhook

    Returns:
        None
    """

    caller = await bot.fetch_user(caller_id)
    # Check if token is valid
    if token not in tokens:
        logging.warning("User %s tried calling through webhook with invalid token.",caller)
        await caller.send("You tried calling me through webhook, but your token was invalid. Send !token to receive your token.")
        return

    caller = await bot.fetch_user(tokens[token])
    logging.info("User %s called exterminate through webhook.",caller)


    caller_channel = await retrieve_caller_channel(caller)
    if caller_channel is None:
        logging.warning("%s called !kamran but was not in any channel",message.author.name)
        await caller.send("You must be in a voice channel to call me!")
        return

    logging.info("%s called !kamran from webhook",caller)
    result = await find_and_exterminate_kamran(caller)
    if not result:
        logging.info("Kamran was not found in any channels; calling celebrate")
        await celebrate(caller)

        
    
@bot.event
async def on_message(message):
    # Handle commands
    if isinstance(message.channel, discord.TextChannel):
        if message.channel.name == bot_commands_channel:
            if message.content == "!leaderboard" or message.content == "!leaderboards":
                logging.info("%s called show_leaderboard in %s",message.author.name,message.channel.name)
                await show_leaderboard(message.channel)

            if message.content == "!stats" or message.content == "!stat":
                logging.info("%s called show_stats in %s",message.author.name,message.channel.name)
                await show_stats(message.author,message.channel)

            if message.content == "!kamran":
                caller_channel = await retrieve_caller_channel(message.author)
                if caller_channel is None:
                    logging.warning("%s called !kamran but was not in any channel",message.author.name)
                    await message.channel.send("You must be in a voice channel to call me!")
                    return

                logging.info("%s called !kamran in %s",message.author.name,message.channel.name)
                result = await find_and_exterminate_kamran(message.author)
                if not result:
                    logging.info("Kamran was not found in any channels; calling celebrate")
                    await celebrate(message.author)
            if message.content == "!quote":
                logging.info("%s called !quote in %s",message.author.name,message.channel.name)
                await show_quote(message.channel)

            if message.content == "!channels":
                channels = [c for c in bot.get_all_channels()]

                for channel in channels:
                    if channel.name == "bot-webook":
                        print(channel.id)
                        print(type(channel.id))


        # Handle messages send to webhook channel
        if message.channel.id == 871847839133749359:
            token, uid = message.content.split("#")
            await handle_webhook(token, uid)

@bot.event
async def on_ready():
    logging.info("Connected and logged in. Death to Kamran!")

# Setup logging
# TODO: different logging levels and formattings for each handler
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("info.log"),
        logging.StreamHandler()
    ]
)

# Load environment variables from .env file
load_dotenv()

# Read the config file and store it in a python dictionary
with open("config.yaml") as f:
    config = yaml.safe_load(f.read())

kick_kamran_audio_files = config["kick_kamran_audio_files"]
kick_caller_audio_file = config["kick_caller_audio_file"]
celebration_audio_file = config["celebration_audio_file"]

kamran_uid = config["kamran_uid"]

bot_commands_channel = config["bot_commands_channel"]

PRG = PseudoRandomGenerator(step=config['caller_kick_chance_step'])

mongo_address = config["mongo_address"]
mongo_username = config["mongo_username"]
mongo_db_name = config["mongo_db_name"]

tokens = {}
# Read user tokens for webhook
with open("user_tokens.yaml") as f:
    user_tokens = yaml.safe_load(f.read())["user-tokens"]
    for user,token in user_tokens:
        tokens[token] = user

# Read quotes from csv file
quotes = []
with open("quote.csv") as f:
    csv_reader = csv.reader(f, delimiter=',')
    for row in csv_reader:
        quotes.append(row)

# Connect to mongodb, will read db password from env variable
connection_string = "mongodb://" + mongo_username + ":" + \
    os.environ.get("MONGO_PWD")+"@"+mongo_address
mongo_client = MongoClient(connection_string)
database = mongo_client[mongo_db_name]

# Run the bot with token read from env variable
bot.run(os.environ.get("KAMRAN_TOKEN"))
