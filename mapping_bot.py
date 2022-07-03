####
#Mapping Bot- runs from starting location and visits count_lim many new rooms, recording
#   the room id, name, and exits at each step, and linking rooms each time it tries an
#   exit. Saves the map it builds, and adds to it every time it is run.
#
#   *Note: Currently a random Tabu search and does not re-check previously found exits
#   for changes
####

import websocket
import json
import threading
import math,time,random
import pickle,glob

def mapping_bot(player):

    #Main loop flag
    running = True

    #Grab the old map if one exists
    file_check = glob.glob("current_map.p")
    if file_check != []:
        #Load up the old map
        map_file = open(file_check[0],'rb')
        old_map_data = pickle.load(map_file)

        #Update map variables with old stored ones
        map_dict = old_map_data[0]
        exit_dict = old_map_data[1]
        name_dict = old_map_data[2]
    else:
        #If no old map, start fresh
        map_dict = {}
        exit_dict = {}
        name_dict = {}

    exits_total = {} #List of all exits seen, but not necessarily tried
    exit_prev = None #most recently used exit
    
    count_lim = 2 #Limit of number of new rooms to see

    while not(player.boot_stage == 6):
        #Loop to wait until boot cycle is done
        pass

    while running and player.is_go:
        #Main loop

        #Grab the main state variables for the bot
        state,S = player.bot_char.getState()
        inRoom = state[0]['inRoom']['rid']
        roomName = player.bot_char.char_models[inRoom]['name']
        roomExits = state[1]

        #If the bot hasn't seen this room, make a new entry
        if not (inRoom in map_dict):
            count_lim-=1 #Reduce search limit by 1 room

            #Add the needed keys to the map dictionaries
            map_dict[inRoom] = roomExits
            name_dict[inRoom] = roomName

            #Update dictionary of seen exits
            for ex in roomExits:
                if not(ex in exit_dict): #check if uploaded w/ old dictionary
                    exits_total[ex] = True

        #If not the first move, update that the most recent exit lead to the current room
        if exit_prev != None:
            exit_dict[exit_prev] = inRoom

        #Save the copy of the map post-update
        player.save_data = [map_dict,exit_dict,name_dict]

        #Random tabu search: get list of exits not yet tried
        exit_cands = []
        for ex in roomExits:
            if not(ex in exit_dict):
                exit_cands = exit_cands + [ex]

        #Print out cuttent location and exits to console (diagnostic)
        print(inRoom)
        print(roomExits)
        print("--------")

        #If there's unseen exits, pick from those randomly
        if exit_cands != []:
            r = random.randint(0,len(exit_cands)-1)
            exit_choice = exit_cands[r]
        #If all exits have been tried, pick any at random
        else:
            r = random.randint(0,len(roomExits)-1)
            exit_choice = roomExits[r]

        exit_prev = exit_choice #Mark the exit taken for linking
        player.bot_char.go(exit_prev) #Send the bot through that exit

        time.sleep(5.0) #Don't run afoul of being 'too active'

        #End if either the count limit reached, or have explored all exits ever seen
        if len(exits_total) == len(exit_dict) or count_lim == 0:
            running = False #Kill process

            #Save a copy of the map
            map_file = open("current_map.p",'wb')
            pickle.dump(player.save_data,map_file)
            map_file.close()

    #Once ended, give a few seconds for last messages to come through- mainly diagnostic
    time.sleep(2.0)
    player.bot_char.gosleep() #Put bot to sleep
    time.sleep(1.0)
    player.ws.close() #Close the Websocket
