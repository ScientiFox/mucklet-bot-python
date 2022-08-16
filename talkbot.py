import websocket
import json
import threading
import math,time,random
import pickle,glob
from difflib import SequenceMatcher

from Mucklet_Python_Bot_V03 import *
from utility_bots import *

#Imports which are not standard
import aiml #THIS MODULE REQUIRES AIML PACKAGE

#Some things to do while idling
FLAVOR = [":stands around",
          ":silently talked to itself",
          ":whistles awkwardly",
          ":rubs its face",
          ":coughs politely into its hand",
          ":rubs its cheek",
          ":yawns",
          ":stretches"
          ]

UNSURE = ["I'm sorry, I didn't catch that...",
                    "Say again?",
                    "What was that? I didn't quite understand.",
                    "If I heard you right, I'm afraid I don't understand",
                    "Sorry, I didn't understand that",
                    "Oh yeah, definitely! Wait, what did you say?",
                    "Could you try again, that didn't make sense to me."
                   ]

MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"]

class talker:

    def __init__(self,player):
        self.kern = aiml.Kernel()

        brain_file = glob.glob("*.brn")

        if brain_file == []:
            self.kern.learn("std-startup.xml")
            supplement = glob.glob("aimls\\*.aiml")
            print("Loading AIMLs")
            for sup in supplement:
                print("learning "+sup.split("\\")[-1].split(".")[0])
                self.kern.learn(sup)
        else:
            print("")
            self.kern.loadBrain(brain_file[0])

        self.props = player.bot_char.char_models["core.char."+player.bot_char.cid+".owned"]
        self.name = self.props['name']
        self.gender = self.props['gender']
        self.species = self.props['species']

        db_time = self.props['created']/1000
        db_time = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(db_time))
        db_time = db_time.split(" ")[0]
        yr,mo,day = db_time.split("-")
        bd_str = MONTHS[int(mo)-1]+" "+day+", "+yr
        self.birthday = bd_str

        self.kern.setBotPredicate("name",self.name)
        self.kern.setBotPredicate("gender",self.gender)
        self.kern.setBotPredicate("species",self.species)
        self.kern.setBotPredicate("birthday",self.birthday)

        self.kern.setBotPredicate("religion","Deekultist")
        self.kern.setBotPredicate("favoritefood","electricity")
        self.kern.setBotPredicate("location","Sinder, the Rift")
        self.kern.setBotPredicate("master","Fox Lancaster-Okamimi")
        self.kern.setBotPredicate("genus","robot")
        self.kern.setBotPredicate("order","artificial intelligence")
        self.kern.setBotPredicate("favoritecolor","blue")

        #char_id : ["cont",time_recv]
        self.char_buffers = {}

        self.resp_delay = 6.0
        self.join_delay = 2.5

        print("Bot Predicates:")
        for a in self.kern._botPredicates.keys():
            print(a)

        print("Session Predicates:")
        for a in self.kern._sessions.keys():
            print(a)
            for b in self.kern._sessions[a]:
                print(b)

    def save_sessions(self):
        ses_set = self.kern._sessions
        self.kern.saveBrain("bot_chatter_brain.brn")
        f = open("bot_learned.chbot",'wb')
        pickle.dump(ses_set,f)
        f.close()

    def load_sessions(self,fle):
        f = open(fle,'rb')
        ses_set = pickle.load(f)
        f.close()
        self.kern._sessions = ses_set

        print("Session Predicates:")
        for a in self.kern._sessions.keys():
            print(a)
            for b in self.kern._sessions[a]:
                print(b,self.kern._sessions[a][b])
        

    def add_addr(self,addr,target):
        if target in self.char_buffers.keys():
            self.char_buffers[target] = self.char_buffers[target] + [(addr,time.time())]
        else:
            self.char_buffers[target] = [(addr,time.time())]

    def resp(self):

        to_resp_to = []
        for target in self.char_buffers:
            addrs = self.char_buffers[target]
            resp_set = []
            resp_curr = ""
            resp_time = -1
            is_join = True

            for addr in addrs:
                cont = addr[0]
                tme = addr[1]
                if resp_time == -1:
                    resp_curr = cont
                    resp_time = tme
                else:
                    if tme-resp_time < self.join_delay:
                        resp_curr = resp_curr + " "*(cont[0]!=" " and resp_curr[-1]!=" ")+cont
                        resp_time = tme
                    else:
                        resp_set = resp_set + [(resp_curr,resp_time)]
                        resp_curr = cont
                        resp_time = tme

            if resp_curr != "":
                resp_set = resp_set + [(resp_curr,resp_time)]

            self.char_buffers[target] = resp_set

            to_hold = []
            for addr in self.char_buffers[target]:
                if time.time() - addr[1] > self.resp_delay:
                    to_resp_to = to_resp_to + [(addr[0],addr[1],target)]
                else:
                    to_hold = to_hold + [addr]
            self.char_buffers[target] = to_hold

        to_resp_to.sort(key = lambda x:x[1])
        op_replies = []
        for addr in to_resp_to:
            op_resp = self.kern.respond(addr[0],addr[2])
            if op_resp != '':
                op_replies = op_replies + [(op_resp,addr[2])]
            else:
                op_replies = op_replies + [(UNSURE[random.randint(0,len(UNSURE)-1)],addr[2])]
            print("REPLYING TO:",addr[0]," WITH:",op_replies[-1][0])
        return op_replies


def talk_bot(player):

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
    player.subprocess_flags['chatter'] =  True

    bot_file = glob.glob("*.chbot")

    if bot_file == []:
        bot_chat_engine = talker(player)
    else:
        bot_chat_engine = talker(player)
        bot_chat_engine.load_sessions(bot_file[0])

    #Mode start-up message
    ALERT_MSG = "I am the talky bot, speak to me with @"+player.bot_char.char_models["core.char."+player.bot_char.cid+".owned"]['name'] + "= What you'd like to say"
    player.bot_char.say(ALERT_MSG)

    #Main loop
    while player.subprocess_flags['chatter']:

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
                    player.subprocess_flags['chatter'] = False
                    bot_chat_engine.save_sessions()
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
            bot_chat_engine.add_addr(cont_a,sender_a['id'])

            S = "-------- \n"
            S = S + "buffers: \n"
            for convo in bot_chat_engine.char_buffers:
                S = S + "  " + convo + ":\n"
                for a in bot_chat_engine.char_buffers[convo]:
                    S = S + "    " + a[0] + "\n"
            S = S + "--------"
            print(S)

        outputs = bot_chat_engine.resp()
        for op in outputs:
            #print("ADD MSG:",op)
            message_queue = [op] + message_queue


