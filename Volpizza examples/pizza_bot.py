import websocket
import json
import threading
import math,time,random
import pickle,glob
from difflib import SequenceMatcher

from utility_bots import *

pizza_file = open("pizza_list.txt")
pizza_lines = pizza_file.readlines()
pizza_file.close()

pizza_list = {}
i = 1
curr_name = None
while i < len(pizza_lines):
    lne = pizza_lines[i].strip()
    if lne != "" and curr_name == None:
        curr_name = lne
    elif lne != "" and curr_name != None:
        if lne[0]=="-":
            pizza_list[curr_name.lower()] = [lne]
        else:
            ing = lne.lower().split(",")
            ing =  [a.strip() for a in ing]
            pizza_list[curr_name.lower()] = ing
        curr_name = None
    i+=1

#for a in pizza_list:
#    print(a)
#    for b in pizza_list[a]:
#        print("  ",b)

ingredients = []
for a in pizza_list:
    for b in pizza_list[a]:
        if not(b in ingredients):
            ingredients = ingredients + [b]

RESPONSES = ["You got it!",
             "Coming right up!",
             "Sure thing",
             "Right-o",
             "On the double",
             ":gives you a thumbs up \"Comin' up!\" ",
             ":nods",
             ":snaps its fingers at you",
             ":gets right to it with a nod",
             "I'm on it",
             "Will do",
             "Gotcha"
            ]

FLAVOR = ["Wipes the counter",
          "Checks on the ovens",
          "Sweeps up some spilled cheese",
          "Nibbles on a pepperoni",
          "Shouts something incomprehensible at the staff",
          "Fusses with a garnish on a pizza",
          "Restocks the topping rack",
          "Adjusts the temperature- to the same level as before",
          "Cleans a dish",
          "Stacks take-away boxes",
          "Spins some dough on a paw"
          ]

GREETING = ["Welcome to VolPizza, what can I get you?",
            "Hey there, whatcha want?",
            "Welcome to VolPizza!",
            "How can I feed you today?",
            "Looking to get a slice?",
            "How about a pie?",
            "Welcome, can I get you a slice?"
            ]

UNSURE = ["Sorry, I don't think we have that one",
          "Afraid not.",
          "Don't think so",
          "I don't know that one",
          "Sorry, what's that?",
          "Nah, can't do it.",
          "Nope."
            ]

def clean_ing(ing):
    junk = ["-",",",".","!","?","~","\"","\'"]
    ing_cl = ""
    for a in ing:
        if not(a in junk):
            ing_cl = ing_cl + a
    return ing_cl

def pizza_bot(player):

    player.subprocess_flags['pizza'] = True

    order_queue = []
    #(pizza,person,time,dur)

    bet_ord_timer = time.time()
    bet_ord_period = 5.0

    flavor_timer = time.time()
    flavor_period = 180.0

    player.bot_char.say("Now serving Pizza!")
    time.sleep(4.0)

    announce_timer = time.time()
    announce_period = 40.0
    state,S = player.bot_char.getState()
    char_list = state[2]
    awake_list = []
    for a in char_list:
        if a['state'] == 'awake':
            awake_list = awake_list + [a]
    char_list = awake_list+[]

    while player.subprocess_flags['pizza']:

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
            player.bot_char.say(S)
            announce_timer = time.time()
        char_list = new_chars + []

        mg = player.bot_char.msg_hist
        if len(mg) > 0:
            sender_m = mg[-1]['data']['char']
            cont_m = mg[-1]['data']['msg']
            del player.bot_char.msg_hist[-1]

            if sender_m['id'] == player.subprocess_flags['commander']:
                if cont_m=="stop":
                    player.bot_char.say("No longer serving pizza, thank you for your patronage")
                    player.subprocess_flags['pizza'] = False
                else:
                    player.bot_char.message("Currently making pizza",sender_m)
                    notice_timer = time.time()
            else:
                player.bot_char.message("Sorry, I am currently making pizza",sender_m)
                notice_timer = time.time()
        else:
            pass

        if time.time()-flavor_timer > flavor_period:
            flavor_timer = time.time()
            r = random.randint(0,len(FLAVOR)-1)
            S = FLAVOR[r]
            player.bot_char.pose(S)

        if len(order_queue) > 0 and time.time()-bet_ord_timer > bet_ord_period:
            bet_ord_timer = time.time()

            order = order_queue[-1]

            if time.time()-order[2]>order[3]:
                pizza = order[0]
                person = order[1]['id']

                pizza_type = pizza[0]
                leave_outs = pizza[1]
                add_ins = pizza[2]

                ingrs = pizza_list[pizza_type] + add_ins
                put_on = []
                for top in ingrs:
                    if not(top in leave_outs):
                        put_on = put_on + [top]
                    else:
                        pass
                i = 0
                joins = []
                while i < len(put_on):
                    if put_on[i] in ['extra','more'] and i+1 < len(put_on):
                        print("  J1:",put_on[i],put_on[i+1])
                        joins = joins + [put_on[i]+" "+put_on[i+1]]
                        i+=2
                    elif put_on[i] in ['lots'] and i+2 < len(put_on):
                        print("  J2:",put_on[i],put_on[i+1],put_on[i+2])
                        joins = joins + [put_on[i]+" of "+put_on[i+2]]
                        i+=3
                    elif put_on[i] in ['a'] and i+3 < len(put_on):
                        print("  J3:",put_on[i],put_on[i+1],put_on[i+2],put_on[i+3])
                        joins = joins + [put_on[i]+put_on[i+1]+" of "+put_on[i+3]]
                        i+=4
                    else:
                        print("  J4:",put_on[i])
                        joins = joins + [put_on[i]]
                        i+=1
                print("JOINS:",joins)
                put_on = joins + []

                if not(put_on[0][0]=="-"):
                    S = pizza_type + " pizza " + "with "*(len(put_on)>0)
                else:
                    S = pizza_list[pizza_type][0][1:] + "with "*(len(put_on)>1)
                    del put_on[0]

                if len(put_on) == 0:
                    pass
                elif len(put_on) == 1:
                    S = S + put_on[0]
                elif len(put_on) == 2:
                    S = S + put_on[0] + " and " + put_on[1]
                else:
                    for top in put_on[:-1]:
                        S = S + top + ", "
                    S = S[:-2]
                    S = S + " and " + put_on[-1]

                S = S+ ", order up!"

                player.bot_char.address(S,person)

                del order_queue[-1]
            else:
                pass

        adr = player.bot_char.addr_hist
        if len(adr) > 0:
            sender_a = adr[-1]['data']['char']
            cont_a = adr[-1]['data']['msg']
            del player.bot_char.addr_hist[-1]

            pizza_opts = list(pizza_list.keys())
            matches = get_matches(cont_a,pizza_opts)
            order_set = overlap_checker(matches)
            order = get_lead_cands(order_set)
            order.sort(key=lambda x:x[1])
            print("ORDER:",order)

            matches = get_matches(cont_a,['suggest','recommend'])
            sugg = overlap_checker(matches)
            if len(sugg) > 0:
                sugg_max = max([a[3] for a in sugg])
                if sugg_max < 0.9:
                    sugg = []

            if len(sugg) > 0:
                S = "I can recommend a "
                pizzas = list(pizza_list.keys())
                rs = [pizzas[random.randint(0,len(pizza_list)-1)] for i in range(3)]
                S = S + rs[0] + ", a " + rs[1] + ", or a " + rs[2]
                player.bot_char.address(S,sender_a['id'])
                time.sleep(2.0+random.random()*2.5)

            elif len(order) > 0:

                negatives = [" no ", "without"]
                positives = ["with","including"]
                modifiers = negatives+positives

                matches = get_matches(cont_a,modifiers)
                modifiers = overlap_checker(matches)
                print(modifiers)
                modifiers = get_lead_cands(modifiers)
                print(modifiers)
                modifiers.sort(key = lambda x:x[1]+x[2])
                print(modifiers)

                leave_outs = []
                add_ins = []
                for i in range(len(modifiers)):
                    if i < len(modifiers)-1:
                        section = cont_a[modifiers[i][1]+modifiers[i][2]:modifiers[i+1][1]]
                    else:
                        section = cont_a[modifiers[i][1]+modifiers[i][2]:]
                    base = ""
                    for l in section:
                        if not(l in [",",";","-","'"]):
                            base = base + l
                        else:
                            base = base + " "
                    for ing in base.split(" "):
                        if not(ing in ['and','or','any','']) and modifiers[i][0] in negatives:
                            leave_outs = leave_outs + [clean_ing(ing)]
                        if not(ing in ['and','or','any','']) and modifiers[i][0] in positives:
                            add_ins = add_ins + [clean_ing(ing)]

                pizza = (order[0][0],leave_outs,add_ins)
                print(pizza)
                person = sender_a
                tme = time.time()
                if not(pizza_list[pizza[0]][0][0] == "-"):
                    duration = len(pizza_list[pizza[0]])*3.0
                else:
                    duration = len(pizza_list[pizza[0]][0])*0.5
                order_queue = [(pizza,person,tme,duration)]+order_queue

                r = random.randint(0,len(RESPONSES)-1)
                S = RESPONSES[r]
                if S[0] == ":":
                    player.bot_char.pose(S[1:])
                else:
                    player.bot_char.address(S,sender_a['id'])
                time.sleep(2.0+random.random()*2.5)

            else:
                S = UNSURE[random.randint(0,len(UNSURE)-1)]
                player.bot_char.address(S,sender_a['id'])
                time.sleep(2.0+random.random()*2.5)
                







