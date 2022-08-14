import websocket
import json
import threading
import math,time,random
import pickle,glob
from difflib import SequenceMatcher

from utility_bots import *

###
#Section to take a command for navigating to a location
#  Includes functions to process map data, find routes, and check user input
###

def print_map(mp):
    rooms = mp[0]
    exits = mp[1]
    names = mp[2]

    for rm in list(rooms.keys()):
        if (rm in names):
            print(names[rm])
            for ex in rooms[rm]:
                if (ex in exits):
                    if exits[ex] in names:
                        print("  ",names[exits[ex]])
                    else:
                        print("  ",exits[ex])
                else:
                    print("  ",ex)
        else:
            print(rooms[rm])
            print("  -")


def path_finder(dat,start,end,find_all=False):
    #Constant-length implementation (O(n)) of Dijkstra's algorithm to find paths
    # between locations
    
    #Grab the data from the map dat input
    rooms = dat[0]
    exits = dat[1]
    names = dat[2]

    #Lists for Dijkstra's algorithm
    rooms_visited = [start] #Rooms done and dusted
    boundary = [start] #Rooms found adjacent to finished rooms needing evaluation
    rooms_link = {start:None} #'hash table' of exits leading to each finished room

    #Early end flag- we don't need the full MPT, just up to the goal location
    end_found = False

    #Until *either* the goal location is found, or all reachable locations seen
    while not(end_found) and len(boundary)>0:

        #Boundary made of all locations adjacent to current boundary not yet visited
        new_boundary = []

        #For everything in the current boundary        
        for room in boundary:

            #Grab the exits
            room_exits = rooms[room]

            to_rooms = [] #Make a list of the exits to novel locations

            #Check each exit
            for a in room_exits:
                #Check if the exit has a mapped destination
                if a in exits:
                    to_rooms = to_rooms + [(a,exits[a])] #If so, annotate it and its destination
                else:
                    #If that exit's destination is unknown as-yet, ignore it
                    pass

            #For each possible destination from this room
            for nr in to_rooms:
                #If the room hasn't been seen yet
                if not(nr[1] in rooms_visited):
                    rooms_visited = rooms_visited + [nr[1]] #Mark that we're seeing it now
                    rooms_link[nr[1]] = (nr[0],room) #Add the link that leads to it
                    new_boundary = new_boundary + [nr[1]] #Add it to the new boundary
                    #If it's the goal state, we can be done!
                    if nr[1] == end:
                        end_found = True
                #If the room is already in the path tree, ignore it
                else:
                    pass
        #Update to the new boundary
        boundary = new_boundary+[]            

    #If the goal is in the path tree after searching
    if end_found and not(find_all):
        #Finish and return the link tree
        return rooms_link
    elif not(end_found) and find_all:
        return rooms_link
    else:
        #Otherwise, annotate that the goal couldn't be found
        return -1

def find_path(rooms_link,end):
    #Function to find a path to a goal room from a link tree

    #Traversal variables
    room_list = [] #List of rooms that will be visited on the path
    exit_list = [] #List of exits to take
    next_room = end #Current room in the traversal- starts at end point and works backwards

    #Until reaching the start (which will have no predecessor link)
    while (rooms_link[next_room] != None):
        room_list = [next_room] + room_list #Put the current room on top of the room queue

        #Put the exit leading to the current room on top of the exit queue
        exit_list = [rooms_link[next_room][0]] + exit_list 

        #Make the next room the one leading to the current one
        next_room = rooms_link[next_room][1]

    #Make the return object the two lists
    path = (room_list,exit_list)
    return path

def find_location_cands(player, main_map, destination):
    #A function to find candidate targets from a human input string

    scored = []#Candidate search score list

    #Loop over all rooms in the provided map
    for rm in main_map[2]:

        #Use the sequence matcher ratio as a 'closeness' score
        score = SequenceMatcher(None,main_map[2][rm],destination).ratio()

        #Add the room and its closeness to the input string to the score list
        scored = scored + [(rm,score,main_map[2][rm])]

    #Sort the list by descending order of score
    scored.sort(key = lambda x:x[1],reverse=True)

    #If the best match is over 90% correlated, assume it's the intended target
    if scored[0][1] > 0.9:
        return True,scored[0][0]
    else:
        #If there's not a 90% match, return top 3
        return False,scored[:3]

def get_GOTO(player):
    #Traversal bot top-level execution function- takes user input, processes it,
    # handles uncertain inputs, and executes the process proper

    #Load up the bot's current map
    map_file = open("current_map.p",'rb') #Open the file
    main_map = pickle.load(map_file) #Load up the data- pickled dictionaries
    map_file.close() #Close the file right away- avoid corruption

    #Grab the appropriate message list
    if player.subprocess_flags['control channel'] == 'msg':
        cont_list = player.bot_char.msg_hist
    if player.subprocess_flags['control channel'] == 'addr':
        cont_list = player.bot_char.addr_hist

    #If a destination argument was passed by the command
    if 'command args' in player.subprocess_flags:
        #Grab it
        destination = player.subprocess_flags['command args']
    else:
        #Otherwise, it wasn't a properly formatted command- say so, but nice
        S = "I couldn't hear where you said to go."
        missive(player,S)
        print(S)
        return 0

    #Use the destination lookup to get a list of candidates the requester might mean
    val,dests = find_location_cands(player,main_map,destination)

    #If a single valid destination was identified
    if val:
        #Set the destination and call the navigation process
        player.subprocess_flags['destination'] = dests
        ret_val = GOTO(player)
        return ret_val #Return the value of the navigation process exit status
    else:
        #If uncertain lookup results, make a prompt string
        S = "I'm not sure which room- did you mean:"+"\n"

        #Top 3 options presented
        i = 1 #Counter
        for rm in dests: #dests is just the top 3 if uncertain
            S = S+"  `"+str(i)+"`: "+rm[2] + "\n" #Add them to pretty string
            i+=1
        S = S + "  or `somewhere else`?"
        missive(player,S) #Send the prompt to the character

    #Set a timeout counter
    listen_time = time.time()

    #While not timed out
    while time.time()-listen_time < 20.0:

        #Grab the channel-appropriate message for the reply
        if player.subprocess_flags['control channel'] == 'msg':
            cont_list = player.bot_char.msg_hist
        if player.subprocess_flags['control channel'] == 'addr':
            cont_list = player.bot_char.addr_hist

        #If there's a message in it
        if len(cont_list)>0:
            #Grab the most recent message
            a_msg = cont_list[-1]

            #Get the message's essential properties
            sender = a_msg['data']['char'] #who sent it?
            cont = a_msg['data']['msg'].strip() #What's it say?

            #Remove the most recent message thus checked
            if player.subprocess_flags['control channel'] == 'msg':
                del player.bot_char.msg_hist[-1]
            if player.subprocess_flags['control channel'] == 'addr':
                del player.bot_char.addr_hist[-1]

            #If sent by someone other than the original requester
            if sender['id'] != player.subprocess_flags['commander']:
                #Politely inform them that the bot is busy with someone else
                player.bot_char.message("Sorry, I am currently executing a task for another client.",sender)
            else:
                #If from the original sender, compare to the index prompts
                score1 = SequenceMatcher(None,cont,"1").ratio()
                score2 = SequenceMatcher(None,cont,"2").ratio()
                score3 = SequenceMatcher(None,cont,"3").ratio()
                score_none = SequenceMatcher(None,cont,"somewhere else").ratio()

                #Based on the score matches, pick an option
                if score_none > 0.5: #No match highest priority
                    #If no math selected, send message and move on
                    S = "I see, please try again"
                    print(S)
                    missive(player,S)
                    retval = 0
                elif score1 > 0.5:
                    #If number 1 matched, run traversal
                    player.subprocess_flags['destination'] = dests[0][0]
                    retval = GOTO(player)
                elif score2 > 0.5:
                    #If number 2 matched, run traversal
                    player.subprocess_flags['destination'] = dests[0][1]
                    retval = GOTO(player)
                elif score3 > 0.5:
                    #If number 3 matched, run traversal
                    player.subprocess_flags['destination'] = dests[0][2]
                    retval = GOTO(player)
                else:
                    #Otherwise, some unknown input- move on
                    S = "I see, please try again"
                    print(S)
                    missive(player,S)
                    retval = 0

                #Regardless of choice, clear operation flags & return
                del player.subprocess_flags['commander']
                del player.subprocess_flags['command args']
                return retval
        else:
            #If no reply to check, just pass by
            pass

    #If 20 seconds go by with no reply, move on
    S = "Request timed out, please try again."
    print(S) 
    missive(player,S)

    #Clear process flags and return
    del player.subprocess_flags['commander']
    del player.subprocess_flags['command args']
    return 0

def exploration_bot(player):
    #Bot to explore the map and update areas

    #Grab the current map
    main_map = player.subprocess_flags['main_map']
    rooms = main_map[0]
    exits = main_map[1]
    names = main_map[2]

    #Main loop flag    
    player.subprocess_flags['exploring'] =  True
    #player.subprocess_flags['room_save'] =  {}
    player.subprocess_flags['expl_tabu'] =  {}

    #Operational variables
    dest = None #Next destination selection
    just_arrived = False #Note arrival so as not to try to grab empty prior exit
    exit_prev = None #last exit taken for map updates

    #State machine variables
    PICK_TARGET,MOVE_TO,GET_RECENT,EXPLORE = 0,1,2,3
    STATE = PICK_TARGET

    DELAY_BARK = 0.0

    #Main loop
    while player.subprocess_flags['exploring']:

        #Check for shutdown messages
        mg = player.bot_char.msg_hist
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
                player.bot_char.message("Sorry, currently in exploration mode",sender_m)

        #Grab a fresh copy of the map
        main_map = player.subprocess_flags['main_map']
        rooms = main_map[0]
        exits = main_map[1]
        names = main_map[2]

        #Grab the current state
        state,S = player.bot_char.getState()
        inRoom = state[0]['inRoom']['rid']
        roomExits = state[1]
        roomName = player.bot_char.char_models[inRoom]['name']

        if not(inRoom in rooms):
            #Add a new room to the map
            rooms[inRoom] = roomExits
            rooms[inRoom] = roomName
            player.subprocess_flags['main_map'] = [rooms,exits,names]
            

        #Phase to pick the next target room
        if STATE == PICK_TARGET and player.subprocess_flags['exploring']:            
            cands = [] #Candidate room list

            print("MAP SIZE: ",len(rooms),len(exits))
            print("TABU SIZE: ",len(player.subprocess_flags['expl_tabu']))
    
            #New copy of the map, in case updated
            main_map = player.subprocess_flags['main_map']
            rooms = main_map[0]
            exits = main_map[1]
            names = main_map[2]

            #Check all rooms for number of unchecked exits
            S = ""
            for rm in rooms:
                n_miss = 0
                exs = rooms[rm]
                for e in exs: #check if exit in the map
                    if not(e in exits):
                        n_miss+=1 #increment counter if not

                #If the room has unexplored exits
                if n_miss > 0:
                    S = S + "RM w/ new exits: "+str(rm)+" exits: "+str(n_miss)+" inRoom: "+str(inRoom)+"\n"
                    paths = path_finder([rooms,exits,names],inRoom,rm) #check if reachable
                    if paths!=-1:
                        path = find_path(paths,rm) #if it is, get a path
                        if path != -1:
                            cands = cands + [(rm,path)] #and add to the candidate list
                        else:
                            print("No path to CAND")
                    else:
                        pass
                else:
                    pass
            print(S)

            #If there are reachable rooms with unexplored exits
            if len(cands) > 0:
                cands.sort(key=lambda x:len(x[1][0])) #sort by distance from current room
                dest = cands[0][0] #set the first one as the next target
                print("Reachable exits new DEST: ",dest,"w/ NEW EXITS: ",cands[0][1])
            else:
                #Otherwise, find all reachable rooms from the current one
                reachable = path_finder([rooms,exits,names],inRoom,"",find_all=True)
                opt = list(reachable.keys()) #grab that list
                fins = []

                for det in opt:
                    if not(det in player.subprocess_flags['expl_tabu']):
                        dist = 0
                        poke = det
                        while poke != None:
                            dist+=1
                            if reachable[poke] != None:
                                poke = reachable[poke][1]
                            else:
                                poke = reachable[poke]
                        fins = fins + [(det,dist)]
                    else:
                        pass

                if len(fins)>0:
                    fins.sort(key=lambda x: x[1])
                    #r = random.randint(0,len(fins)-1) #pick one at random
                    dest = fins[0][0] #make it the next destination
                    print("Tabu check NEW DEST:",dest,", dist:",fins[0][1])

                else:
                    #no non-tabu random sites to check
                    player.subprocess_flags['exploring'] = False
                    print("All known and observable locations checked")

            #Set the state to navigation
            STATE = MOVE_TO

        #When navigating
        elif STATE == MOVE_TO and player.subprocess_flags['exploring']:
            player.subprocess_flags['destination'] = dest #Set the destination properly

            #Run the goto function normally
            run_goto = GOTO(player,trial=True)
            time.sleep(6.0)

            #If you couldn't get there (changing exits, etc), re-pick target
            if run_goto == -1:
                STATE = PICK_TARGET
            else:
                #otherwise, go to explore phase, set ops variables to reflect end of trip
                STATE = EXPLORE
                just_arrived = True
                exit_prev = None

        #When exploring
        elif STATE == EXPLORE and player.subprocess_flags['exploring']:

            #If the current room isn't in the map, add it
            if not (inRoom in rooms):
                print("NEW ROOM")
                rooms[inRoom] = roomExits
                names[inRoom] = roomName
                player.subprocess_flags['main_map'] = [rooms,exits,names]

            #If coming from a navigation, no prev exit set, so clear the flag
            if just_arrived:
                just_arrived = False
            else: #If flag already cleared, update the exit with the current room
                exits[exit_prev] = inRoom
                player.subprocess_flags['main_map'] = [rooms,exits,names]

            #Pick exits to take
            cand_exits = [] #make candidate list
            for ex in roomExits:
                if not(ex in exits): #if the exit hasn't been explored
                    print("NEW EXIT SEEN") #note it to the console
                    cand_exits = cand_exits + [ex] #Add it to the candidate list
                else:
                    pass

            #If there's some unseen exits
            if len(cand_exits)> 0:
                r = random.randint(0,len(cand_exits)-1) #Grab one at random
                exit_choice = cand_exits[r] #And set it to be taken
                exit_prev = exit_choice #mark it as 'previous' for after the movement
                player.bot_char.go(exit_prev) #Take the exit
                time.sleep(6.0) #Delay to not run afoul of overflow protection
            else:
                #if no unseen exits, go back and pick another target with unexplored ones
                STATE = PICK_TARGET

    #Save a copy of the map-  when process ended
    print("Saving Data")
    map_file = open("current_map.p",'wb')
    pickle.dump(player.subprocess_flags['main_map'],map_file)
    map_file.close()

    #rm_file = open("rms_mir5.p",'wb')
    #pickle.dump(player.subprocess_flags['room_save'],rm_file)
    #rm_file.close()


    print("Data Saved")

    return 1

def GOTO(player,trial=False):
    #Function to actually execute a traversal

    main_map = player.subprocess_flags['main_map']
    rooms = main_map[0]
    exits = main_map[1]
    names = main_map[2]

    if player.subprocess_flags['destination'] in names:
        print("GOING TO:"+names[player.subprocess_flags['destination']])
    else:
        print("GOING TO:"+player.subprocess_flags['destination'])

    #If a destination is marked
    if 'destination' in player.subprocess_flags:
        #Grab it
        destination = player.subprocess_flags['destination']

        #And clear the process flag
        del player.subprocess_flags['destination']
    else:
        #Otherwise, acknowledge that and move on
        S = "No destination set"
        missive(player,S)
        return -1

    #Manual input- diagnostic
    #end = find_location_cands(player,main_map,destination)

    #If not doing diagnostics, grab the endpoint
    end = destination

    #If the endpoint is none, the room couldn't be found in the map
    if end == None:
        #Say so and return
        S = "Room not found"
        missive(player,S)
        return -1
    else:
        #Otherwise continue on
        pass

    #Set the process flag so the bot knows it is traveling
    player.subprocess_flags['is_navigating'] = True

    #Most recent exit for map update
    prev_exit = None

    TOO_ACTIVE_FLAG = False

    #Until travel flag is cleared
    while player.subprocess_flags['is_navigating']:

        #lookedAt = []
        #for a in list(player.bot_char.char_models.keys()):
        #    if 'details' in a.split('.') and 'room' in a.split('.'):
        #        rm = player.bot_char.char_models[a]
        #        if not(rm['id'] in player.subprocess_flags['room_save']):
        #            print(rm['name'])
        #            player.subprocess_flags['room_save'][rm['id']] = rm

        #Check for stop command
        mg = player.bot_char.msg_hist
        if len(mg) > 0:
            sender_m = mg[-1]['data']['char']
            cont_m = mg[-1]['data']['msg']
            if sender_m['id'] == player.subprocess_flags['commander']:
                if cont_m == 'stop':
                    player.subprocess_flags['exploring'] = False
                    player.subprocess_flags['is_navigating'] = False
                else:
                    pass
            else:
                player.bot_char.message("Sorry, currently in navigation mode",sender_m)

        #Grab a copy of the map
        main_map = player.subprocess_flags['main_map']
        rooms = main_map[0]
        exits = main_map[1]
        names = main_map[2]

        #Grab the bot's current statue
        current_state,S = player.bot_char.getState()

        #Peel the current room from the state
        current_room = current_state[0]['inRoom']['rid']
        roomExits = current_state[1]
        roomName = player.bot_char.char_models[current_room]['name']

        #Update map with room info on each movement
        rooms[current_room] = roomExits
        names[current_room] = roomName
        if not(prev_exit == None) and not(TOO_ACTIVE_FLAG):
            exits[prev_exit] = current_room
        if TOO_ACTIVE_FLAG:
            TOO_ACTIVE_FLAG = False
        player.subprocess_flags['main_map'] = [rooms,exits,names]
        player.subprocess_flags['expl_tabu'][current_room] = True

        #If at the destination
        if current_room == end:
            #Clear loop flag
            player.subprocess_flags['is_navigating'] = False

            #Inform the request issuer and return
            S = "Arrived at Destination"
            player.bot_char.message(S,player.subprocess_flags['commander'])
            print(S)

            #Save a copy of the map-  when process ended
            print("Saving Data")
            map_file = open("current_map.p",'wb')
            pickle.dump(player.subprocess_flags['main_map'],map_file)
            map_file.close()

            return 1

        #If not ended- find the path from the current location to the goal
        #  Re-evaluates path every time to account for changes or accidental commands
        plotted = path_finder(main_map,current_room,end)

        #If a path from the current location
        if plotted != -1:
            #Peel the route out of the path tree
            path = find_path(plotted,end)
        else:
            #Otherwise annotate no path available
            path = -1

        #If there's no path
        if path == -1:
            #Clear the loop flag
            player.subprocess_flags['is_navigating'] = False

            #Save a copy of the map-  when process ended
            print("Saving Data")
            map_file = open("current_map.p",'wb')
            pickle.dump(player.subprocess_flags['main_map'],map_file)
            map_file.close()

            #Inform the request issuer and return
            if not(trial):
                S = "No path Found"
                player.bot_char.message(S,player.subprocess_flags['commander'])
            return -1

        # If there is a path
        else:
            #Grab the exit to the next location
            exit_to_take = path[1][0]
            prev_exit = exit_to_take

            #if the travel message counter hasn't been added to the flags
            if not('travel_counter' in player.subprocess_flags):
                #Add it now
                player.subprocess_flags['travel_counter']=0

            #Grab the most recent travel counter
            travel_ct = player.subprocess_flags['travel_counter']

            #Take the exit
            player.bot_char.go(exit_to_take)

            #Wait until the travel completed message comes through
            t_timer = time.time()
            while (travel_ct == player.subprocess_flags['travel_counter']) and not(time.time()-t_timer > 6.0):
                pass

            if time.time()-t_timer > 6.0:
                TOO_ACTIVE_FLAG = True                

            #Wait a bit to not run afoul of 'too active' error
            time.sleep(6.0)
