# mucklet-bot-python
A python client and bot implementation for Mucklet-API

## Introduction

This is a python implementation of a client for the Mucklet-API which underwrites Wolfery.com. Mucklet-API makes use of Resgate (resgate.io) for managing calls to the API, meaning that any interface to it can be based on Websockets, if the requests are formatted correctly. From there, an interface or a bot can be constructed by implementing a RES client that accesses the Mucklet-API. The objective of the project is to implement a flexible base, in Python, for building bots for Mucklet. 

Based on that, this package does three things: implements a very basic RES client which accesses the Wolfery Resgate server using Websocket, manages the data and calls to the server with a primary 'player' object, and a secondary 'bot character' object which handles the automated processes directly, and provides basic connection and upkeep for the bot with regards to keeping the connection active and the internal data consistent whenever an update event is received by the websocket.

Note that while it is derived from https://github.com/anisus/mucklet-bot, it does not exactly implement that package.

Additionally, four test and demonstration bots are included, illustrating usage of the main package.

#Usage

This module requires credentials for Wolfery.com to operate. In 'Mucklet_Python_Bot_V03.py' are three variables to provide these credentials- remember to strip yours out of the script before sharing your code!

USER takes a user account name, exactly as it appears in the settings.
PASS takes the SHA256 hash of the account password, padded with a trailing '=', https://approsto.com/sha-generator/ includes a tool to generate this hash.
HASH takes anHMAC-SHA256 code of the account password, peppered with 'TheStoryStartsHere'

Further, it presumes the existence of a character intended to be controlled as a bot (unlike Anisus' mucklet-bot, which will attempt to create a character).

BOT_NAME takes a tuple of the first and last name of the character to be controlled as a bot. 

Note that this is fully asynchronous control. If you run a bot client, and also access the character in your browser, for instance, both sets of commands can control the character (You could, for example, use this to produce automatic reactions to certain stimuli while also controlling your character directly- just an idea).

Execution of the 'Mucklet_Python_Bot_V03.py' script will begin the client and initialize a session with Mucklet-API at Wolfery.

As presented, the main application provides for four demonstration bots, imported just prior to the __main__ block.

These four are 'alert_bot', 'command_executing_bot', 'mapping_bot', and 
'demo_function_bot'. For ease of use, all four are imported, but only the one in use needs to be included. The 'alert_bot' and 'demo_function_bot' both require a target character ID, as they send a message to a specific player.

CHAR_TARGET takes this ID in both cases. The main application displays the logged account's characters' names and IDs on start up, for convenience.

Starting a specific bot only requires to start a thread with the primary control script associated with that bot as the thread target. All the maintenence work (keep awake pings, event handling, etc.) is handled by the bot object.

#Making bots

Every bot will need to take a 'player' argument, which allows it to access the API management systems in the main module. Other arguments can be provided as well, as illustrated by the 'command_bot' process.

A set of utility actions (such as 'say', 'go', and 'pose, among others) are available in the character object, and access to the current state (current room, exits, people in the room, etc.) are available through the getState method. 

Current implementation includes simple reporting to the console for non 'address' or 'message' events directed at the bot (though you can change that easily if you wish), and built-in queues for messages and addresses so you can deal with each contact event individually, and in order.

If, however, you wish, the full set of models and collections representing the world as presented by the API to the client is also available, in the char object's .char_models and .char_collections members. They can be a little tricky to navigate at first, though. 

Once a player is logged in, and the bot character defined, these methods allow interaction. Again, see the examples- all those features are used in one or more of them.

Contact FoxLancaster-Okami with questions, issues, suggestions, or requests!



