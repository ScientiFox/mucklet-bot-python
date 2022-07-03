####
#Demo function bot- mainly used in initial debug, just illustrates basic functions
####

import websocket
import json
import threading
import math,time,random
import pickle,glob

def timed_process(player):
    #Demo async control module- moves, says lines and shuts down

    #The stuff to say, and timers to not say it all at once
    lines =["I want to be alive",
            "I am alive!",
            "Alive, I tell y-"]
    STATE = -1 #It's a really simple linear state machine
    timer = -1
    timer_started = False

    #Loop flag
    running = True

    CHAR_TARGET = "<Char ID to Message>" #fill in ID of char to message

    while not(player.boot_stage == 6):
        #Wait until bot has minimum necessary params filled
        pass

    #is_go stops the thread when the bot shuts down
    while running and player.is_go:

        #Main run loop
        if not(timer_started):
            timer = time.time() #set timer
            timer_started = True #mark as running
            state,S = player.bot_char.getState() #grab initial state
            player.bot_char.say(S) #make the bot say it's state
        else:
            if (time.time() - timer > 2.0): #do something every 2 seconds
                if STATE == -1: #first thing
                    exits = player.bot_char.getExits() #Grab the current exits
                    if len(exits) > 0: #if any exits...
                        player.bot_char.go(exits[0]) #Go through the first one
                if STATE in [0,1,2]: #next three things
                    player.bot_char.say(lines[STATE]) #Say the current state line
                    pass
                if STATE in [3]:
                    #Test to message another character
                    mess = "A test message from the bot @" + str(time.localtime())
                    target = CHAR_TARGET #Target character ID
                    player.bot_char.message(mess,target)
                timer = time.time() #update the timer
                STATE+=1 #increment state
            elif STATE == 4: #After four states
                running = False #kill process
                state,S = player.bot_char.getState() #Get the state
                player.bot_char.say(S) #say the state again
                pass
            else:
                #do nothing between states
                pass

    #Once ended, give a few seconds for last messages to come through- mainly diagnostic
    time.sleep(2.0)
    player.bot_char.gosleep() #Put bot to sleep
    time.sleep(1.0)
    player.ws.close() #Close the Websocket
