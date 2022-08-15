####
#Command-executing bot
#   A bot which executes commands sent by address from another player
#   has several commands and a keyword check to execute them
####

import websocket
import json
import threading
import math,time,random
import pickle,glob
from difflib import SequenceMatcher

########
#This next section defines the commands for the main interpreter
########

from utility_bots import *
from navigation_bots import *
from talkbot import *

time_cmd = {'time': #Key phrase for the command- must be present
                {'phrases':['tell', 'what'], #secondary phrases- at least one must be present
                'eng':'What time is it?', #english language version for 'did you mean' clarifications
                'function':time_cmd, #function to call when the command is executed
                'description':"Announce the current time over the communication channel- &tell time" #Description to print for the 'help' call
                }
            }

#Same as above
go_cmd = {'go':
                {'phrases':['out', 'away'],
                'eng':'Go away?',
                'function':leave_cmd,
                'description':"Leave the room- &go away"
                }
            }

goto_cmd = {'goto':
                {'phrases':[],
                'eng':'Goto somewhere?',
                'function':get_GOTO,
                'description':"Navigate to a specified location- &goto club"
                }
            }

sleep_cmd = {'sleep':
                {'phrases':['go','to'],
                'eng':'Go to ssleep?',
                'function':go_sleep,
                'description':"Put the bot to sleep- &go to sleep"
                }
            }

say_cmd = {'say':
                {'phrases':[],
                'eng':'Say something?',
                'function':say_it,
                'description':"Say words- &say hello"
                }
            }

dildo_cmd = {'dildo':
                {'phrases':[],
                'eng':'use dildo?',
                'function':do_dildo,
                'description':"Activate dildo mode- &dildo for 45 seconds every 10 seconds"
                }
            }

watch_cmd = {'watch':
                {'phrases':['room','space'],
                'eng':'Watch this space?',
                'function':alert_bot,
                'description':"Watch a room and alert the issuer when a new character enters- &watch this space"
                }
            }

set_comm_cmd = {'set_comm':
                {'phrases':[],
                'eng':'Set communication mode?',
                'function':set_comm,
                'description':"Switch between Address(addr) and Message(msg) control- &set_comm addr"
                }
            }

roll_dice_cmd = {'roll':
                {'phrases':[],
                'eng':'Roll dice?',
                'function':roll_dice,
                'description':"Just roll some dice- &roll 4d6+2d8"
                }
            }

explore_cmd = {'explore':
                {'phrases':['go'],
                'eng':'Go exloring?',
                'function':exploration_bot,
                'description':"explore the map- &go explore"
                }
            }

train_time_cmd = {'train':
                {'phrases':['time','since'],
                'eng':'Get time since woke up on train?',
                'function':time_since_train,
                'description':"get time since first woke up- &time since train"
                }
            }

say_code_cmd = {'saycode':
                {'phrases':[],
                'eng':'Say something in weird type?',
                'function':say_code,
                'description':"say something in a weird typeface- &saycode something to say weird"
                }
            }

say_gal_cmd = {'saygal':
                {'phrases':[],
                'eng':'Say something in weird alien type?',
                'function':say_code,
                'description':"say something in a weird alien typeface- &saygal something to say weird"
                }
            }

timer_cmd = {'set_timer':
                {'phrases':[],
                'eng':'Set a timer?',
                'function':make_timer,
                'description':"Set a timer- &set_timer 120,30"
                }
            }

spin_bottle_cmd = {'spin':
                {'phrases':['bottle'],
                'eng':'Spin the bottle?',
                'function':spin_bottle,
                'description':"Spin the bottle- &spin bottle"
                }
            }

chat_cmd = {'chat':
                {'phrases':['start','bot'],
                'eng':'Run the chat bot?',
                'function':talk_bot,
                'description':"Run the chat bot- &start chat bot"
                }
            }

#List of the commands to go into the main bot controller
COMMANDS = [time_cmd,
            go_cmd,
            goto_cmd,
            sleep_cmd,
            say_cmd,
            dildo_cmd,
            watch_cmd,
            set_comm_cmd,
            roll_dice_cmd,
            explore_cmd,
            train_time_cmd,
            say_code_cmd,
            timer_cmd,
            spin_bottle_cmd,
            say_gal_cmd,
            chat_cmd
            ]

def command_bot(player,commands,_key_phrase="&"):
    #Controller for command taking bot

    running = True #Main loop flag

    #Key phrase- defaults to bot
    #   (so that regular addresses can be distinguised from commands, for example)
    key_phrase = _key_phrase

    while not(player.boot_stage == 6):
        #Wait until boot complete
        pass

    try:
        f = open("current_map.p",'rb')
        dat = pickle.load(f)
        f.close()
    except:
        dat =  [{},{},{}]

    player.subprocess_flags['main_map'] = dat
    player.subprocess_flags['expl_tabu'] = {}

    player.subprocess_flags['control channel'] = 'msg'
    #player.subprocess_flags['control channel'] = 'addr'

    while running and player.is_go:
        #Main loop

        state,S = player.bot_char.getState()
        inRoom = state[0]['inRoom']['rid']

        #get-help segment
        get_help = False #If help request made on any channel
        if len(player.bot_char.msg_hist)>0: #check if any messages
            msg_str = player.bot_char.msg_hist[-1]['data']['msg'] #grab the contents
            if msg_str[:4] == 'help' or msg_str[:5] == ' help': #if it starts with 'help'
                get_help = True #set the flag
                h_send = player.bot_char.msg_hist[-1]['data']['char']['id'] #Grab the asker's ID

        if len(player.bot_char.addr_hist)>0: #Check addresses
            msg_str = player.bot_char.addr_hist[-1]['data']['msg'] #Grab contents
            if msg_str[:4] == 'help' or msg_str[:5] == ' help': #If starting with 'help'
                get_help = True #Set flag
                h_send = player.bot_char.addr_hist[-1]['data']['char']['id'] #Grab asker's ID

        #If someone asked for help, make a pretty string to send them
        if get_help:
            S = "\n"+"For using me:" + "\n"
            S = S + "  *for politeness, I respond to either @ or msg (set by comm mode)" + "\n"
            S = S + "  *preface commands with & (for now!)" + "\n"
            S = S + "__Current Commands:__"+"\n"
            for cmd in commands: #Add the list of names and descriptions
                desc = cmd[list(cmd.keys())[0]]['description'].split("-")
                S = S + "  **" + desc[0] + "**\n"
                S = S + "  eg.: " + "`" + desc[1] + "`" + "\n\n"

            #Get the current addressing method
            if player.subprocess_flags['control channel'] == 'msg':
                S = S + "Current control mode is: `messaging`"
            if player.subprocess_flags['control channel'] == 'addr':
                S = S + "Current control mode is: `addressing`"

            #Send the help as a message- it's big, so not in public for politeness
            player.bot_char.message(S,h_send)

        #Get the appropriate contact history, and keep the other one clear
        if player.subprocess_flags['control channel'] == 'msg': #If in message mode
            cont_list = player.bot_char.msg_hist #Grab message history
            if len(player.bot_char.addr_hist) > 0: #If any addresses in queue
                del player.bot_char.addr_hist[-1] #Delete the most recent
        if player.subprocess_flags['control channel'] == 'addr': #If in address mode 
            cont_list = player.bot_char.addr_hist #Grab address history
            if len(player.bot_char.msg_hist) > 0: #if any messages
                del player.bot_char.msg_hist[-1] #Delete the most recent one

        #If a contact is awaiting processing
        if len(cont_list) > 0:

            #Grab the oldest address/msg
            #a_msg = player.bot_char.addr_hist[-1]
            a_msg = cont_list[-1]
            sender = a_msg['data']['char'] #who sent it?
            cont = a_msg['data']['msg'] #What's it say?

            del cont_list[-1]

            #If the key_phrase for giving a command starts the message
            if cont[:len(key_phrase)] == key_phrase:

                #Account for a leading space between keyphrase and message proper
                cont = cont[len(key_phrase):] #Grab everything after the keyphrase
                if cont[0] == " ": #Sf starting with a space (eg. & roll...)
                    cont = cont[1:] #Strip the leading space off

                #Regularize the actual command
                command_words = cont.split(" ") #Break up by spaces
                command = "" #Set base
                for w in command_words: #For each word 
                    command = command + w + " " #Add with a single space
                command = command[:-1] #Strip trailing space

                sel_cmds = [] #List of valid commands present in the message

                #For each registered command
                for phrase in commands:

                    key = list(phrase.keys())[0] #Grab the command key phrase
                    check = check_command(player,command,phrase,sender) #run the check to see if valid

                    player.subprocess_flags['commander'] = sender['id']
                    player.subprocess_flags['commander name'] = sender['name']+" "+sender['surname']
                    if check: #if a registered command is here, add to the list
                        sel_cmds = sel_cmds + [phrase]
                    else: #Otherwise keep moving
                        pass

                #If the parsed command string didn't flag any registered command, say so
                if len(sel_cmds) == 0:
                    resp = "I did not understand your command"
                    missive(player,resp)

                #If it could be more than one command, ask for clarification
                elif len(sel_cmds) > 1:
                    resp = "I am confused about whether you meant: " + "\n"
                    #For each potential command
                    for cm in sel_cmds:
                        key = list(cm.keys())[0] #Grab key
                        eng = cm[key]['eng'] #Grab english phrase version
                        resp = resp + "  -"+eng+"\n"
                    resp = resp + "Please try again with a simpler request"
                    missive(player,resp) #Say the clarification prompt

                #If only one command found, do it
                else:
                    key = list(sel_cmds[0].keys())[0] #grab the key
                    sel_cmds[0][key]['function'](player) #execute the associated function

        #If not contacts in waiting, just move along
        else:
            pass

        #Wait a second to not execute too fast
        time.sleep(1.0)

from Mucklet_Python_Bot_V03 import *

if __name__ == '__main__':

    #Make the main bot
    a_bot = bot()

    #Build the websocket w/ bot methods as callbacks
    #websocket.enableTrace(True)
    ws = websocket.WebSocketApp(HOST
                                ,on_message = a_bot.on_message
                                ,on_error   = a_bot.on_error
                                ,on_close   = a_bot.on_close
                                ,on_open    = a_bot.on_open)

    #Attach the full WS to the bot
    a_bot.set_ws(ws)

    #Boot thread
    boot_thread = threading.Thread(target=a_bot.boot, args=())
    boot_thread.start()

    #Keepawake thread- ping once every 25 seconds
    keep_awake_thread = threading.Thread(target=a_bot.keepAwake, args=(25.0,))
    keep_awake_thread.start()

    #Start up the control thread- determines which bot to run:
    ctrl_thread = threading.Thread(target=command_bot, args=(a_bot,COMMANDS,))
    ctrl_thread.start()

    #Fire up the websocket
    ws.run_forever(origin=ORIGIN)
