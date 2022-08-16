import websocket
import json
import threading
import math,time,random
import pickle,glob
from difflib import SequenceMatcher

CODESRC = "▀▖┗▛▄▖▜▚┣ ▜▚┗┣┗┫┓┏┓ ▛▄▖┅┗▖. ┣┗┏▛▄▖▜┏┣ ▚ ▖▞┣┗▖┗┣. ┣┗▖┃▀▚▗┏┏┓. ▖┛▀┗▞┃┏▄ ▛┏┗▄▖▜▚┣ ┅▖┗━▖ ▖┓┫▞┣ ▚ ▛▄┅┗▖ ▚ ▖▞┣┗▖┗┣ ▚┛▘▞━▖"
CODELST = {}
for a in CODESRC:
    if not(a ==" "):
        CODELST[a] = True
CODELST = list(CODELST.keys())

GALSRC = "ᑑ∴ᒷ∷ℸ ̣ ||⚍╎𝙹!¡ᔑᓭ↸⎓⊣⍑⋮ꖌꖎ⨅ ̇/ᓵ⍊ʖリᒲ"
GALLST = {}
for a in GALSRC:
    if not(a ==" "):
        GALLST[a] = True
GALLST = list(GALLST.keys())

########
#Helper functions for the command parsing system
########

def check_command(player,txt,cmd,commander):
    #Helper function to check if necessary command is present

    #Grab the key phrase and support phrases
    key = list(cmd.keys())[0]
    non_key = cmd[key]['phrases']

    #Flag variables for presence of command keys
    has_key = False
    if len(non_key)>0:
        has_non_key = False #If secondary phrases present, have to look for them
    else:
        has_non_key = True #Automatically approve secondary phrase check for argument commands

    #Get the list of words in the command string
    txt_words = txt.split(" ")

    #Check if the main keyword and any of the support phrases are present
    args = ""
    #For each word in the message
    for word in txt_words:

        if word == key: #If it's a key for the command in question, mark flag
            has_key = True

        elif word in non_key: #Mark the second flag for any non-key
            has_non_key = True

        #If no secondary phrases, get arguments after keyword
        elif len(non_key) == 0 and has_key == True:
            args = args + word + " "

    #If there's arguments and valid command
    if len(args)>0 and has_key and has_non_key:
        args = args[:-1] #Strip trailing space
        player.subprocess_flags['command args'] = args #Put args into process flags

        #Put requester ID and name into process flags
        player.subprocess_flags['commander'] = commander['id']
        player.subprocess_flags['commander name'] = commander['name']+" "+commander['surname']
        print("COMMANDER NAME:",player.subprocess_flags['commander name'])

    #return true if the keyword and any phrases present, false otherwise
    return has_key and has_non_key

def missive(player,S):
    #Send a message in the current command channel (public address or private message)
    if player.subprocess_flags['control channel'] == 'msg':
        player.bot_char.message(S,player.subprocess_flags['commander'])
    if player.subprocess_flags['control channel'] == 'addr':
        player.bot_char.say(S)

####
#Functions to parse inputs for non-exclusive keyphrases
####

def clear_junk(a,junk):
    #Remove 'junk chars from a string
    a_clr = ""
    for l in a:
        if not(l in junk):
            a_clr = a_clr + l
        else:
            a_clr = a_clr + " "
    return a_clr

def compare_segment(A,B):
    #First is the reference, return linear order matches w/ scores
    a = A.lower()
    b = B.lower()
    junk = [" ",",",".","!","?",";",":","-"]

    a = clear_junk(a,junk)
    b = clear_junk(b,junk)

    segs = []

    i = 0
    j = 0
    curr_str = ""
    while i < len(a):
        if j == len(b)-1 and a[i] == b[j]:
            segs = segs + [(curr_str+a[i],i-j)]
            curr_str = ""
            j = 0
        if a[i] == b[j]:
            curr_str = curr_str + a[i]
            j+=1
        elif a[i] != b[j]:
            j = 0
            curr_str = ""
        i+=1

    matches = []
    for mat in segs:
        score = (1.0*len(mat[0]))/len(b)
        matches = matches + [(mat[0],mat[1],len(mat[0]),score)]

    return matches

def get_matches(txt,options):
    #grab a set of best matches from a text map pair
    sorted_matches = []

    for opt in options:
        seg = compare_segment(txt,opt)
        if len(seg)>0:
            longest = max([a[2] for a in seg])
            for s in seg:
                if s[2] == longest:
                    sorted_matches = sorted_matches + [s]
                else:
                    pass
        else:
            pass
    sorted_matches.sort(key = lambda x: x[3],reverse=True)

    return sorted_matches

def get_lead_cands(candidates):
    #Grab the top-scoring candidates from a match set (i.e. at least the best, but >1 if multiple hits at the same highest score)
    op = []
    if len(candidates)>0:
        cands = list(candidates)
        cands.sort(key=lambda x:x[3],reverse=True)
        m_score = cands[0][3]
        for cn in cands:
            if cn[3] == m_score:
                op = op + [cn]
            else:
                pass
    return op

def overlap_checker(candidates):
    #Loop over matches and remove overlapping hits, like: "ladys virgin milkshake" will hit 'gin' and 'ladys virgin', but 'gin' is fully inside 'ladys virgin' so it's kicked out

    overlap_check = {}
    removes = {}

    for chk in candidates:
        clear = True
        to_take = []
        for cn in overlap_check:
            if (cn[1] <= chk[1] and chk[1]+chk[2]<=cn[1]+cn[2]):
                clear = False
            if (chk[1] <= cn[1] and cn[1]+cn[2]<=chk[1]+chk[2]):
                to_take = to_take + [cn]
        for rem in to_take:
            del overlap_check[rem]
            removes[rem]=True
        if clear:
            overlap_check[chk] = True
        else:
            removes[chk] = True

    return overlap_check

########
#Commands that can actually be called as a bot function
########

###
#Command to report the time
###

def time_cmd(player):
    #Simple task to execute if the 'tell time' command is given

    #Grab the formatted time
    tme = time.localtime()
    hr = str(tme.tm_hour)
    mn = str(tme.tm_min)

    #Make an output string
    time_str = "The current time is: "+hr+":"+"0"*(len(mn)==1)+mn

    #Say the string
    missive(player,time_str)
    return 1


###
#Command to leave the room
###

def leave_cmd(player):
    #Simple task if the 'go away' command is given
    exits = player.bot_char.getExits() #get the exits
    go_to = exits[0] #pick the first one
    player.bot_char.go(go_to) #get gone
    return 1


###
#Command to watch the room and report new visitors
#  Includes a provision to end the task by a command
###

def alert_bot(player):
    #This bot waits in a location and alerts a user if someone new enters
    #  *Updates once a second

    #Execution variables
    checked_first = False #Has the current room been checked yet?
    char_list = [] #List of chars currently in the room
    CHAR_TARGET = 'can1p7e9gbrmb439d8n0' #Character to message on update

    while not(player.boot_stage == 6):
        #Wait until bot has minimum necessary params filled
        pass

    #Set operational flags
    player.subprocess_flags['watching'] = True

    #Alert player that mode is active
    missive(player,"Watching now")

    #While running and player is connected
    while player.subprocess_flags['watching'] and player.is_go:

        #Grab the appropriate communication history based on mode
        if player.subprocess_flags['control channel'] == 'msg':
            cont_list = player.bot_char.msg_hist
        if player.subprocess_flags['control channel'] == 'addr':
            cont_list = player.bot_char.addr_hist

        #If there is a message waiting
        if len(cont_list) > 0:

            #Grab oldest message's properties
            a_msg = cont_list[-1]
            sender = a_msg['data']['char'] #who sent it?
            cont = a_msg['data']['msg'] #What's it say?

            #Delete the oldest message in the appropriate queue
            if player.subprocess_flags['control channel'] == 'msg':
                del player.bot_char.msg_hist[-1]
            if player.subprocess_flags['control channel'] == 'addr':
                del player.bot_char.addr_hist[-1]

            #Check if a message from the character who started the task
            if sender['id'] == player.subprocess_flags['commander']:
                #If so, and if 'stop' mode, kill process
                if cont == 'stop':
                    player.subprocess_flags['watching'] = False
                else:
                    pass
            #If not the issuer, ignore and inform new requester
            else:
                player.bot_char.message("Sorry, I'm currently executing a task for another client",sender['id'])

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

    #Inform the issuer that the task is ended
    missive(player,"No longer watching")

    #Clear the relevant process flags
    del player.subprocess_flags['commander']
    del player.subprocess_flags['watching']

    return 1

###
#Command to put the bot to sleep
###

def go_sleep(player):
    #Simple command to put the bot to sleep
    player.bot_char.gosleep()
    player.ws.close()
    return 1


###
#Command to make the bot say a phrase
###

def say_it(player):
    #Simple command to make the bot say something (With a bit of flavor!)
    S = player.subprocess_flags['command args']
    del player.subprocess_flags['command args']
    player.bot_char.pose(" says through its speakers: "+S)
    return 1

def make_code(inp):
    #Function to turn strings into 'CODE', designed ordinally so a string becomes the same encrypted string each time
    op = ""
    ind = 0
    for a in inp:
        if a != " ":
            ind = (ind+ord(a))%len(CODELST)
            op = op + CODELST[ind]
        else:
            op = op + " "
    return op

def make_gal(inp):
    #Same as above but for that weird galspeak thing
    op = ""
    ind = 0
    for a in inp:
        if a != " ":
            ind = (ind+ord(a))%len(GALLST)
            op = op + GALLST[ind]
        else:
            op = op + " "
    return op

def say_code(player):
    #Actually say the CODE phrase
    S = player.subprocess_flags['command args']
    del player.subprocess_flags['command args']
    player.bot_char.say(make_code(S))
    return 1

def say_gal(player):
    #Actually say the galspeak phrase
    S = player.subprocess_flags['command args']
    del player.subprocess_flags['command args']
    player.bot_char.say(make_gal(S))
    return 1

def make_timer(player):
    #Function to make a timer from command flag inputs and run it
    S = player.subprocess_flags['command args']
    try:
        dur = int(S.split(",")[0])
        if len(S.split(","))>1:
            per = int(S.split(",")[1])
    except:
        missive(player,"Could not parse timer arguments")
        return -1

    timer = time.time()
    per_timer = timer
    while (time.time()-timer<dur):
        ti = time.time()-per_timer
        if ti > per:
            dur_left = int(round(dur - (time.time()-timer),0))
            S = str(dur_left)+" second" + "s"*(dur_left!=1) +" left"
            missive(player,S)
            per_timer = time.time()
        else:
            pass
    missive(player,"Time up")
    return 1

###
#Command to run the bot's Dildo Mode
#  Includes a complex argument parser
###

def do_dildo(player):
    #Activate the robot's dildo mode

    #Grab and then clear the arguments
    S = player.subprocess_flags['command args']
    del player.subprocess_flags['command args']

    #Viable time units- days and hours remanded to seconds to be polite
    time_units = ['minutes','seconds','minute','seconds']

    setting = S.split(" ") #Break up message for parsing
    dur = 15.0 #default duration of 15 seconds
    period = 5.0 #default period of 5 seconds

    #If message is too short to be valid
    if len(setting) < 3:
        player.bot_char.say("TOO FEW INPUTS, PERFORMING DEFAULT DILDOING")

    #If enough text to be a valid setting command
    else:
        #Search through the command string
        for i in range(len(setting))[2:]:
            #If segment is 'for X <time units>'
            if setting[i] in time_units and setting[i-2] == 'for':
                #See if can convert X to a number, set duration if so
                try:
                    #if <time units> in minutes
                    if setting[i] in ['minute','minutes']:
                        dur = float(setting[i-1])*60 #multiply by 60 seconds
                    #If not units of mintues
                    else:
                        dur = float(setting[i-1]) #Assume seconds
                except:
                    #If X can't be made a number, move along
                    pass
            #If segment is 'every X <time units>', set period
            if setting[i] in time_units and setting[i-2] == 'every':
                #See if can convert X to a number
                try:
                    #if <time units> in minutes
                    if setting[i] in ['minute','minutes']:
                        period = float(setting[i-1])*60 #Multiply by 60 seconds
                    else:
                        period = float(setting[i-1])#Otherwise assume seconds
                except:
                    #Pass on if X isn't number-able
                    pass

    #Diagnostic print to console
    #print("DILDOING FOR:",dur," seconds every",period," seconds")

    player.bot_char.pose("goes brrrrrr") #Send initial action
    runtime = time.time() #Set timer for duration
    time.sleep(period) #Give the first action its period
    while time.time()-runtime < dur-period: #Loop until duration - period (for last action)
        player.bot_char.pose("keeps going brrrrrr") #Make main duration action
        time.sleep(period) #Give action its period

    player.bot_char.pose("goes brrr a little less") #final dildo message
    time.sleep(1.0) #Completion delay

    #Announce completion of dildo procedure and thank user
    player.bot_char.say("DILDOING COMPLETE")
    time.sleep(1.0)
    player.bot_char.say("THANK YOU FOR YOUR PATRONAGE")
    return 1


###
#Command to change the bot's communication mode
###

def set_comm(player):
    #Function to swap between message and address communication mode

    comm_mode = player.subprocess_flags['command args'] #Grab new mode from argument
    del player.subprocess_flags['command args'] #Clear argument flag

    #If it's a valid switch
    if comm_mode in ['msg','addr']:
        player.subprocess_flags['control channel'] = comm_mode #Set the new value
        missive(player,"Comm channel changed") #Announce change to issuer
    #If not valid
    else:
        #Inform the issuer
        missive(player,"Invald comm channel") 

    #Clear the process flag and return
    del player.subprocess_flags['commander']
    return 1

###
#Section to take a command to roll some dice
###

def roll(n,d):
    #Function to roll a single die
    rolls = [random.randint(1,d) for a in range(n)]
    return sum(rolls),rolls

def die_parser(dies):
    #Parse a string of a set of dies like 4d6+2d9-18d3+12
    # looks at groups and peels operations: 4d6+2d9-18d3+12
    #                         Current position-^  ^-Lookahead

    dies = dies.strip()#Clear excess white space

    #Loop variables
    pos_curr = 0 #Current position in string
    pos_look = 0 #lookahead index
    rolls = [] #Set of rolls made
    val = 0 #Sum of rolls made

    #Position loops over furthest seen die
    while pos_look < len(dies):

        #While grabbing numbers an not at end of string
        while not(dies[pos_look] in ['+','-']) and (pos_look < len(dies)-1):
            #Increment the lookahead index, if possible
            if (pos_look < len(dies)-1):
                pos_look+=1

        #If at the end, increment past to teminate loop
        if pos_look == len(dies)-1:
            pos_look = pos_look+1

        #Grab the current segment to evauate
        seg = dies[pos_curr:pos_look]

        #If not an operation present at head of segment, assume '+'
        if not(seg[0] in ['+','-']):
            seg = "+"+seg

        #Grab dies component from segment
        nd = seg[1:].split('d') #Split around the 'die'

        #If no 'd' present- must be a constant
        if len(nd) == 1:
            if seg[0] == '+':
                #Add a constant to the value if '+'
                val = val + int(nd[0])
            if seg[0] == '-':
                #Subtract constant if '-'
                val = val - int(nd[0])
        #If a 'd' is present, it's a die roll
        else:
            #Grab the value of the specific roll and individual results
            v,rl = roll(int(nd[0]),int(nd[1]))
            #Add to value if leading '+'
            if seg[0] == '+':
                val = val + v
            #Subtract from value if leading '-'
            if seg[0] == '-':
                val = val - v
            #Add individual rolls to list of all rolls
            rolls = rolls + [rl]
        #Move the current position to the lookahead, and the lookahead up 1
        pos_curr = pos_look
        pos_look+=1

    #Return the total result and the individual rolls
    return val,rolls

def roll_dice(player):
    #Function to execute the roll dice command
    dies = player.subprocess_flags['command args'] #Grab the dies to roll from the command
    del player.subprocess_flags['command args'] #Clear the process flag

    try:
        val,rolls = die_parser(dies) #try to execute the parser
        name = player.subprocess_flags['commander name'] #Grab the requester's name
        missive(player,name+" rolls "+dies+": "+str(val)) #Report the roll- So-and-so rolls...
    except:
        #If the roll fails, notify the requester
        missive(player,"Die roll did not execute- perhaps formatted wrong?")

    #After, clear process flags and return
    del player.subprocess_flags['commander name']
    return 1    

def time_since_train(player):
    #Report the time since the currently controlled bot was created
    ch = 'core.char.'+player.bot_char.cid+".owned"
    time_train = player.bot_char.char_models[ch]['created']/1000
    per = (time.time()-time_train)

    days = int(per/(60*60*24))
    hrs = int((per-days*(60*60*24))/(60*60))
    mins = int((per-days*(60*60*24)-hrs*60*60)/60)
    secs = int((per-days*(60*60*24)-hrs*60*60-mins*60))

    tmes = [(days," day"),(hrs," hour"),(mins," minute")]

    S = "I woke up on the train "
    for a in tmes:
        S = S + str(a[0]) + a[1] + "s"*(a[0]>1) + ", "
    S = S + "and " + str(secs) + " second" + "s"*(secs>1) + " ago."

    missive(player,S)
    return 1

def spin_bottle(player):
    #Run the spin-the-bottle function on players in the current room

    state,S = player.bot_char.getState() #Grab initial state
    char_list = state[2] #Fetch characters list
    
    r = random.randint(0,len(char_list)-1)
    char_sel = char_list[r]

    nme = char_sel["name"]+" "+char_sel["surname"]

    S = player.subprocess_flags['commander name'] + " spins the bottle, landing on: "+nme
    player.bot_char.say(S)

    del player.subprocess_flags['commander name']
    return 1






