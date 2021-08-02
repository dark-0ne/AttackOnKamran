import asyncio
import random
import discord
import yaml
import os

from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables from .env file
load_dotenv()

# Have to set intents so bot can see users in voice channels
intents = discord.Intents.default()
intents.members = True

bot = discord.Client(intents=intents)

# Connect to mongodb, will read db password from env variable
connection_string = "mongodb://AoKBot:" + \
    os.environ.get("MONGO_PWD")+"@localhost"
mongo_client = MongoClient(connection_string)
database = mongo_client["AttackOnKamran"]


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
    voice_client: discord.VoiceClient = await voice_channel.connect()

    async def kick_and_disconnect() -> None:
        """
        Kick the victim and disconnect from voice channel

        Victim's id should be set before running this function in user_to_kick_id outer variable 
        """

        user_to_kick = voice_channel.guild.get_member(user_to_kick_id)

        # Disconnect user (Move to none channel)
        await user_to_kick.edit(voice_channel=None)

        # Update database depeding on whether kamran was kicked or not
        if user_to_kick_id == kamran_uid:
            database.stat.update_one(
                {"username": caller.name+"#"+caller.discriminator}, {"$inc": {"kills": 1}}, upsert=True)
        else:
            database.stat.update_one(
                {"username": caller.name+"#"+caller.discriminator}, {"$inc": {"deaths": 1}}, upsert=True)

        # Leave the channel
        await voice_client.disconnect()

    def after_play(e):
        # We have to hook into asyncio here as voice_client.play
        # runs the Callable it's given without await'ing it
        # Basically this just calls `kick_and_disconnect`
        asyncio.run_coroutine_threadsafe(
            kick_and_disconnect(), bot.loop)

    # Determine if kamran is getting kicked or not
    random_int = random.randint(0, 101)
    print("random number is {}".format(random_int))

    if random_int <= kamran_kick_chance * 100:
        print("Should kick kamran")
        user_to_kick_id = kamran_uid
        random_audio_file = random.choice(kick_kamran_audio_files)
        audio_to_play = os.path.join(os.getcwd(), "audio", random_audio_file)
    else:
        print("Should kick caller")
        user_to_kick_id = caller.id
        audio_to_play = os.path.join(
            os.getcwd(), "audio", kick_caller_audio_file)

    # Play the audio
    # Runs `after_play` when audio has finished playing
    print("playing audio: {}".format(audio_to_play))
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

    # Retrieve caller channel
    voice_channel = await retrieve_caller_channel(caller)
    voice_client: discord.VoiceClient = await voice_channel.connect()

    audio_to_play = os.path.join(os.getcwd(), "audio", celebration_audio_file)

    # Play the audio, and disconnect from channel after it's over
    voice_client.play(discord.FFmpegPCMAudio(audio_to_play),
                      after=voice_client.disconnect)


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
                print("Found kamran in channel")
                return channel


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
                print("Found caller in channel")
                return channel


async def show_leaderboard(target_channel) -> None:
    """
    Send a message containing leaderboard to a target channel

    Args:
        target_channel (discord.TextChannel): Channel object which bot should send the message to 
    
    Returns:
        None
    """

    # Retrieve all user records from database
    result = database.stat.find()

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
        user_kd, key=lambda x: user_kd[x][0]/(user_kd[x][1]+1), reverse=True)

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


@bot.event
async def on_message(message):
    if message.channel.name == bot_commands_channel:
        if message.content == "!leaderboard" or message.content == "!leaderboards":
            print("showing leaderboard")
            await show_leaderboard(message.channel)

        if message.content == "!stats" or message.content == "!stat":
            print("showing stats")
            await show_stats(message.author,message.channel)

        if message.content == "!kamran":
            caller_channel = await retrieve_caller_channel(message.author)
            if caller_channel is None:
                await message.channel.send("You must be in a voice channel to call me!")
                return

            print("calling exterminate")
            result = await find_and_exterminate_kamran(message.author)
            if not result:
                await celebrate(message.author)


@bot.event
async def on_ready():
    print("Connected and logged in. Here I come!")

# Read the config file and store it in a python dictionary
with open("config.yaml") as f:
    config = yaml.safe_load(f.read())

kick_kamran_audio_files = config["kick_kamran_audio_files"]
kick_caller_audio_file = config["kick_caller_audio_file"]
celebration_audio_file = config["celebration_audio_file"]

kamran_uid = config["kamran_uid"]
kamran_kick_chance = config["kamran_kick_chance"]

bot_commands_channel = config["bot-commands-channel"]

# Run the bot with token read from env variable
bot.run(os.environ.get("KAMRAN_TOKEN"))
