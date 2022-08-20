# mucklet-bot-python
A python client and bot implementation for Mucklet-API

## Introduction

This is a python implementation of a client for the Mucklet-API which underwrites Wolfery.com. Mucklet-API makes use of Resgate (resgate.io) for managing calls to the API, meaning that any interface to it can be based on Websockets, if the requests are formatted correctly. From there, an interface or a bot can be constructed by implementing a RES client that accesses the Mucklet-API. The objective of the project is to implement a flexible base, in Python, for building bots for Mucklet. 

Based on that, this package does three things: implements a very basic RES client which accesses the Wolfery Resgate server using Websocket, manages the data and calls to the server with a primary 'player' object, and a secondary 'bot character' object which handles the automated processes directly, and provides basic connection and upkeep for the bot with regards to keeping the connection active and the internal data consistent whenever an update event is received by the websocket.

Note that while it is derived from https://github.com/anisus/mucklet-bot, it does not exactly implement that package.

Additionally, several test and utility bots are included, illustrating usage of the main package.

# Usage

This module requires credentials for Wolfery.com to operate. In `config_bot.py` are four string variables:

`USER = ""`

`password = ""`

`bt_name = ""`

`bt_surname = ""`


`USER` and `password` are your credientials to log in to the site. `bt_name` and `bt_surname` are the first and last names of the character you want to control as a bot. Remember to strip your credentials out of the script before sharing your code!

This package presumes the existence of a character intended to be controlled as a bot (unlike Anisus' mucklet-bot, which will attempt to create a character).

Note that this is fully asynchronous control. If you run a bot client, and also access the character in your browser, for instance, both sets of commands can control the character (You can, for example, use this to produce automatic reactions to certain stimuli while also controlling your character directly- the say_code bot function does this!).

You can control multiple bot characters at once by creating parallel instances of the package with individual config files for each character. The Volpizza bots work this way- a main script calls 4 independent instances in separate threads, each configured independently for the character controlled by that instance.

Execution of the `command_executing_bot.py` script will begin the client and initialize a session with Mucklet-API at Wolfery.

Currently, the included bot functionality modules are included in `utility_bots.py` and `navigation_bots.py`. At the top of `command_executing_bot.py`, these packages are included, and the functions in them are thus available inside the main script. utility_bots include general purpose functions, such as command and NLP functions, as well as bot methods (like `alert_bot` and `spin_bottle`). `navigation_bots` is exclusively for bots which move around the world, such as the `goto` bot and the `exploration` bot for building the map (included in the package is the file current_map.p, which is a pickle file of the most up-to-date map collected by the bot, and is updated by all actions which move the bot at time of writing).

Once `command_executing_bot.py` is running, the bot can be set to run a module by messaging it. The details of the command interface can be read off by messaging the bot with: `msg bot name=help`. The core idea with the control mode is that the bot has a keyphrase to look for when waiting for a command ('&' by default) which will allow it to know it is receiving an order to begin a function. Other modules running under the main controller need not have this keyphrase, but the main controller is built with it assumed to make partitioning between interaction addresses (such as ordering a drink from Iam Abot in the pizzaria) distinct from execution commands (you can remove this on your own bot though- if you like).

# Making bots

Any other script containing functions representing a bot module can be included at the top of the script, just after the statements for utility_bots and navigation_bots. For instance, if you write a new file `my_bot.py` containing a bot module, you would modify the import section to read:

`from utility_bots import *  `

`from navigation_bots import * ` 

`from my_bot import * `

From there, your software in that package will be available. It is accessed through the management process executed by `command_executing_bot.py`, which is designed to run commands from a library implemented elsewhere, using a common format for detecting execution commands and processing help requests. These commands are included as dictionaries containing a specific set of keys, and you will need to create a new dictionary and entry for each bot module you add. 

For instance, say inside of `my_bot`, you had a main function you would like the bot to be able to execute, called `my_bot_function`. You would create a dictionary object formatted like those already in `command_executing_bot.py` like so:

`my_bot_function_cmd = {'function': #Key phrase for the command- must be present  `

`                      {'phrases':['run', 'do'], #secondary phrases- at least one must be present  `

`                      'eng':'run my bot function?', #english language version for 'did you mean' clarifications  `

`                      'function':my_bot_function, #function to call when the command is executed  `

`                      'description':"Description of your module- &run function" #Description to print for the 'help' call  `

`                }  `

`            }  `


In this dictionary, the key (`'function'`, in this case) is the primary thing that has to be present in your command message to the bot for it to start this module.

`'phrases'` can be one of two things- if it is not empty, it is additional texts that at east one of must be somewhere in the command for the bot to run (so in this example, `&function run` and `&do function` would both start the module, but `&function` would not), if it is left empty, as `'phrases':[]`, then everything after the keyphrase will be fed to the module as a text string argument in the bot object variable `subprocess_flags['command args']` which can be accessed by the module (see the `say_cmd` and corresponding `say_it` module in `utility_bots` for an example of this usage)

`'eng'` is a plain text description of the module for the 'help' function when it needs to ask for a clarification for an uninterpreted commmand.

`'function'` is a pointer to the function which will be called when this module is invoked. Every bot will need to take exactly one `player` argument, which allows it to access the API management systems in the main module. When executed, `command_executing_bot.py` automatically creates a bot object, and passes it to every module as the `player` argument. Additional varibles are always passed to the module as members of the internal `player.subprocess_flags[]` dictionary, which is a member object of the bot object.

Finally, `'description'` is an english description of the module, which requires an example use as you would actually call it, separated from the main text with a '-'.

One this dictionary is created, you can add it to the `COMMANDS` list in `command_executing_bot.py`, which makes it available for scanning by the main process, and makes the module availble to execute.

To actually write your own bot, the `bot_template.py` script is included as a starting point. As written, the sole function within, `demo_bot`, can be added to the `command_executing_bot` pipeline as described above, or run independently, thus providing an example of how you may also write your own stand alone bot as well. Note that if run stand alone, it will immediately start up with its own functionality, and when terminated the process will stop (in `command_executing_bot`, when one module is terminated using `msg bot char=stop` another may be started using the command interface).

This script implements all the basics needed to run a bot using the same standards as in the rest of the included modules, including the basic imports needed to use the `Mucklet_Python_Bot_V03` module for managing the API and the utility_bots package, which includes several fundamental functions.

It includes a single function, `demo_bot(player)`, which highlights the basic process of grabbing command command arguments if started from `command_executing_bot`, a loop that waits until the bot is fully booted to execute (necessary for standalone bots to prevent faults by accessing variables before initialized- when a bot is run under `command_executing_bot`, this is handled by that controller), fetching a stop message for ending the bot operation, getting all the bot's state variables in Wolfery, implementation of a message output queue which is timed to prevent 'you are too active' errors, and accessing and handling direct addressing (in the form of the bot's primary function- an echo server).

Other use cases which interact with the game world in a more nuanced way can be seen inside the `utility_bots` and `navigation_bots` packages. They implement bot functions identically to the template, but with multiple funcitons defined in the same package. Examples of substantially more complex interactive bots can be found in the Volpizza Examples file, which includes the source code (at time of writing) for the pizzaria bots which play blackjack and roulette and take drink and pizza orders. These bots illustrate complex systems managing internal states, interpreting english inputs with NLP methods, and formatting output english language statements as outputs.

I am currently working on implementing bots which play adversarial games (such as tic tac toe or battleship) using backend AIs I have developed in the past, and will be adding these as examples once they're deployment ready.

Contact FoxLancaster-Okami with questions, issues, suggestions, or requests!



