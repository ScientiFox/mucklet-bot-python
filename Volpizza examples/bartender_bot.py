import websocket
import json
import threading
import math,time,random
import pickle,glob
from difflib import SequenceMatcher

from utility_bots import *

def process_file(lines):
    units = []
    curr_cock = []
    for ln in lines:
        if ln != "\n":
            curr_cock = curr_cock + [ln[:-1]]
        else:
            units = units + [curr_cock+[]]
            curr_cock = []
    return units


####
#Section to make the bot a bartender
####

#Open recipe lists from files
f = open('drinks_list.txt')
drinks_base = f.readlines()
f.close()

f = open('coffees_list.txt')
drinks_coffees = f.readlines()
f.close()

f = open('cocktails_list.txt')
drinks_cocktail = f.readlines()
f.close()

#Turn list files into useful lookups
drinks_base = process_file(drinks_base)
drinks_coffees = process_file(drinks_coffees)
drinks_cocktail = process_file(drinks_cocktail)

#Make the cocktails lists
cocktails = {}
for ck in drinks_cocktail: #For each one
    name = ck[0].lower() #Peel the name
    verbs = [] #make a list of the verbs you can use
    vb = ck[-2].lower().split(" ") #parse out the actual words for verbs
    for v in vb:
        if v != '':
            verbs = verbs + [v] #Read all the non empty ones into a list
    glass = ck[-1].lower()#Grab the kind of glass it goes in
    ingredients = [a.split("cl")[-1].lower() for a in ck[1:-2]] #break up the ingredient list for removing 'cl' volumes
    ingredients = [a.strip() for a in ingredients] #peel off whitespace for kerning
    cocktails[name] = [ingredients,verbs,glass] #Add the actual parsed values to the lookup

#Basically the same as above
coffees = {}
for ck in drinks_coffees:
    name = ck[0].lower()
    verbs = []
    vb = ck[-2].lower().split(" ")
    for v in vb:
        if v != '':
            verbs = verbs + [v]
    glass = ck[-1].lower()
    ingredients = [a.split("cl")[-1].lower() for a in ck[1:-2]]
    ingredients = [a.strip() for a in ingredients]
    coffees[name] = [ingredients,verbs,glass]

#The regular drinks are just line items
drinks = [a[0] for a in drinks_base]

#The full menu is a list of all the drink lookups
menu = [drinks,coffees,cocktails]

#A table of synonyms for spicing up the listed recipes
SYNONYMS = {"pours":["drains","decants","splashes","pours","pours","pours"],
            "drops":["dumps","drizzles","sprinkles"],
            "stirs":["blends","whisks","beats","stirs","stirs"],
            "mixes":["combines","infuses","mingles","mixes","mixes","mixes"],
            "shakes":["rattles","rustles","shakes","shakes","shakes","shakes"],
            "strains":["filters","sifts","strains","strains"],
            "covers":["blankets","fills","covers","fills"],
            "layers":["coats","places","builds"],
            "cup":["glass","mug","mason jar","tumbler"],
            "makes":["prepares","fixes","serves","makes","makes","makes"]
            }

#A list of on-delivery replies (one for singular drinks, one for several)
DELIVERY_SINGULAR = ["Here you go!",
                     "Order up!",
                     "All ready!",
                     "Your drink is ready!",
                     "Enjoy!",
                     "Enjoy your drink, [sir and/or madam](https://static.wikia.nocookie.net/fallout/images/5/55/NVVendortronGreetingsSirOrMadam.ogg/revision/latest?cb=20130701124210)!",
                     "Enjoy your drink!",
                     "Hope you like it!",
                     "Hope you like drinking it as much as I did making it!"
                    ]
DELIVERY_PLURAL =  ["Here you go!",
                     "Order up!",
                     "All ready!",
                     "Your drinks are ready!",
                     "Enjoy!",
                     "Enjoy your drinks, sir and/or madam!",
                     "Enjoy your drinks!",
                     "Hope you like it!",
                     "Hope you like drinking them as much as I did making them!"
                    ]

#Some things to say when the request doesn't match anything
UNSURE = ["I'm sorry, I didn't catch that...",
                    "Say again?",
                    "What was that? I didn't quite understand.",
                    "If I heard you right, I'm afraid I can't make that one.",
                    "Sorry, I didn't understand that",
                    "Oh yeah, definitely! Wait, what did you say?",
                    "Could you try again, that didn't make sense to me."
                   ]

#Some things to say when the order goes through
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

#The list of sinder originals- names and recipes
SINDER_ORIGINALS = {"wolfys espresso":[":fetches a bottle of vodka and Bepi Tosolini's Exprè, and sets them on the bar.",
                                        ":makes a single espresso, then fishes an empty martini glass and the sugar syrup out of the fridge.",
                                        ":pours syrup, vodka, espresso and the liquer into a shaker, tops it up with a handful of ice, and shakes vigorously.",
                                        ":pours the mix into the chilled glass, waiting for the thick white foam to set in, and finally tops it with two coffee beans."
                                        ],
                    "ladys milkshake":[":pulls out a bottle of whipped cream vodka and plugs in the blender.",
                                        ":pours ice, milk, chocolate mix, and bananas into the blender, mixing them together with whipped cream, double chocolate vodka and macchiatto mix.",
                                        ":once the ice is pureed, dispenses the milkshake into a tall glasses and plants a dash of crushed peppermint on the top."
                                        ],
                    "morgans orapple juice":[":takes a bottle of orange juice and a bottle of apple juice, and mixes them together in a glass."
                                            ],
                    "louve chardonnay":[":pours the wine into a glass.",
                                        "It's bold, moderately acidic; the tasting reminds of oak, butter, peach, weredragon saliva; a floral nose with wet grass, tones of minerals."
                                            ],
                    "sauvignon blanc":[":pours the wine into a glass.",
                                       "It's light and dry, slightly acidic. Tasting notes are reminiscent of citrus, pear, unicorn semen, honey."
                                            ],
                    "special merlot":[":pours the wine into a glass.",
                                      "Light and balanced, easy to enjoy, but noticeably tannic – as merlot does."
                                            ],
                    "pinotage":[":pours the wine into a glass.",
                                "Dry and bold, mildly acidic, tastes of oak, chocolate, with the earthy smells and hints of a wolf. Shinyuu's favourite."
                                            ],
                    }



#The suggestions lists
SUGGESTIONS = {"Fruity drinks":["Pina Colada","Cosmopolitan","Grasshopper"],
               "Sinder originals":["Wolfy's Espresso","Lady's Milkshake","Morgan's Orapple Juice"],
               'louve wines':["Louve Chardonnay","Sauvignon Blanc","Special Merlot","Pinotage"]
                }

#A helper function to take a programmed reply and swap out synonyms for variability
def verbosify(txt,synonyms):
    S_verbosity = txt.split(" ")#Break up into words

    S = ""
    for wrd in S_verbosity:#For each word 
        if wrd in synonyms: #check if there's a synonym
            alts = [wrd]+synonyms[wrd] #if there is, grab one at random and replace the original with it
            r = random.randint(0,len(alts)-1)
            S = S + alts[r] + " "
        else: #Otherwise just put the original in
            S = S + wrd + " "
    S = S[:-1]#remove trailing space
    return S

#Helper function to mix up a list randomly
def scramble_list(lst):
    if len(lst)>1: #if there's more than one entry

        if type(lst) == type({}):
            old_list = list(lst.keys)+[] #copy the old list
        else:
            old_list = lst+[]

        new_list = [] #empty new one
        while len(old_list)>0: #while the old one isn't empty
            r = random.randint(0,len(old_list)-1) #take a random one out
            new_list = new_list + [old_list[r]] #put it in the new one
            del old_list[r] #remove it from the old one
        return new_list
    else:
        return lst #Can't re-order just one element

def make_drink(drink,menu):
    #To make a drink
    #Drink: (name,ind,size,type)

    #If it's a regular one without a recipe    
    if drink[3] == 'drink':
        recipe = None #Nothing here
        S = "pours the "+drink[0]+" into a cup" #basic to make sentence
        S = verbosify(S,SYNONYMS) #Mix up the synonyms
        return ":"+S,'drink' #Return the string and the type

    #For a coffee drink
    elif drink[3] == 'coffee':
        recipe = menu[1][drink[0]] #Grab recipe from lookup
        typ = 'coffee' #mark type

    #Same as above
    elif drink[3] == 'cocktail':
        recipe = menu[2][drink[0]]
        typ = 'cocktail'

    ingredients = recipe[0] #Peel the ingredients from the recipe
    verbs = recipe[1] #Grab the making verbs
    vessel = recipe[2] #Grab the cup

    #If there's more than one ingredient
    if len(ingredients) > 1:
        n_ing = random.randint(2,len(ingredients)) #Pick a random number of them to use
        n_ing = min([3,n_ing]) #cap at three
    else:
        n_ing = 1 #If only one, not going to do any more than 1

    #If no ingredients listed- use a generic (shouldn't happen for a good list file)
    if n_ing == 0:
        S = ":makes the "+drink[0]+" in a "+vessel
        S = verbosify(S,SYNONYMS) #Mix up the words, though
        return S,typ
    else:
        #If more than 0 ingredients
        r_verb = random.randint(0,len(verbs)-1)
        S = ":"+verbs[r_verb] + " " #Initial string- : for an action
        ings = scramble_list(ingredients) #mix up the list

        #Some filler phrases to make account for it only being a few inredients
        RECIPE_FILS = [" and some other things into a ",
                       " among other ingredients, into a ",
                       ", and a few other things into a ",
                       " with a couple other things into a ",
                       " and a few other things into a ",
                       " along with other ingredients into a ",
                       " aside with a couple extra add ins into a "
                       ]
        rf = random.randint(0,len(RECIPE_FILS)-1)

        #For one ingredient
        if n_ing == 1:
            S = S + ings[0] + RECIPE_FILS[rf]+vessel #just add them together
        elif n_ing == 2: #For two
            S = S + ings[0] + " and " + ings[1] + RECIPE_FILS[rf] +vessel #Use 'and'
        elif n_ing == 3: #For three
            S = S + ings[0] + ", " + ings[1] + ", and " + ings[2] +  RECIPE_FILS[rf]+vessel #Add a comma!

        #mix up the synonyms
        S = verbosify(S,SYNONYMS)
        return S,typ #Return string and drink type

def find_drinks(txt,menu):
    #function to match text to available things on the menu

    #remove possessive from the string (shouldn't be junk, want to not split by it)
    txt_pos = txt.split("'")
    txt = ""
    for a in txt_pos:
        txt = txt + a

    #Grab all three categories' lists
    drinks = menu[0]
    coffees = menu[1]
    cocktails = menu[2]

    #Check text against each list
    drinks_hits = get_matches(txt,drinks)
    coffee_hits = get_matches(txt,coffees)
    cocktail_hits = get_matches(txt,cocktails)

    #Candidate lists
    candidates = []

    #For each set of matches, only keep over 90% correlation ones
    for cn in drinks_hits:
        if cn[3] > 0.9:
            candidates = candidates + [(cn[0],cn[1],cn[2],'drink')] #save the name, position, length, and type
    for cn in coffee_hits:
        if cn[3] > 0.9:
            candidates = candidates + [(cn[0],cn[1],cn[2],'coffee')]
    for cn in cocktail_hits:
        if cn[3] > 0.9:
            candidates = candidates + [(cn[0],cn[1],cn[2],'cocktail')]

    #Run the overlap checker to get the final matches
    overlap_check = overlap_checker(candidates)

    return overlap_check

def bartender(player):

    player.subprocess_flags['bartending'] = True

    commander = player.subprocess_flags['commander']

    announce_timer = time.time()
    announce_period = 150.0
    state,S = player.bot_char.getState()
    char_list = state[2]
    awake_list = []
    for a in char_list:
        if a['state'] == 'awake':
            awake_list = awake_list + [a]
    char_list = awake_list+[]

    sender_a = None
    cont_a = None

    flavor_timer = time.time()
    flavor_period = 200.0 + random.random()*(3*60)

    message_queue = []
    message_timer = time.time()
    BASE_PERIOD = 7.0
    message_period = BASE_PERIOD
    msg_first = True

    char_drink_ct = {}

    ALERT_MSG = "Hello, I am Iam the bartending bot! Order a drink by addressing me, like: `@"+player.bot_char.getState()[0][0]["name"]+"= I'd like a martini`! Or if you like, I can `suggest` some __Sinder Originals__!"

    #player.bot_char.say("I am now ready to serve drinks!")
    player.bot_char.say(ALERT_MSG)

    while player.subprocess_flags['bartending']:

        if len(message_queue)>0:
            flavor_timer = time.time()
        if len(message_queue)==0 and time.time()-flavor_timer > flavor_period:
            msg_flav = FLAVOR[random.randint(0,len(FLAVOR)-1)]
            message_queue = [(msg_flav,None)] + message_queue
            flavor_timer=time.time()
            flavor_period = 120.0 + random.random()*(3*60)

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
            message_queue = [(ALERT_MSG,None)] + message_queue
            announce_timer = time.time()
            message_timer = time.time()
        char_list = new_chars + []            

        if len(message_queue) > 0 and time.time()-message_timer > message_period:
            msg_now = message_queue[-1]
            del message_queue[-1]

            S = msg_now[0]
            target = msg_now[1]

            if S[0] == ":":
                player.bot_char.pose(S[1:])
            if S[0] != ":" and target == None:
                player.bot_char.say(S)
            if S[0] != ":" and target != None:
                player.bot_char.address(S,target)

            message_timer = time.time()
            message_period = message_period*(random.random()+0.5)
            lw = BASE_PERIOD*0.5
            up = BASE_PERIOD*2.0
            message_period = message_period*(message_period>lw)*(message_period<up) + lw*(message_period<=lw)+ up*(message_period>=up)

        adr = player.bot_char.addr_hist
        mg = player.bot_char.msg_hist

        if len(adr) > 0:
            sender_a = adr[-1]['data']['char']
            cont_a = adr[-1]['data']['msg']
            del player.bot_char.addr_hist[-1]

            drinks = find_drinks(cont_a,menu)
            print("DRINKS: ",drinks)
            message_timer = time.time()

            junk_fn =  lambda x: x in [" ",",",".","!","?",";",":","-"]
            seqm = SequenceMatcher(junk_fn,"suggest",cont_a.lower())
            seq1 = seqm.find_longest_match(0,len("suggest"),0,len(cont_a)).size == len("suggest")

            seqm = SequenceMatcher(junk_fn,"sinder originals",cont_a.lower())
            seq2 = seqm.find_longest_match(0,len("sinder originals"),0,len(cont_a)).size == len("sinder originals")

            seqm = SequenceMatcher(junk_fn,"house wines",cont_a.lower())
            seq3 = seqm.find_longest_match(0,len("house wines"),0,len(cont_a)).size == len("house wines")

            if seq1 or seq2 or seq3:
                msg = "If I might recommend some Sinder originals! "+"\n"
                for a in SUGGESTIONS['Sinder originals']:
                    msg = msg + "  `"+a+"`\n"

                msg = msg + "or, the Chateau Louve house wines: "+"\n"
                for a in SUGGESTIONS['louve wines']:
                    msg = msg + "  `"+a+"`\n"
                
                msg = msg + "I can also make you a standard, such as "

                r1 = random.randint(0,len(menu[0])-1)
                msg = msg + 'a' + 'n'*(menu[0][r1][0] in ['a','e','i','o','u']) + " "+ menu[0][r1]+", "

                r2 = random.randint(0,len(menu[1])-1)
                msg = msg + 'a' + 'n'*(list(menu[1].keys())[r2][0] in ['a','e','i','o','u']) + " "+  list(menu[1].keys())[r2]+", or "

                r3 = random.randint(0,len(menu[2])-1)
                msg = msg + 'a' + 'n'*(list(menu[2].keys())[r3][0] in ['a','e','i','o','u']) + " "+  list(menu[2].keys())[r3]
                
                message_queue = [(msg,sender_a['id'])] + message_queue
            elif drinks == [] or drinks == {}:
                msg = UNSURE[random.randint(0,len(UNSURE)-1)]
                message_queue = [(msg,sender_a['id'])] + message_queue
            else:
                message_timer = time.time()

                if sender_a['id'] in char_drink_ct:
                    char_drink_ct[sender_a['id']] = char_drink_ct[sender_a['id']] + 1
                else:
                    char_drink_ct[sender_a['id']] = 1

                if char_drink_ct[sender_a['id']] < 4:
                    rep_msg = RESPONSES[random.randint(0,len(RESPONSES)-1)]
                    message_queue = [(rep_msg,None)] + message_queue

                    drinks = scramble_list(drinks)

                    for dr in drinks:
                        if dr[0] in SINDER_ORIGINALS:
                            for instr in SINDER_ORIGINALS[dr[0]]:
                                message_queue = [(instr,None)] + message_queue
                        else:
                            msg = make_drink(dr,menu)
                            message_queue = [(msg[0],None)] + message_queue

                    if len(drinks) == 1:
                        del_msg = DELIVERY_SINGULAR[random.randint(0,len(DELIVERY_SINGULAR)-1)]
                    else:
                        del_msg = DELIVERY_PLURAL[random.randint(0,len(DELIVERY_PLURAL)-1)]
                    message_queue = [(del_msg,sender_a['id'])] + message_queue
                elif char_drink_ct[sender_a['id']] == 6:
                    message_queue = [("You've had too much, you're cut off",sender_a['id'])] + message_queue
                else:
                    pass
        else:
            pass

        if len(mg) > 0:
            sender_m = mg[-1]['data']['char']
            cont_m = mg[-1]['data']['msg']
            del player.bot_char.msg_hist[-1]

            if sender_m['id'] == commander:
                if cont_m=="stop":
                    player.subprocess_flags['bartending'] = False
                    player.bot_char.say("No longer serving drinks, thank you for your patronage")
                else:
                    player.bot_char.message("Currently in bartending mode",commander)
            else:
                player.bot_char.message("Sorry, I am currently in bartending mode, please order with @",sender_m)
        else:
            pass
