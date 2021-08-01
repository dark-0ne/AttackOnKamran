import asyncio
import random
import discord
import yaml
import os
import operator
from dotenv import load_dotenv
from pymongo import MongoClient

from typing import Optional, List, Tuple

# Conversion from sec to min
MIN = 60

load_dotenv()

intents = discord.Intents.default()
intents.members = True

bot = discord.Client(intents=intents)

# Connect to mongodb
connection_string = "mongodb://AoKBot:" + \
    os.environ.get("MONGO_PWD")+"@localhost"
mongo_client = MongoClient(connection_string)
database = mongo_client["AttackOnKamran"]


async def start_a_tour(username):
    # Retrieve active voice channel
    voice_channel = await retrieve_kamran_channel()
    if voice_channel is None:
        print("Kamran not found in any channel. Hooray!")
        voice_channel = await retrieve_caller_channel(username.split('#')[0])

    # Join the voice channel
    voice_client: discord.VoiceClient = await voice_channel.connect()

    async def kick_member_and_disconnect():
        if not kamran_found:
            await voice_client.disconnect()
            return

        if len(members_to_kick) == 0:
            print("Punishing user {}".format(username))
            member_to_kick = voice_channel.guild.get_member_named(username)
            await member_to_kick.edit(voice_channel=None)
            database.stat.update_one({"username": username}, {
                                     "$inc": {"deaths": 1}}, upsert=True)

        for victim_user_id in members_to_kick:
            member_to_kick = voice_channel.guild.get_member(victim_user_id)
            print("Kicking member '%s'..." % (member_to_kick,))
            await member_to_kick.edit(voice_channel=None)
            database.stat.update_one({"username": username}, {
                                     "$inc": {"kills": 1}}, upsert=True)
            database.stat.update_one({"username": "kamran#8868"}, {
                                     "$inc": {"deaths": 1}}, upsert=True)

        # Leave the channel
        await voice_client.disconnect()

        # Announce that the tour is beginning

    def after_play(e):
        # We have to hook into asyncio here as voice_client.play
        # runs the Callable it's given without await'ing it
        # Basically this just calls `kick_member_and_disconnect`
        asyncio.run_coroutine_threadsafe(
            kick_member_and_disconnect(), bot.loop)

    # Play the audio
    # Runs `after_play` when audio has finished playing
    members_to_kick = []
    kamran_found = False
    members_in_channel = list(voice_channel.voice_states.keys())

    audio_to_play = dead_audio_clip_filepath
    for victim_user_id, percentage in targeted_victims:
        # Check that this user is currently in the voice channel
        if victim_user_id not in members_in_channel:
            continue

        audio_to_play = laugh_audio_clip_filepath
        kamran_found = True
        random_int = random.randint(0, 101)
        if random_int <= percentage * 100:
            print("found victim: {}".format(victim_user_id))
            members_to_kick.append(victim_user_id)

    if len(members_to_kick) > 0:
        print("should play kick")
        audio_to_play = random.choice(kick_audio_clip_filepath)
    print("playing audio: {}".format(audio_to_play))
    voice_client.play(discord.FFmpegPCMAudio(audio_to_play), after=after_play)


async def retrieve_kamran_channel():
    """Scans all active voice channels the bot can see and returns a random one"""
    # Get all channels the bot can see
    channels = [c for c in bot.get_all_channels()]

    # Randomize them so we don't pick the same channel every time
    random.shuffle(channels)

    # Check if each channel is a VoiceChannel with active members
    for channel in channels:
        if isinstance(channel, discord.VoiceChannel):
            if len(channel.members) > 0:
                members_in_channel = list(channel.voice_states.keys())
                for victim_user_id, percentage in targeted_victims:
                    if victim_user_id in members_in_channel:
                        print("Found active channel")
                        return channel


async def retrieve_caller_channel(username):
    """Scans all active voice channels the bot can see and returns a random one"""
    # Get all channels the bot can see
    channels = [c for c in bot.get_all_channels()]

    # Randomize them so we don't pick the same channel every time
    random.shuffle(channels)

    # Check if each channel is a VoiceChannel with active members
    for channel in channels:
        if isinstance(channel, discord.VoiceChannel):
            if len(channel.members) > 0:
                members_in_channel = [user.name for user in channel.members]
                print(members_in_channel)
                print(username)
                if username in members_in_channel:
                    print("Found active channel")
                    return channel


async def show_leaderboard(message):
    result = database.stat.find()
    total_kills = 0
    total_deaths = 0
    user_kd = {}
    for item in result:
        if item["username"] != "kamran#8868":
            try:
                user_kills = item["kills"]
                total_kills += user_kills
            except KeyError:
                user_kills = 0
            try:
                user_deaths = item["deaths"]
                total_deaths += user_deaths
            except KeyError:
                user_deaths = 0

            user_kd[item['username']] = (user_kills, user_deaths)

    message_to_send = "```\nIn our battle to save humanity, we have slain Kamran {} times, and {} of our comrades have fallen to his evil!\n\nMost exterminations have been achieved by:\n\n".format(
        total_kills, total_deaths)
    top_killers = sorted(user_kd, key=lambda x: user_kd[x][0],reverse=True)
    top_deaths = sorted(user_kd, key=lambda x: user_kd[x][1],reverse=True)
    top_kd = sorted(user_kd, key=lambda x: user_kd[x][0]/(user_kd[x][1]+1),reverse=True)

    for user in top_killers[:3]:
        message_to_send += "{}: {}\n".format(user,user_kd[user][0])

    message_to_send += "\nMost sacrifices have been made by: \n\n"
    for user in top_deaths[:3]:
        message_to_send += "{}: {}\n".format(user,user_kd[user][1])

    message_to_send += "\nHighest K/D Ratio: \n\n"
    for user in top_kd[:3]:
        try:
            message_to_send += "{}: {:.2f}\n".format(user,user_kd[user][0]/user_kd[user][1])
        except ZeroDivisionError:
            message_to_send += "{}: **Immortal**\n".format(user)

    message_to_send += "```"
    await message.channel.send(message_to_send)


# Text command to have bot join channel
@bot.event
async def on_message(message):
    if message.channel.name == "bot-webhook":
        sleep_amount = random.randint(trigger_sleep_min, trigger_sleep_max)
        print("Trigger phrase ACTIVATED! Waiting %d seconds..." %
              (sleep_amount,))
        await asyncio.sleep(sleep_amount)

        # Try to kick a user from a channel
        print("Triggered!")
        await message.delete()
        await start_a_tour(message.content)
    if message.channel.name == "bot-commands":
        if message.content == "!leaderboard":
            print("showing leaderboard")
            await show_leaderboard(message)

        if message.content == "!kamran":
            print("calling shit")
            await start_a_tour(message.author.name+"#"+message.author.discriminator)


@bot.event
async def on_ready():
    print("Connected and logged in. Here I come!")

# Read the config file and store it in a python dictionary
with open("config.yaml") as f:
    config = yaml.safe_load(f.read())

# Config options
picture_folder = config.get("picture_folder", "")
picture_amount = config.get("picture_amount", 1)
picture_captions = config.get("picture_captions", [])
before_picture_messages = config.get("before_picture_messages", [])
after_picture_messages = config.get("after_picture_messages", [])
between_picture_delay = config.get("between_picture_delay", 0)

targeted_victims: List[Tuple[int, float]] = config.get("targeted_victims", [])

trigger_phrase = config.get("trigger_phrase", "")
trigger_sleep_min = config.get("trigger_sleep_min", 0)
trigger_sleep_max = config.get("trigger_sleep_max", 0)
allowed_command_user_ids = config["allowed_command_user_ids"]

kick_audio_clip_filepath = config["kick_audio_clip_filepath"]
laugh_audio_clip_filepath = config["laugh_audio_clip_filepath"]
dead_audio_clip_filepath = config["dead_audio_clip_filepath"]

bot.run(os.environ.get("KAMRAN_TOKEN"))
