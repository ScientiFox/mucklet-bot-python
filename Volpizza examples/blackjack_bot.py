import websocket
import json
import threading
import math,time,random
import pickle,glob
from difflib import SequenceMatcher

from utility_bots import *

###
#Section for the blackjack bot
###

SUITS = ['Spades', 'Hearts', 'Diamonds', 'Clubs']
SUIT_IMG = {'Spades':'♠', 'Hearts':'♥', 'Diamonds':'♦', 'Clubs':'♣'}
CARDS = [str(a) for a in range(11)[2:]]+['J','Q','K','A']
DECK = []
for a in SUITS:
    for b in CARDS:
        DECK = DECK + [b+" of "+a]
VALUES = {**{str(a):a for a in range(11)[2:]},**{"J":10,"Q":10,"K":10}}

FLAVOR = ["shuffles the cards",
          "moves some chips around",
          "chews his nails",
          "fiddles under the table for a moment",
          "sneaks a sip off a hidden drink",
          "adjusts his cap",
          "opens a fresh pack of cards",
          "eats a mint",
          "looks over at the roulette croupier",
          "rolls his shoulders and stretches",
          "scratches his arm",
          "runs a quick self-check"
          ]

def shuffle(_deck):
    deck = _deck + []
    s_deck = []
    while len(deck)>0:
        r = random.randint(0,len(deck)-1)
        s_deck = s_deck + [deck[r]]
        del deck[r]
    return s_deck

def get_sum(hand):
    s = 0
    n_aces = 0
    val = 0
    for cd in hand:
        if cd.split(" ")[0] != "A":
            val = val + VALUES[cd.split(" ")[0]]
        else:
            n_aces+=1

    if n_aces == 0:
        return [val]
    else:
        vals = []
        for A in range(n_aces+1):
            vals = vals + [val + (n_aces + 10*A)] 
        return vals

class blackjack:

    def __init__(self,_player):
        self.n_decks = 2

        self.gamblers = {}
        self.deck = (DECK+[])*self.n_decks

        self.bust = False
        self.blackjack = False
        self.hole_card = None
        self.show_cards = []

        self.player = _player

        self.to_call = []
        self.in_play_ct = 0

    def deal_self(self,n):
        for i in range(n):
            if self.hole_card == None:
                self.hole_card = self.draw_card()
            else:
                self.show_cards = self.show_cards + [self.draw_card()]

    def make_show_msg(self,gameover):
        S = ""
        len_max = max([len(self.gamblers[a]['char']['name']) for a in self.gamblers]+[len("dealer")])
        for gamb in self.gamblers:
            nme = self.gamblers[gamb]['char']['name']
            S = S +"`" +nme + ":" + " "*(len_max-len(nme))+"` "

            for cd in self.gamblers[gamb]['hand']:
                pip = cd.split(" of ")[0]
                suit = SUIT_IMG[cd.split(" of ")[1]]
                S = S + pip + suit + " "

            if self.gamblers[gamb]['bust']:
                S = S + "BUST "
            elif self.gamblers[gamb]['blackjack']:
                S = S + "Blackjack! "
            S = S[:-1]+"\n"
        if not(gameover):
            S = S + "`Dealer:"+" "*(len_max-len("Dealer")) + "` XX "
        else:
            pip = self.hole_card.split(" of ")[0]
            suit = SUIT_IMG[self.hole_card.split(" of ")[1]]
            S = S + "`Dealer:"+" "*(len_max-len("Dealer")) + "` "+ pip + suit +" "
        for cd in self.show_cards:
            pip = cd.split(" of ")[0]
            suit = SUIT_IMG[cd.split(" of ")[1]]
            S = S + pip + suit + " "
        S = S[:-1]
        return S

    def add_gambler(self,char):
        if not(char['id'] in self.gamblers):
            self.gamblers[char['id']] = {'char':char,'hand':[],'bust':False,'blackjack':False}
            return 1
        else:
            return 0

    def remove_gambler(self,char):
        if char['id'] in self.gamblers:
            del self.gamblers[char['id']]
            return 1
        else:
            return 0

    def draw_card(self):
        card = self.deck[0]
        del self.deck[0]
        return card

    def shuffle_deck(self):
        for gamb in self.gamblers:
            self.gamblers[gamb]['hand'] = []
            self.gamblers[gamb]['bust'] = False
            self.gamblers[gamb]['blackjack'] = False
        self.hole_card = None
        self.show_cards = []
        self.bust = False

        self.deck = shuffle(DECK)
        return 1

    def deal(self,n,drawers):
        for i in range(n):
            for gamb in drawers:
                card = self.draw_card()
                self.gamblers[gamb]['hand'].append(card)
        return 1

    def dealer_hit(self):
        val = get_sum(self.show_cards+[self.hole_card])
        if min(val) <= 16:
            return True
        else:
            return False

    def check_winners(self):

        dealer_score = get_sum(self.show_cards + [self.hole_card])
        dealer_score = max([a*(a<=21) for a in dealer_score])
        dealer_score = dealer_score*(dealer_score<=21)

        max_score = 0
        winners = []

        for gamb in self.gamblers:
            score = get_sum(self.gamblers[gamb]['hand'])
            score = [a*(a<=21) for a in score]
            score = max(score)
            if score > max_score and score > dealer_score:
                max_score = score
                winners = [gamb]
            elif score == max_score and score > dealer_score:
                winners = winners + [gamb]

        if max_score == 0 and dealer_score == 0:
            return []
        elif max_score >= dealer_score:
            return winners
        elif dealer_score > max_score:
            return ["dealer"]

    def play_round(self):

        round_over = False

        commander = self.player.subprocess_flags['commander']

        get_players_timer = time.time()
        get_players_period = 30.0

        hit_stay_timer = None
        hit_stay_period = 25.0

        max_gamblers = 7

        CHECK,DEAL,GET_HITS,GET_PLAYERS,GAME_OVER = 0,1,2,3,4
        POST,WAIT = 0,1

        STATE = GET_PLAYERS
        subSTATE = POST

        self.player.bot_char.say("Say `@Dealer=I'm in` to join or `@Dealer=I'm out` to leave")

        announce_timer = time.time()
        announce_period = 60.0
        state,S = self.player.bot_char.getState()
        char_list = state[2]
        awake_list = []
        for a in char_list:
            if a['state'] == 'awake':
                awake_list = awake_list + [a]
        char_list = awake_list+[]

        flavor_timer = time.time()
        flavor_period = 200.0 + random.random()*(3*60)

        while not(round_over):

            people = self.player.bot_char.getPeople()
            people = [a['id'] for a in people]
            removes = []
            for gamb in self.gamblers:
                if not(self.gamblers[gamb]['char']['id'] in people):
                    removes = removes + [self.gamblers[gamb]['char']]
            for rem in removes:
                self.remove_gambler(rem)

            mg = self.player.bot_char.msg_hist
            if len(mg) > 0:
                sender_m = mg[-1]['data']['char']
                cont_m = mg[-1]['data']['msg']
                del self.player.bot_char.msg_hist[-1]

                if sender_m['id'] == commander:
                    if cont_m=="stop":
                        self.player.bot_char.say("I'm sorry- this round has been terminated.")
                        self.player.subprocess_flags['blackjack'] = False
                        self.player.subprocess_flags['playing_blackjack'] = False
                        return 1
                    else:
                        self.player.bot_char.message("Currently in blackjack mode",commander)
                        time.sleep(4.0)
                else:
                    self.player.bot_char.message("Sorry, I am currently  dealing blackjack, please order with @",sender_m)
                    time.sleep(4.0)
            else:
                pass

            if STATE == CHECK:
                self.in_play_ct = 0
                for gamb in self.gamblers:
                    val = get_sum(self.gamblers[gamb]['hand'])
                    if min(val) > 21:
                        self.gamblers[gamb]['bust'] = True
                    elif 21 in val:
                        self.gamblers[gamb]['blackjack'] = True
                    else:
                        self.in_play_ct+=1

                val = get_sum(self.show_cards + [self.hole_card])
                if min(val) > 21:
                    self.bust = True
                if 21 in val:
                    self.blackjack = True

                if self.in_play_ct == 0:
                    STATE = GAME_OVER
                else:
                    STATE = GET_HITS
                    subSTATE = POST

            elif STATE == DEAL:
                if self.hole_card == None:
                    self.deal(2,list(self.gamblers.keys()))
                    self.deal_self(2)
                    STATE = CHECK
                else:
                    self.deal(1,self.to_call)
                    if not(self.blackjack or self.bust):
                        vals = get_sum(self.show_cards + [self.hole_card])
                        diffs = [a*(21-a>=0) for a in vals]
                        if max(diffs)<17:
                            self.deal_self(1)
                        else:
                            pass
                    if len(self.to_call) == 0:
                        STATE = GAME_OVER
                    else:
                        STATE = CHECK

            elif STATE == GET_HITS:

                if subSTATE == POST:
                    S = self.make_show_msg(False)
                    self.player.bot_char.say("The Table: \n"+S)
                    time.sleep(6.0)

                    S = ""
                    for gamb in self.gamblers:
                        if not(self.gamblers[gamb]['bust'] or self.gamblers[gamb]['blackjack']):
                            S = S + self.gamblers[gamb]['char']['name'] + ", "
                    S = S[:-2] + ": hit or stay?"
                    self.player.bot_char.say(S)
                    time.sleep(4.0)

                    self.to_call = []

                    subSTATE = WAIT
                    hit_stay_timer = time.time()

                elif subSTATE == WAIT:
                    
                    adr = self.player.bot_char.addr_hist
                    if len(adr) > 0:
                        sender_a = adr[-1]['data']['char']
                        cont_a = adr[-1]['data']['msg']
                        del self.player.bot_char.addr_hist[-1]

                        if sender_a['id'] in self.gamblers:
                            if not(self.gamblers[sender_a['id']]['bust'] or self.gamblers[sender_a['id']]['blackjack']):
                                mtch = get_matches(cont_a,["hit","stay"])
                                ovp = overlap_checker(mtch)
                                ovp = [o[0] for o in ovp]

                                if ("hit" in ovp) and ("stay" in ovp):
                                    self.player.bot_char.message("I can't tell if you mean hit or stay")
                                    time.sleep(4.0)
                                elif ("stay" in ovp):
                                    self.in_play_ct-=1
                                elif ("hit" in ovp):
                                    self.to_call = self.to_call + [sender_a['id']]
                                else:
                                    pass
                            else:
                                self.player.bot_char.message("I'm sorry, you're out for the round",sender_a['id'])
                                self.in_play_ct-=1
                                time.sleep(4.0)
                        else:
                            self.player.bot_char.message("Sorry, you cannot join a round already in progress",sender_a['id'])
                            time.sleep(4.0)
                    else:
                        pass

                    if self.in_play_ct == 0:
                        STATE = GAME_OVER
                    elif len(self.to_call) == self.in_play_ct or time.time()-hit_stay_timer > hit_stay_period:
                        subSTATE = POST
                        STATE = DEAL

            elif STATE == GET_PLAYERS:

                adr = self.player.bot_char.addr_hist
                if len(adr) > 0:
                    sender_a = adr[-1]['data']['char']
                    cont_a = adr[-1]['data']['msg']
                    del self.player.bot_char.addr_hist[-1]

                    mtch_in = get_matches(cont_a,["in","play","game","go"])
                    ovp_in = overlap_checker(mtch_in)
                    ovp_in = [o[0] for o in ovp_in]

                    mtch_out = get_matches(cont_a,["out","done","leave"])
                    ovp_out = overlap_checker(mtch_out)
                    ovp_out = [o[0] for o in ovp_out]

                    if len(ovp_in) > 0:
                        ret = self.add_gambler(sender_a)
                        if ret:
                            self.player.bot_char.say(sender_a['name']+" joined the round")
                            time.sleep(4.0)
                    
                    if len(ovp_out) > 0:
                        ret = self.remove_gambler(sender_a)
                        if ret:
                            self.player.bot_char.say(sender_a['name']+" left the round")
                            time.sleep(4.0)

                if time.time()-get_players_timer > get_players_period or len(self.gamblers) > max_gamblers:
                    if len(self.gamblers) >  0:
                        self.to_call = [gamb for gamb in self.gamblers]
                        self.shuffle_deck()
                        STATE = DEAL
                    else:
                        STATE = GET_PLAYERS
                        get_players_timer = time.time()

                state,S = self.player.bot_char.getState()
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
                    self.player.bot_char.say("Say `@Dealer=I'm in` to join or `@Dealer=I'm out` to leave")
                    time.sleep(4.0)
                    announce_timer = time.time()
                    message_timer = time.time()
                char_list = new_chars + []

                if time.time()-flavor_timer > flavor_period:
                    msg_flav = FLAVOR[random.randint(0,len(FLAVOR)-1)]
                    self.player.bot_char.pose(msg_flav)
                    flavor_timer=time.time()
                    flavor_period = 120.0 + random.random()*(3*60)

            elif STATE == GAME_OVER:
                S = self.make_show_msg(True)
                self.player.bot_char.say("The Table: \n"+S)
                time.sleep(4.0)

                winners = self.check_winners()
                for win in winners:
                    if win != 'dealer':
                        if not(self.gamblers[win]['char']['id'] in self.player.subprocess_flags['gambler_scores']):
                            self.player.subprocess_flags['gambler_scores'][self.gamblers[win]['char']['id']] = (self.gamblers[win]['char']['name']+" "+self.gamblers[win]['char']['surname'],1)
                        else:
                            entry = self.player.subprocess_flags['gambler_scores'][self.gamblers[win]['char']['id']]
                            self.player.subprocess_flags['gambler_scores'][self.gamblers[win]['char']['id']] = (entry[0],entry[1]+1)
                    else:
                        pass

                if len(winners)==0:
                    S = "No winners this round."
                elif len(winners) == 1:
                    if winners[0] == "dealer":
                        S = "Dealer wins"
                    else:
                        S = "This round's winner: `"+self.gamblers[winners[0]]['char']['name']+"` "
                elif len(winners)>1:
                    S = "Winners this round: "
                    for win in winners:
                        S = S + "`"+self.gamblers[win]['char']['name']+"`, "
                    S = S[:-2]
                
                self.player.bot_char.say(S)
                self.shuffle_deck()
                time.sleep(4.0)
                return 1

def blackjack_bot(player):

    dealer = blackjack(player)
    player.subprocess_flags['blackjack'] = True
    player.subprocess_flags['playing_blackjack'] = True
    player.subprocess_flags['gambler_scores'] = {}

    #player.bot_char.say("Ready to deal blackjack! Say `@Iam=start game` to begin!")
    #time.sleep(1.0)

    notice_timer = time.time()
    notice_period = 60.0

    game_timer=time.time()
    game_period=5.0

    while (player.subprocess_flags['blackjack']):

        mg = player.bot_char.msg_hist
        if len(mg) > 0:
            sender_m = mg[-1]['data']['char']
            cont_m = mg[-1]['data']['msg']
            del player.bot_char.msg_hist[-1]

            if sender_m['id'] == player.subprocess_flags['commander']:
                if cont_m=="stop":
                    player.bot_char.say("No longer dealing blackjack")
                    time.sleep(3.0)
                    player.subprocess_flags['blackjack'] = False
                    player.subprocess_flags['playing_blackjack'] = False
                else:
                    player.bot_char.message("Currently in blackjack mode",commander)
                    notice_timer = time.time()
                    time.sleep(3.0)
            else:
                player.bot_char.message("Sorry, I am currently  dealing blackjack, please order with @",sender_m)
                notice_timer = time.time()
                time.sleep(3.0)
        else:
            pass

        if player.subprocess_flags['playing_blackjack'] and time.time()-game_timer>game_period:
            dealer.play_round()
            if not(player.subprocess_flags['playing_blackjack']):
                return 1
            time.sleep(3.0)
            player.bot_char.say("Next round begins soon...")
            notice_timer = time.time()
            game_timer=time.time()
            time.sleep(3.0)

            leaderboard = []
            for gamb in player.subprocess_flags["gambler_scores"]:
                entry = player.subprocess_flags["gambler_scores"][gamb]
                leaderboard = leaderboard + [(entry[0],entry[1])]
            leaderboard.sort(key=lambda x:x[1],reverse=True)

            if len(leaderboard)>0:
                S = "Leaderboard: \n"
                for l in leaderboard[:5]:
                    S = S + "`"+l[0]+":` "+str(l[1])+"\n"
                player.bot_char.say(S)
                time.sleep(3.0)
                notice_timer = time.time()

