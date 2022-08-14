import websocket
import json
import threading
import math,time,random
import pickle,glob
import hashlib,codecs,hmac

'''
Implementation of the Mucklet API for building bots in python.

The basic idea is that all you really need from Resgate is the _sendNow
function, everything else is housekeeping. _sendNow is just a WebSocket
send with Resgate formatting.

The rest is implementing two parts- the bot and bot character classes,
the former holding the top-level stuff like authentication, the latter
managing the specific stuff for the character autonomously controlled.

'''

from config_bot import *

pepper = "TheStoryStartsHere"

m = hashlib.sha256()
m.update(bytes(password,'UTF-8'))
hx = m.hexdigest()
PASS = codecs.encode(codecs.decode(hx, 'hex'), 'base64').decode()[:-1]

hx = hmac.new(bytes(pepper,'UTF-8'),msg=bytes(password,'UTF-8'), digestmod = hashlib.sha256).hexdigest()
HASH = codecs.encode(codecs.decode(hx, 'hex'), 'base64').decode()[:-1]

BOT_NAME = (bt_name,bt_surname)

print("USER:",USER)
print("PASS:",PASS)
print("HASH:",HASH)

#_sendNow IDs- for tracking replies by type
LOGIN = 1
GET_PLAYER = 2
GET_CHARS = 3
CHAR_CTRL = 4
CTRL_BOT = 5
WAKEUP = 6
GO = 7
SAY = 8
SLEEP = 9
SUBSCRIBE = 10
UNSUBSCRIBE = 11
POSE = 12
TELEPORT = 13
WHISPER = 14
ADDRESS = 15
MESSAGE = 16
PING = 17

#If you want *all* the diagnostics
VERBOSE = False

def _sendNow(ws,method,ind=0,params = None,verbose=VERBOSE):
    #Helper function to wrap WS function
    request = {"id":ind,"method":method,"params":params}
    msg = json.dumps(request)
    ws.send(msg)
    if verbose:
        print("sent: ",msg)
        print("--------")

class bot:
    #bot supra class for login and meta parameters

    def __init__(self):
        #Set the login stuffs
        self.user = USER
        self.hash = HASH
        self.password = PASS
        self.bot_name = BOT_NAME

        self.ws = None #For the Websocket- filled in after so the on_message
                       # and etc. can be methods

        #Basic RIDs for getting assets
        self.player_rid = None
        self.char_id = None

        #The atached bot character object
        self.bot_char = None

        #Make a lot of noise in the console
        self.verbose = VERBOSE
        self.keep_awake = False

        #boot params
        self.started = False
        self.boot_stage = 0

        #Bot thread manager
        self.is_go = True

        #diagnostic
        self.MSGS_TOCHECK = []

        #Place for a bot to save some sort of observational data to
        self.save_data = None

        #Passable generic flag system for subprocess control
        self.subprocess_flags = {}

    def set_ws(self,_ws):
        #Attach the websocket- done after ws is initialized w/
        # methods from this class
        self.ws = _ws

    def keepAwake(self,period):
        #Function to be run in a separate thread, pings the bot every period seconds to keep it awake

        #Wait until the bot is fully booted
        while self.boot_stage != 6:
            pass

        timer = time.time() #Start up the event timer
        self.keep_awake = True #Thread loop variable (killed by on_close in WS)

        #Run untill killed externally
        while self.keep_awake and self.is_go:

            #Every period seconds, do a call
            if time.time()-timer > period:
                self.bot_char.ping() #Send the ping
                timer = time.time() #Reset the timer

                #Be loud?
                if self.verbose:
                    print("Pinged...")

            #Do nothing in between pings
            else:
                pass

    def boot(self):

        #Boot sequence started in separate thread, waits until on_open is called in WS
        #In thread to have messages, so it's run in order to build the char objects cleanly
        while not(self.started):
            pass

        print("AUTHENTICATING")
        #Authenticate and get the player info
        params = {  "name":self.user,
                    "hash":self.hash}
        _sendNow(self.ws,'auth.auth.login',params=params,ind=LOGIN)
        while (self.boot_stage == 0):
            pass

        print("GETTING PLAYER RID")
        #Get Player rid
        _sendNow(self.ws,'call.core.getPlayer',ind=GET_PLAYER)
        while(self.boot_stage == 1):
            pass

        print("GETTING CHARS SET")
        #Get character data
        _sendNow(self.ws,"get."+self.player_rid,ind=GET_CHARS)
        while(self.boot_stage == 2):
            pass

        print("CONTROLLING BOT")
        #Take control of the bot character
        method = "call."+self.player_rid+".controlChar"
        _sendNow(self.ws,method,params={'charId':self.bot_char.cid},ind=CTRL_BOT)
        while(self.boot_stage == 3):
            pass

        print("WAKING BOT")
        #Wake the bot up
        method = "call.core.char."+self.bot_char.cid+".ctrl.wakeup"
        _sendNow(self.ws,method,ind=WAKEUP)
        while(self.boot_stage == 4):
            pass

        print("GETTING CHAR DATA")
        #Get looking character data
        _sendNow(self.ws,"subscribe."+self.player_rid,ind=GET_CHARS)
        while(self.boot_stage == 5):
            pass

        #Done booting
        print("BOOTED")

    def on_open(self,ws):
        #All it does is trigger the boot thread
        self.started = True

    def on_message(self,ws,message):
        #Message handler- basically everything taps here
        msg = json.loads(message) #make it a dictionary

        #Be loud?
        if self.verbose:
            print(json.dumps(msg, indent=2, sort_keys=True))
            print("--------")

        #Error message handler- currently just to pass boot if already controlled or awake
        if 'error' in msg and self.boot_stage < 6:
            if self.boot_stage == 3 and msg['id'] == CTRL_BOT:
                self.boot_stage = 4
            if self.boot_stage == 4 and msg['id'] == WAKEUP:
                self.boot_stage = 5
        elif 'error' in msg:
            #Prints errors outside boot cycle
            print(msg)

        #For reply responses
        if 'result' in msg and self.boot_stage < 6:

            #Boot Cycle syncing
            #The login and setup are only allowed to proceed once each
            #  requested message arrives, and is processed
            if self.boot_stage == 0 and msg["id"] == LOGIN:
                self.boot_stage = 1
            if self.boot_stage == 1 and msg["id"] == GET_PLAYER:
                self.player_rid = msg['result']['rid']
                self.boot_stage = 2
            if self.boot_stage == 2 and msg['id'] == GET_CHARS:
                #Grab the char data to search to ID the bot
                chars = msg["result"]["collections"][self.player_rid+".chars"]
                chars = [a['rid'] for a in chars] #Get the actual refs
                for ch in chars:
                    #Loop over the chars
                    char_data = msg["result"]["models"][ch]
                    print("    " + char_data["name"] + " " + char_data["surname"] + " : " + char_data['id'])
                    if char_data["name"] == BOT_NAME[0] and char_data["surname"] == BOT_NAME[1]:
                        #If find the bot's name, get its ID and make the char object
                        cid = char_data["id"]
                        self.bot_char = char(cid,self)
                self.boot_stage = 3
            if self.boot_stage == 3 and msg['id'] == CTRL_BOT:
                self.boot_stage = 4
            if self.boot_stage == 4 and msg['id'] == WAKEUP:
                self.boot_stage = 5
            if self.boot_stage == 5 and msg['id'] == GET_CHARS:

                #Grab the initial player data models and collections after 1st subscription
                self.bot_char.char_models = msg["result"]["models"]
                self.bot_char.char_collections = msg["result"]["collections"]

                #Mark done with boot cycle
                self.boot_stage = 6

        elif 'result' in msg and self.boot_stage == 6:
            #Currently nothing- was some diagnostic, now obsolete
            #   might be useful in future, though
            if msg['id'] == GET_CHARS:
                pass
            if msg['id'] == GO:
                pass

        #For event pings
        if 'event' in msg:

            #Break up the event type into RID and an action type
            evt = msg['event']
            evt_parse = evt.split(".")
            obj = evt_parse[1]
            Id = evt_parse[2]
            prop = evt_parse[3]
            act = evt_parse[4]

            #ID of the resource being modified
            rid = 'core.'+obj+'.'+Id+'.'+prop

            #Be loud?
            if self.verbose:
                print(act+" "+rid)

            if act == 'change':
                #For applying changes to models and collections

                if 'values' in msg['data']:
                    #Loop over all values and update targets
                    for v in msg['data']['values']:
                        if rid in self.bot_char.char_models:
                            self.bot_char.char_models[rid][v]  = msg['data']['values'][v]
                        if rid in self.bot_char.char_collections:
                            self.bot_char.char_collections[rid][v]  = msg['data']['values'][v]
                        if self.verbose:
                            print("Updated: "+ str(rid) + "<"+str(v)+">" +" with: "+ str(msg['data']['values'][v]))

                if 'models' in msg['data']:
                    #Loop over all update models and replace the old ones
                    for m in msg['data']['models']:
                        self.bot_char.char_models[m] = msg['data']['models'][m]
                        if self.verbose:
                            print("Updated model: "+ str(rid))

                if 'collections' in msg['data']:
                    #Loop over all collections and replace
                    for c in msg['data']['collections']:
                        self.bot_char.char_collections[c] = msg['data']['collections'][c]
                        if self.verbose:
                            print("Updated collection: "+ str(c))

            if act == 'add':
                #insert collection value- currently assuming always at idx=0
                #   that assumption might be bad, but so far so good and
                #   Accipiter hasn't got back to me about that yet
                self.bot_char.char_collections[rid] = [msg['data']['value']] + self.bot_char.char_collections[rid]

                #Add models to char_models if any are there
                if 'models' in msg['data']:
                    for m in msg['data']['models']:
                        self.bot_char.char_models[m] = msg['data']['models'][m]
                if self.verbose:
                    print(msg)

            if act == 'remove':
                #delete target location in target RID
                if rid in self.bot_char.char_collections: #Check if in since error, just in case
                    del self.bot_char.char_collections[rid][msg['data']['idx']]
                if self.verbose:
                    print(msg)

            if act == 'out':
                #Output event handler-
                typ = msg['data']['type'] #message type
                cont = msg['data']['msg'] #contents of message
                name = msg['data']['char']['name'] + " " + msg['data']['char']['surname'] #Name of actor
                ID = msg['data']['char']['id']

                if typ == 'say':
                    #Add 'say' for these
                    print(name + " says: "+cont)
                    pass
                elif typ in ['pose','sleep','travel','leave','arrive','wakeup']:
                    #Just print the rest of the notices

                    #A check to see if the bot has traveled
                    if typ == 'travel' and ID == self.bot_char.cid:
                        if 'travel_counter' in self.subprocess_flags:
                            self.subprocess_flags['travel_counter'] = self.subprocess_flags['travel_counter'] + 1
                        else:
                            self.subprocess_flags['travel_counter'] = 1

                    print(name + ": "+cont)
                    pass
                elif typ == 'whisper':
                    print(name+" whispers: "+cont)
                    pass
                elif typ == 'ooc':
                    print(name+" says ooc: "+cont)
                    pass


                #Message and addresses are specific to the bot, so they get saved
                #   in queues for processing
                elif typ == 'message':
                    #If for the bot character and not already saved
                    if msg['data']['target']['id'] == self.bot_char.cid and not(msg['data']["id"] in self.bot_char.msg_ids):
                        #Save the message itself
                        self.bot_char.msg_hist = [msg] + self.bot_char.msg_hist
                        #Mark the mesage as saved
                        self.bot_char.msg_ids[msg['data']['id']] = None
                        #Print it
                        print(name + ": PMs "+msg['data']['target']['name']+": "+cont)
                    else:
                        pass
                #Same as above, but for addresses
                elif typ == 'address':
                    if msg['data']['target']["id"] == self.bot_char.cid and not(msg['data']["id"] in self.bot_char.addr_ids):
                        self.bot_char.addr_hist = [msg] + self.bot_char.addr_hist
                        self.bot_char.addr_ids[msg['data']["id"]] = None
                        print(name + ": Addressed "+msg['data']['target']['name']+": "+cont)
                    else:
                        pass
                else:
                    #If we're not handling the messae yet, just print it out JSON style
                    #   that way it's easy to examine and write a new handler
                    print(msg)

            #A spacer to separate each events' reporting if loud
            if self.verbose:
                print("--------")
            pass

    def on_error(self,ws,error):
        #Just report errors
        print('There was an error {}'.format(error))

    def on_close(self,ws,a,b):
        #Why are there three parameters? a,b are always None, None
        self.keep_awake = False #turn off kee-awake pings
        self.is_go = False #mark the bot as shut down to stop threads
        print(a)
        print(b)
        print("closed")

class char:
    #Class to hold the bot info & methods

    def __init__(self,_cid,_player):
        #Start up by processing in the getPlayer info for the bot char
        self.cid = _cid

        #Models and collections which have had data presented to the bot
        self.char_models = None
        self.char_collections = None

        #Refer to parent explicitly, I hate inheritance
        self.player = _player

        #Address history (for interaction)
        self.addr_hist = []
        self.addr_ids = {}

        #Message history, same as ^
        self.msg_hist = []
        self.msg_ids = {}

    def getExits(self):
        #A helper function to get the current exits for the bot char
        if "core.char."+self.cid+".owned" in self.char_models:
            char_model = self.char_models["core.char."+self.cid+".owned"]
            char_inroom = char_model['inRoom']['rid']
        else:
            return []
        if char_inroom+".exits" in self.char_collections:
            exits = self.char_collections[char_inroom+".exits"]
            exit_list = [a['rid'] for a in exits]
            return exit_list
        else:
            return []

    def getState(self):
        #A helper function to build the salient state data for the bot character

        #Grab char data, exit RIDs, and people in the current room
        if "core.char."+self.cid+".owned" in self.char_models:
            char_model = self.char_models["core.char."+self.cid+".owned"]
        else:
            char_model = {}
        exits = self.getExits()
        people = self.getPeople()

        #primary output- a state list
        state_var = [char_model,exits,people]

        #Also make a pretty print diagnostic
        S = "Character: "+"\n"
        S = S + "  " + "id: " + str(char_model["id"])+"\n"
        S = S + "  " + "idle: " + str(char_model["idle"])+"\n"

        S = S + "  " + "inRoom: " + str(self.char_models[char_model["inRoom"]['rid']]['name'])+"\n"
        S = S + "  " + "name: " + str(char_model["name"]) + " " + str(char_model["surname"])+"\n"
        S = S + "  " + "state: " + str(char_model["state"])+"\n"

        S = S + "People: " +"\n"
        for a in people:
            S = S  + "  " + str(a['name']) + " " + str(a['surname'])+"\n"

        S = S + "Exits: " +"\n"
        for a in exits:
            S = S + "  " + str(a) +"\n"

        #Return actual data and pretty print
        return state_var,S

    def getPeople(self):
        #A helper function to get the characters currently in the room
        if "core.char."+self.cid+".owned" in self.char_models:
            char_model = self.char_models["core.char."+self.cid+".owned"]
            char_inroom = char_model['inRoom']['rid']
        else:
            return []
        if char_inroom+".chars" in self.char_collections:
            people = self.char_collections[char_inroom+".chars"]
            people = [a['rid'] for a in people]
            people = [self.char_models[a] for a in people]
            return people
        else:
            return []

    ####
    # The following functions are all utility wrappers on Mucklet character calls
    ####

    def gosleep(self):
        method = "call.core.char."+self.cid+".ctrl.sleep"
        _sendNow(self.player.ws,method,params={},ind=SLEEP)

    def say(self,msg):
        method = "call.core.char."+self.cid+".ctrl.say"
        _sendNow(self.player.ws,method,params={'msg':msg},ind=SAY)

    def go(self,ext):
        method = "call.core.char."+self.cid+".ctrl.useExit"
        _sendNow(self.player.ws,method,params={'exitId':ext.split(".")[-1]},ind=GO)

    def pose(self,msg):
        method = "call.core.char."+self.cid+".ctrl.pose"
        _sendNow(self.player.ws,method,params={'msg':msg},ind=POSE)

    def teleport(self,nodeId):
        method = "call.core.char."+self.cid+".ctrl.teleport"
        _sendNow(self.player.ws,method,params={'nodeId':nodeId},ind=TELEPORT)

    def whisper(self,msg,targetId,pose='whispers'):
        method = "call.core.char."+self.cid+".ctrl.whisper"
        _sendNow(self.player.ws,method,params={'msg':msg,'charId':targetId,'pose':pose},ind=WHISPER)

    def address(self,msg,targetId):
        method = "call.core.char."+self.cid+".ctrl.address"
        _sendNow(self.player.ws,method,params={'msg':msg,'charId':targetId},ind=ADDRESS)

    def message(self,msg,targetId):
        method = "call.core.char."+self.cid+".ctrl.message"
        _sendNow(self.player.ws,method,params={'msg':msg,'charId':targetId},ind=MESSAGE)

    def ping(self):
        method = "call.core.char."+self.cid+".ctrl.ping"
        _sendNow(self.player.ws,method,params={},ind=PING)



        
