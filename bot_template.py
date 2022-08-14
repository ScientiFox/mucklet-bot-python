import websocket
import json
import threading
import math,time,random
import pickle,glob
from difflib import SequenceMatcher

from Mucklet_Python_Bot_V03 import *
from utility_bots import *

#Some things to do while idling
FLAVOR = [":wipes off some tables",
          ":washes a glass",
          ":clears some trash away",
          ":makes itself an oil-based cocktail",
          ":dries some glasses",
          ":thinks about tapping the sign",
          ":dries some glasses",
          ":washes a glass",
          ":gathers up dishes",
          ":runs a quick self-check"]

def demo_bot(player):

    #Grab and then clear the arguments
    if 'command args' in player.subprocess_flags:
        cmd_args = player.subprocess_flags['command args']
        del player.subprocess_flags['command args']

    while not(player.boot_stage == 6):
        pass

    #Set up variables for the message output queue
    message_queue = []
    message_timer = time.time()
    BASE_PERIOD = 7.0
    message_period = BASE_PERIOD
    msg_first = True

    #Timer values for saying flavor text
    flavor_timer = time.time()
    flavor_period = 200.0 + random.random()*(3*60)

    #Turn the bot loop on
    player.subprocess_flags['bot_running'] =  True

    #Mode start-up message
    ALERT_MSG = "I am the bot template, I echo addresses."
    player.bot_char.say(ALERT_MSG)

    #Main loop
    while player.subprocess_flags['bot_running']:

        #Grab the addresses and messages sent
        adr = player.bot_char.addr_hist
        mg = player.bot_char.msg_hist

        #Check for shutdown messages
        if len(mg) > 0:
            sender_m = mg[-1]['data']['char']
            cont_m = mg[-1]['data']['msg']

            #If sent by the issuer
            if sender_m['id'] == player.subprocess_flags['commander']:
                if cont_m == 'stop':
                    #Stop the loop
                    player.subprocess_flags['exploring'] = False
                else:
                    pass
            else:
                #Let anyone else know the bot is busy
                player.bot_char.message("Sorry, currently performing a task",sender_m)

        #Get current state information
        state,S = player.bot_char.getState()
        inRoom = state[0]['inRoom']['rid']
        roomExits = state[1]
        roomName = player.bot_char.char_models[inRoom]['name']
        char_list = state[2] #Fetch characters list

        #Process the message queue for whether to say something
        if len(message_queue)>0:
            flavor_timer = time.time()
        if len(message_queue)==0 and time.time()-flavor_timer > flavor_period:
            msg_flav = FLAVOR[random.randint(0,len(FLAVOR)-1)]
            message_queue = [(msg_flav,None)] + message_queue
            flavor_timer=time.time()
            flavor_period = 120.0 + random.random()*(3*60)
        if len(message_queue) > 0 and time.time()-message_timer > message_period:
            msg_now = message_queue[-1]
            del message_queue[-1]

            #grab msg text and sender
            S = msg_now[0]
            target = msg_now[1]

            #Parse for poses vs say
            if S[0] == ":":
                player.bot_char.pose(S[1:])
            if S[0] != ":" and target == None:
                player.bot_char.say(S)
            if S[0] != ":" and target != None:
                player.bot_char.address(S,target)

            #Set the message timer anew
            message_timer = time.time()
            message_period = message_period*(random.random()+0.5) #New variable period- feels more lifelike
            lw = BASE_PERIOD*0.5
            up = BASE_PERIOD*2.0
            message_period = message_period*(message_period>lw)*(message_period<up) + lw*(message_period<=lw)+ up*(message_period>=up)

        #Handle direct addresses
        if len(adr) > 0:
            sender_a = adr[-1]['data']['char']
            cont_a = adr[-1]['data']['msg']
            del player.bot_char.addr_hist[-1]

            S = sender_a['name'] + " said: \"" + cont_a + "\""
            message_queue = [(S,None)] + message_queue


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
    ctrl_thread = threading.Thread(target=demo_bot, args=(a_bot,))
    ctrl_thread.start()

    #Fire up the websocket
    ws.run_forever(origin=ORIGIN)
