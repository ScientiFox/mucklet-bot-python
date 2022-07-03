####
#Command-executing bot
#   A bot which executes commands sent by address from another player
#   has two commands and a keyword check to execute them- either says the time, or
#   leaves the room
####

import websocket
import json
import threading
import math,time,random
import pickle,glob

def check_command(txt,cmd):
    #Helper function to check if necessary command is present

    #Grab the key phrase and support phrases
    key = list(cmd.keys())[0]
    non_key = cmd[key]['phrases']

    #Flag variables for presence of command keys
    has_key = False
    has_non_key = False

    #Get the list of words in the command string
    txt_words = txt.split(" ")

    #Check if the main keyword and any of the support phrases are present
    for word in txt_words:
        if word == key:
            has_key = True
        if word in non_key:
            has_non_key = True

    #return true if the keyword and any phrases present, false otherwise
    return has_key and has_non_key

def time_cmd(player):
    #Simple task to execute if the 'tell time' command is given

    #Grab the formatted time
    tme = time.localtime()
    hr = str(tme.tm_hour)
    mn = str(tme.tm_min)

    #Make an output string
    time_str = "The current time is: "+hr+":"+"0"*(len(mn)==1)+mn

    #Say the string
    player.bot_char.say(time_str)

def leave_cmd(player):
    #Simple task if the 'go away' command is given
    exits = player.bot_char.getExits() #get the exits
    go_to = exits[0] #pick the first one
    player.bot_char.go(go_to) #get gone


##
#This next section defines the commands
##

time_cmd = {'time': #Key phrase for the command- must be present
                {'phrases':['tell', 'what'], #secondary phrases- at least one must be present
                'eng':'What time is it?', #english language version for 'did you mean' clarifications
                'function':time_cmd #function to call when the command is executed
                }
            }

#Same as above
go_cmd = {'go':
                {'phrases':['out', 'away'],
                'eng':'Go away?',
                'function':leave_cmd
                }
            }

#List of the commands to go into the main bot controller
COMMANDS = [time_cmd,go_cmd]

#Controller for command taking bot
def command_bot(player,commands,_key_phrase="bot"):

    running = True #Main loop flag

    #Key phrase- defaults to bot
    #   (so that regular addresses can be distinguised from commands, for example)
    key_phrase = _key_phrase

    while not(player.boot_stage == 6):
        #Wait until boot complete
        pass

    while running and player.is_go:
        #Main loop

        #If there are any addresses not yet dealt with
        if len(player.bot_char.addr_hist) > 0:

            #Grab the oldest address
            a_msg = player.bot_char.addr_hist[-1]
            sender = a_msg['data']['char'] #who sent it?
            cont = a_msg['data']['msg'] #What's it say?

            #If the key_phrase for giving a command starts the message
            if cont.split(" ")[0] == key_phrase:

                #Grab the actual command
                command_words = cont.split(" ")[1:]
                command = ""
                for w in command_words:
                    command = command + w + " "
                command = command[:-1]

                print("command: ",command)
                #For each registered command
                sel_cmds = []
                for phrase in commands:

                    key = list(phrase.keys())[0] #Grab the command key phrase
                    check = check_command(command,phrase) #run the check to see if valid

                    if check: #if a registered command is here, add to the list
                        sel_cmds = sel_cmds + [phrase]
                    else:
                        pass

                #If the parsed command didn't flag a registered command, say so
                if len(sel_cmds) == 0:
                    resp = "I did not understand your command"
                    player.bot_char.say(resp)

                #If it could be more than one command, ask for clarification
                elif len(sel_cmds) > 1:
                    resp = "Did you mean: " + "\n"
                    for cm in sel_cmds:
                        key = list(cm.keys())[0] #Grab key
                        eng = cm[key]['eng'] #Grab english phrase version
                        resp = resp + "  -"+eng+"\n"
                    player.bot_char.say(resp)

                #If only one command found, do it
                else:
                    key = list(sel_cmds[0].keys())[0] #grab the key
                    sel_cmds[0][key]['function'](player) #execute the associated function

            #Whether it was a command or not, remove it from the queue
            del player.bot_char.addr_hist[-1]

        else:
            pass

        #Wait a second to not execute too fast
        time.sleep(1.0)
