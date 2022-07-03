####
#The following bot waits in the area it wakes up in and watches for new characters to
#   enter. When that happens, it messages a set other character to notify them
#   of the new entries.
####

import websocket
import json
import threading
import math,time,random
import pickle,glob

def alert_bot(player):
    #This bot waits in a location and alerts a user if someone new enters
    #  *Updates once a second

    #Execution variables
    running = True #Main loop
    checked_first = False #Has the current room been checked yet?
    char_list = [] #List of chars currently in the room
    CHAR_TARGET = '<Char ID to message>' #Character to message on update

    while not(player.boot_stage == 6):
        #Wait until bot has minimum necessary params filled
        pass

    #While running and player is connected
    while running and player.is_go:

        #If first time around
        if not(checked_first):
            state,S = player.bot_char.getState() #Grab initial state
            char_list = state[2] #Fetch characters list
            checked_first = True #Note that initial list is grabbed

        # If not the first time
        else:
            #Grab the current state and new list of people in the room
            state,S = player.bot_char.getState()
            new_chars = state[2]

            #Just get a list of charIds of the prior list
            ids_old = [a['id'] for a in char_list]

            #Build the list of new chars to notify the target character of
            notify_list = []
            for char in new_chars: #Loop over all new chars
                if not(char['id'] in ids_old): #Check if ID was in here last time
                    #If so, add to update list
                    notify_list = notify_list + [char['name'] + " " + char['surname']]

            #If one new person, message with singular string
            if len(notify_list)==1:
                msg_not = notify_list[0] + " entered "+player.bot_char.char_models[state[0]["inRoom"]['rid']]['name']
                player.bot_char.message(msg_not,CHAR_TARGET)
                player.bot_char.say(notify_list[0]+" arrived.")

            #If more than one new person, send update with plural list string
            if len(notify_list)>1:
                msg_not = ""
                for a in notify_list[:-1]: #Add each new person but the last
                    msg_not = msg_not + a + ", "

                #Format last person ("so-and-so, such-and-such and whosit")
                msg_not = msg_not[:-2] + " and " + notify_list[-1] + " entered "+player.bot_char.char_models[state[0]["inRoom"]['rid']]['name']
                player.bot_char.message(msg_not,CHAR_TARGET)

            #Replace old list with new one
            char_list = new_chars
            time.sleep(1.0) #wait a second before checking again
