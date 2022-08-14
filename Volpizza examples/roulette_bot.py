import websocket
import json
import threading
import math,time,random
import pickle,glob
from difflib import SequenceMatcher

from utility_bots import *

wheel_str = "0-28-9-26-30-11-7-20-32-17-5-22-34-15-3-24-36-13-1-27-10-25-29-12-8-19-31-18-6-21-33-16-4-23-35-14-2"
wheel_set = wheel_str.split("-")

BETS = { "straight":35,"single":35,
         "split":17,
         "street":11,
         "corner":8,"square":8,
         "six line":5,"double street":5,
         "basket":6,
         "low":1,"high":1,
         "red":1,"black":1,
         "even":1,"odd":1,
         "dozen":2,
         "column":2
        }

BOARD = [[0],
         [1,2,3],
         [4,5,6],
         [7,8,9],
         [10,11,12],
         [13,14,15],
         [16,17,18],
         [19,20,21],
         [22,23,24],
         [25,26,27],
         [28,29,30],
         [31,32,33],
         [34,35,36]
        ]

REDS = [32, 19, 21, 25, 34, 27, 36, 30, 23, 5, 16, 1, 14, 9, 18, 7, 12, 3]
BLACKS = [15, 4, 2, 17, 6, 13, 11, 8, 10, 24, 33, 20, 31, 22, 29, 28, 35, 26]

GREETING = ["stretches and waves \"Want to place a bet?\" ",
            "pops his knuckles.",
            "nods \"Feel like laying down a bet?\" ",
            "sits up suddenly, looking over.",
            " yips \"Oh!\" and jumps up at attention.",
            "shifts in place, nodding."
            ]

FLAVOR = ["yawns.",
          "yawns and stretches his arms up over his head.",
          "sniffs, wiggling.",
          "snuffs, dozing a little.",
          "lets his eyes flutter closed.",
          "stretches, wiggling.",
          "yips sleepily.",
          "rubs his nose.",
          "leans back comfortably.",
          "rolls his shoulders.",
          "yawns into a paw."
            ]

def parse_bet(txt):
    options = list(BETS.keys())

    matches = get_matches(txt,options)
    overlap = get_lead_cands(overlap_checker(matches))
    overlap.sort(key=lambda x:x[1])

    player_bets = []

    for i in range(len(overlap)):
        bt = overlap[i]
        bet_type = bt[0]
        if i <len(overlap)-1:
            bt2 = overlap[i+1]
            bet_contents = txt[bt[1]+bt[2]:bt2[1]]
        else:
            bet_contents = txt[bt[1]+bt[2]:]
        btct = ""
        for l in bet_contents:
            if not(l in [",",":",";","-"]):
                btct = btct+l
            else:
                btct = btct+" "

        if bet_type in ["straight","single"]:
            nums = []
            for n in btct.split(" "):
                try:
                    v = int(n)
                    nums = nums+[n]
                except:
                    pass
            ct = len(nums)
        elif bet_type == "low":
            nums = list(range(19)[1:])
            ct = 1
        elif bet_type == "high":
            nums = list(range(37)[19:])
            ct = 1
        elif bet_type == "even":
            nums = [2*a for a in range(19)]
            ct = 1
        elif bet_type == "odd":
            nums = [2*a+1 for a in range(18)]
            ct = 1
        elif bet_type == "red":
            nums = [32, 19, 21, 25, 34, 27, 36, 30, 23, 5, 16, 1, 14, 9, 18, 7, 12, 3]
            ct = 1
        elif bet_type == "black":
            nums = [15, 4, 2, 17, 6, 13, 11, 8, 10, 24, 33, 20, 31, 22, 29, 28, 35, 26]
            ct = 1
        elif bet_type == "street":
            nums = []
            ct = 0
            for n in btct.split(" "):
                try:
                    v = int(n)
                    if v==0:
                        pass
                    elif v%3 == 1:
                        nums = nums+[v,v+1,v+2]
                        ct+=1
                    elif v%3 == 2:
                        nums = nums+[v-1,v,v+1]
                        ct+=1
                    elif v%3 == 0:
                        nums = nums+[v-2,v-1,v]
                        ct+=1
                except:
                    pass
        elif bet_type == "column":
            nums = []
            ct = 0
            for n in btct.split(" "):
                try:
                    v = int(n)
                    if v==0:
                        pass
                    elif v%3 == 1:
                        nums = nums+[1+a*3 for a in range(12)]
                        ct+=1
                    elif v%3 == 2:
                        nums = nums+[2+a*3 for a in range(12)]
                        ct+=1
                    elif v%3 == 0:
                        nums = nums+[3+a*3 for a in range(12)]
                        ct+=1
                except:
                    pass
        elif bet_type == "dozen":
            nums = []
            ct = 0
            for n in btct.split(" "):
                try:
                    v = int(n)
                    if v in list(range(13)[1:]):
                        nums = nums + list(range(13)[1:])
                        ct+=1
                    elif v in list(range(25)[13:]):
                        nums = nums + list(range(25)[13:])
                        ct+=1
                    elif v in list(range(37)[25:]):
                        nums = nums + list(range(37)[25:])
                        ct+=1
                except:
                    pass
        player_bets = player_bets + [(bet_type,nums,ct)]

    return player_bets

def roulette_bot(player):

    player.subprocess_flags['roulette'] = True

    TAKE_BETS,PROMPT_BETS,SPIN_WHEEL,PAY_BETS = 0,1,2,3
    STATE = PROMPT_BETS

    START_SPIN,RUN_SPIN,END_SPIN = 0,1,2
    SUBSTATE = START_SPIN

    betting_timer=time.time()
    betting_period = 45.0

    player_points = {}
    player_bets = {}

    result = None

    announce_timer = time.time()
    announce_period = 180.0
    state,S = player.bot_char.getState()
    char_list = state[2]
    awake_list = []
    for a in char_list:
        if a['state'] == 'awake':
            awake_list = awake_list + [a]
    char_list = awake_list+[]

    flavor_timer = time.time()
    flavor_period = 180.0 + random.random()*(3*60)

    while player.subprocess_flags['roulette']:

        state,S = player.bot_char.getState()
        new_chars = state[2]
        awake_list = []
        for a in new_chars:
            if a['state'] == 'awake':
                awake_list = awake_list + [a]
        new_chars = awake_list+[]

        ids_old = [a['id'] for a in char_list]
        n_new = 0
        for char in new_chars:
            if not(char['id'] in ids_old): 
                n_new+=1
        if n_new>0 and time.time()-announce_timer > announce_period:
            r = random.randint(0,len(GREETING)-1)
            S = GREETING[r]
            player.bot_char.pose(S)            
            announce_timer = time.time()
        char_list = new_chars + []            

        if time.time()-flavor_timer > flavor_period:
            flavor_timer = time.time()
            r = random.randint(0,len(FLAVOR)-1)
            S = FLAVOR[r]
            player.bot_char.pose(S)

        mg = player.bot_char.msg_hist
        if len(mg) > 0:
            sender_m = mg[-1]['data']['char']
            cont_m = mg[-1]['data']['msg']
            del player.bot_char.msg_hist[-1]

            if sender_m['id'] == player.subprocess_flags['commander']:
                if cont_m=="stop":
                    player.bot_char.say("No longer spinning")
                    player.subprocess_flags['roulette'] = False
                else:
                    player.bot_char.message("Currently spinning roulette",commander)
                    notice_timer = time.time()
            else:
                player.bot_char.message("Sorry, I am currently running the roulette table",sender_m)
                notice_timer = time.time()
        else:
            pass


        if STATE == PROMPT_BETS and player.subprocess_flags['roulette']:

            betting_timer = time.time()
            player_bets = {}

            STATE = TAKE_BETS

        elif STATE == TAKE_BETS and player.subprocess_flags['roulette']:
            adr = player.bot_char.addr_hist
            if len(adr) > 0:
                sender_a = adr[-1]['data']['char']
                cont_a = adr[-1]['data']['msg']
                del player.bot_char.addr_hist[-1]

                bets = parse_bet(cont_a)
                if bets != []:
                    player_bets[sender_a['id']] = bets
                    chips = sum(bt[2] for bt in bets)
                    S = sender_a['name'] + " in for "+str(chips)+ " chip"+"s"*(chips>1)
                    player.bot_char.say(S)
                    time.sleep(2.0)

            if (time.time()-betting_timer < betting_period):
                pass
            else:
                if len(player_bets) > 0:
                    STATE = SPIN_WHEEL
                else:
                    STATE = PROMPT_BETS

        elif STATE == SPIN_WHEEL and player.subprocess_flags['roulette']:

            if SUBSTATE == START_SPIN:
                player.bot_char.pose("takes hold of the handle and spins the wheel...")
                time.sleep(3.5+random.random()*3.0)
                SUBSTATE = RUN_SPIN

            elif SUBSTATE == RUN_SPIN:
                player.bot_char.pose("watches as the wheel spins and spins...")
                time.sleep(3.5+random.random()*3.0)
                SUBSTATE = END_SPIN

            elif SUBSTATE == END_SPIN:
                r = random.randint(0,len(wheel_set)-1)
                n_hits = random.randint(0,3)+2
                hits = []
                for n in range(n_hits):
                    hits = hits + [wheel_set[r]]
                    r = (r + random.randint(1,4))%len(wheel_set)
                S = "waits as the ball bounces... "
                print(hits)
                for h in hits[:-1]:
                    S = S + str(h)+"... "
                player.bot_char.pose(S)
                time.sleep(4.5+random.random()*3.0)
                result = int(hits[-1])
                STATE = PAY_BETS
                SUBSTATE = START_SPIN

                S="Ball lands on "
                if result in BLACKS:
                    S = S + "Black "
                if result in REDS:
                    S = S + "Red "
                S = S + str(result)
                player.bot_char.say(S)
                time.sleep(3.5+random.random()*3.0)

        elif STATE == PAY_BETS and player.subprocess_flags['roulette']:

            winners = []
            for gamb in player_bets:
                gamb_winnings = 0
                for bt in player_bets[gamb]:
                    tp = bt[0]
                    nums = bt[1]
                    ct = bt[2]
                    gamb_winnings = gamb_winnings - ct
                    if result in nums:
                        gamb_winnings = gamb_winnings + BETS[tp]
                        winners = winners + [gamb]

                if gamb in player_points:
                    player_points[gamb] = player_points[gamb] + gamb_winnings
                else:
                    player_points[gamb] = gamb_winnings

            player_bets = {}

            people = player.bot_char.getPeople()
            lookup = {a['id']:a['name']+" "+a['surname'] for a in people}
            people = [(a['id'],a['name']+" "+a['surname']) for a in people]

            if len(winners) == 0:
                S = "No winners this round."
            elif len(winners) == 1 and winners[0] in lookup:
                S = lookup[winners[0]] + " wins this round!"
            elif len(winners) > 1:
                S = ""
                for per in people:
                    if per[0] in winners:
                        S = S + lookup[per[0]] +", "
                S = S[:-2]
                S = S + " win this round!"
            player.bot_char.say(S)
            time.sleep(5.0)

            gamblers_in = {}
            for per in people:
                if per[0] in player_points:
                    gamblers_in[per[1]] = player_points[per[0]]

            S = "Current Winnings: \n"
            for nme in gamblers_in:
                S = S + "`" + nme + ":` "+str(gamblers_in[nme]) + "\n"
            player.bot_char.pose(S)
            time.sleep(5.0)

            STATE = PROMPT_BETS


