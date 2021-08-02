# AttackOnKamran
<p align="center">
  <img src="images/AttackOnKamran.jpg" />
</p>

## What is this?
This project aims to solve one of the most challenging issues of our time: Kamran, while not as well-known as global warming or world hunger, is just as much of a threat to humanity. Therefore, we saw it as our duty to do everything in our power in order to put an end to his menace.

## What does it do?
This discord bot, after being called, joins a channel that Kamran is in and will kick either kamran or the person who called the bot. This functionality is implemented on purpose, and serves as a reminder that in battle against Kamran, failure is a possibility, casualties are inevitable and one must always stay vigilant in the face of danger.

## Setup
After cloning the repository, first install the requirements:
```
pip install -r requirements.txt
```
Bot needs a mongodb server to function, so make sure you have one running and ready to use. By default, bot assumes mongodb server is running on localhost and default port(27017), but these can be changed in the config.yaml file. You also need to setup a user and database on mongodb for bot to use. Again values for these can be set in config.yaml file.

Next, create a .env file that includes bot's API token, and database password. A sample .env file is included for reference.

Finally, you can run the bot with `python AttackOnKamran.py`:
<p align="center">
  <img src="images/sample_output.jpg" />
</p>

## Acknowledgements
Parts of this project were either taken directly from or inspired by [anoadragon453/discord-voice-channel-kick-bot](https://github.com/anoadragon453/discord-voice-channel-kick-bot)

## Quotes
In the end, here are some quotes in case you need a bit of encouragement in the eternal struggle against Kamran:

> Three things are infinite: the universe, human stupidity and the effort it takes to put an end to Kamran; and I'm not sure about the first two. __-Albert Einstein__

> Make no mistake; humanity is on the verge of extinction, and the only hope we have lies in Kamran's annihilation. __-Captain Levi__

> Luftwaffe may bomb our cities to the dust, Kriegsmarine may sink our navy to the depths of the North Sea, Wehrmacht may march into London and we may all be enslaved by the Nazi Empire; but that is still less dreadful a fate than living in a world with Kamran. __-Winston Churchill__
