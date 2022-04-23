# Simple Python example to do TextSynth completion requests
#
# The API secret key must be in the TEXTSYNTH_API_SECRET_KEY environment
# variable.
import os
import sys
import requests
from enum import Enum

import irc.bot
import irc.strings
from irc.client import ip_numstr_to_quad, ip_quad_to_numstr
from random import randrange

api_url = "https://api.textsynth.com"
# read from environment variable TEXTSYNTH_API_SECRET_KEY
api_key = os.environ["TEXTSYNTH_API_SECRET_KEY"]
# engine to use
api_engine = "gptneox_20B"

def textsynth_completion(prompt, max_tokens = 1, n = 1, stop = []):
    bias = {
            "5658": -100, # you
            "1394": -100, # You
    }
    response = requests.post(api_url + "/v1/engines/" + api_engine + "/completions", headers = { "Authorization": "Bearer " + api_key }, json = { "prompt": prompt, "max_tokens": max_tokens, 'n': n, 'stop': stop, "logit_bias": bias })
    resp = response.json()
    if "text" in resp: 
        return resp["text"]
    else:
        print("ERROR", resp)
        assert False

def yes_or_no(prompt, question, prob):
    yesToken = 4374
    noToken = 2302

    response = requests.post(
            api_url + "/v1/engines/" + api_engine + "/completions",
            headers = { "Authorization": "Bearer " + api_key },
            json = { "prompt": prompt + question, "max_tokens": 1, "logit_bias": {"2302": 50*(1-prob), "4374": 50*prob}, "top_k": 1 })
    resp = response.json()
    if "text" in resp: 
        r = resp['text']
        print(question, r)
        #if r != "Yes" and r != "No":
        #    print("yes_or_no " + resp["text"])
        return r == "Yes"
    else:
        print("ERROR", resp)
        assert False

def likely(prompt, affirmation, negation):
    responseA = requests.post(
            api_url + "/v1/engines/" + api_engine + "/logprob",
            headers = { "Authorization": "Bearer " + api_key },
            json = { "context": prompt, "continuation": affirmation })
    respA = responseA.json()
    responseN = requests.post(
            api_url + "/v1/engines/" + api_engine + "/logprob",
            headers = { "Authorization": "Bearer " + api_key },
            json = { "context": prompt, "continuation": negation })
    respN = responseN.json()
    print(affirmation, respA['logprob'], negation, respN['logprob'])
    return respA['logprob'] > respN['logprob']

def range_q(prompt, question, lower = 1, upper = 9):
    tokens = [
            17,
            18,
            374,
            495,
            577,
            608,
            721,
            818,
            721,
            818,
            854,
            898
    ]

    bias = {}
    for i in range(lower, upper+1):
        bias[str(tokens[i])] = 100

    response = requests.post(
            api_url + "/v1/engines/" + api_engine + "/completions",
            headers = { "Authorization": "Bearer " + api_key },
            json = { "prompt": prompt + question, "max_tokens": 1, "logit_bias": bias })
    resp = response.json()
    if "text" in resp: 
        r = resp['text']
        print(question, r)
        #if r != "Yes" and r != "No":
        #    print("yes_or_no " + resp["text"])
        return int(r)
    else:
        print("ERROR", resp)
        assert False


def cutSentence(s):
    #TODO: Handle quotations
    return s.split(".")[0] + "."


#print()
#print(yes_or_no(currentPrompt, "Is Arthur dead?", 0.5))
#print(yes_or_no(currentPrompt, "Is Bernard dead?", 0.5))
#print(yes_or_no(currentPrompt, "Has Arthur found loot?", 0.1))
#print(textsynth_completion(currentPrompt + "Arthur found a weapon, it is a ", max_tokens = 10, stop = ['.']))
#print(yes_or_no(currentPrompt, "Has Bernard found loot?", 0.1))
#print(textsynth_completion(currentPrompt + "What kind of loot has Bernard found?", max_tokens = 20))
#print(yes_or_no(currentPrompt, "Has Arthur lost his sword?", 0.1))
#print(yes_or_no(currentPrompt, "Has Bernard lost his hammer?", 0.1))


class State(Enum):
    WAITING = 1
    STARTED = 2
    FIGHTING = 3
    FIGHTING_ESCAPABLE = 3

class TestBot(irc.bot.SingleServerIRCBot):

    def __init__(self, channel, nickname, server, port=6667):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.channel = channel
        self.playerMapping = {}
        self.state = State.WAITING
        # Won't be changed
        self.playerNames = [
                'Arthur',
                'Galahad',
                'Percival',
                'Lancelot',
                'Gawain'
                ]

        # Can be chosen by player
        self.playerRaces = [
                'alcoholic warrior monk',
                'dwarf',
                'elf',
                'orc',
                'human'
                ]
        # Will be changed during party
        self.playerWeapons = [
                'sword',
                'hammer',
                'knife',
                'magic wand',
                'dagger'
                ]
        self.playerLives = [ 100, 100, 100, 100, 100 ]
        self.playerLucks = [ 2, 1, 0, 0, 0 ]
        assert len(self.playerLives) == len(self.playerWeapons)
        assert len(self.playerLives) == len(self.playerRaces)
        assert len(self.playerLives) == len(self.playerNames)
        assert len(self.playerLives) == len(self.playerLucks)

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        c.join(self.channel)

    def on_pubmsg(self, c, e):
        print("Got pubmsg", e)
        a = e.arguments[0].split(":", 1)
        if len(a) > 1 and irc.strings.lower(a[0]) == irc.strings.lower(self.connection.get_nickname()):
            self.do_command(e, a[1].strip())
        return

    def fight(self):
        c = self.connection

        self.prompt_and_say("A fight has begun.")
        weapon = textsynth_completion(self.prompt + f"The {self.enemy}'s preferred weapon is a ", max_tokens = 6, stop = [ ".", "?", "!" ])
        self.prompt_and_say(f"The enemy's preferred weapon is a " + weapon + ".")
        self.state = State.FIGHTING
        self.enemyWeapon = weapon

    def on_action(self, c, e):
        print("Got action", e.arguments[0], e.source)
        msg = e.arguments[0]
        nick = e.source.split("!")[0]
        print("..." + nick)
        playerId = self.playerMapping.get(nick)
        if playerId is None:
            print("Got action from non-player")
            return
        playerName = self.playerNames[playerId]

        if self.state == State.WAITING:
            return
        if self.playerLives[playerId] < 0:
            self.say("I hear dead people...")
            return

        if self.state == State.FIGHTING:
            self.prompt += f"{playerName} {msg}. "
            print(self.prompt)
            
            self.prompt_and_say(f"{playerName} fights enemy's {self.enemyWeapon} with his {self.playerWeapons[playerId]}.")

            ret = textsynth_completion(self.prompt + "Result?", max_tokens = 20, stop = [ ".", "?", "!" ])
            self.say(ret + ".")
            self.prompt += ret + ". "

            difficulty = range_q(self.prompt, "How good is {playerName}'s {self.playerWeapons[playerId]} against enemy's {self.enemyWeapon}?")
            self.say(f"Your weapon's power against the enemy's is {difficulty}")
            self.state = State.STARTED

            luck = self.playerLucks[playerId]
            dice = randrange(1, 7)
            self.say(f"Fair dice reported {dice}, your luck is {luck}.")
            if dice + luck >= difficulty:
                self.prompt_and_say(f"{playerName} killed the enemy. The fight is finished.")
                self.state = State.STARTED
            else:
                self.state = State.STARTED
                self.say(f"You lost {difficulty - (dice + luck)} HP")
                self.playerLives[playerId] -= difficulty - (dice + luck)
                self.state = State.STARTED

            return

        if self.state != State.STARTED:
            return

        self.prompt += f"{playerName} {msg}. "
        print(self.prompt)

        ret = textsynth_completion(self.prompt + "Result?", max_tokens = 20, stop = [ ".", "?", "!" ])
        self.say(ret + ".")
        self.prompt += ret + ". "

        print(self.prompt)

        ret = textsynth_completion(self.prompt + "Result?", max_tokens = 20, stop = [ ".", "?", "!" ])
        try:
            self.say(ret + ".")
            self.prompt += ret + ". "
        except:
            pass

        print(self.prompt)
        for nick in self.playerMapping:
            isPlayerDead = yes_or_no(self.prompt, f"Is {playerName} dead?", 0.5)
            isPlayerNotAlive = not yes_or_no(self.prompt, f"Is {playerName} alive?", 0.5)
            if isPlayerDead and isPlayerNotAlive:
                self.playerLives[playerId] -= 20
                self.say("Well, you died.")
                if self.playerLives[playerId] >= 0:
                    self.say(f"Your remaning life is {self.playerLives[playerId]}, you can go on.")
                    self.prompt += f"{playerName} escapes death, and become alive again."
                else:
                    self.say(f"Farewall {playerName}")

        #fightOngoing = yes_or_no(self.prompt, "Is a fight ongoing?", 0.4)
        fightOngoing = likely(self.prompt, "Fight.", "Life is good.")
        if fightOngoing:
            self.enemy = textsynth_completion(self.prompt + "The enemy is a ", max_tokens = 20, stop = [ ".", "?", "!" ])
            self.prompt_and_say("The enemy is a " + self.enemy + ".")

            fightEscapable = yes_or_no(self.prompt, "Can the fight be dodged?", 0.55)
            if fightEscapable:
                self.say("A fight has begun. Brace yourselves. You may escape it. Is it your wish?")
                self.state = State.FIGHTING_ESCAPABLE
            else:
                self.fight()



    def say(self, msg, replace = True):
        print("> " + msg)
        if replace:
            for nick in self.playerMapping:
                i = self.playerMapping[nick]
                name = self.playerNames[i]
                msg = msg.replace(name, nick)
        self.connection.privmsg(self.channel, msg.replace('\n', '').replace('\r', ''))

    def prompt_and_say(self, msg):
        self.prompt += msg
        self.say(msg)

    def do_command(self, e, cmd):
        nick = e.source.nick
        c = self.connection

        playerId = self.playerMapping.get(nick)

        if cmd == "disconnect":
            self.disconnect()
        elif cmd == "die":
            self.die()
        elif cmd == 'join' and self.state == State.WAITING:
            to = len(self.playerMapping)
            toName = self.playerNames[to]
            self.playerMapping[nick] = to
            self.say(f"{nick} joins as {toName}. He is a {self.playerRaces[to]}, starting with a {self.playerWeapons[to]}.", replace = False)
        elif cmd == 'start' and len(self.playerMapping) > 0:
            self.prompt = ""
            for nick in self.playerMapping:
                i = self.playerMapping[nick]
                self.prompt_and_say(f"{self.playerNames[i]} is a {self.playerRaces[i]} with a {self.playerWeapons[i]}.")
            self.prompt_and_say("The team start at the tavern next to the dungeon.")
            self.state = State.STARTED
        elif (cmd == "yes" or cmd == "no") and self.state == State.FIGHTING_ESCAPABLE and playerId is not None:
            if cmd == "yes":
                difficulty = range_q(self.prompt, "How hard is the fight to dodge?")
                self.say("Dodging the fight has difficulty " + str(difficulty))
                luck = self.playerLucks[playerId]
                dice = randrange(1, 7)
                self.say(f"Fair dice reported {dice}, your luck is {luck}.")
                if dice + luck >= difficulty:
                    self.state = State.STARTED
                    self.prompt_and_say("The team dodged the fight.")
                else:
                    self.say("Dodge fail, you enter in the fight.")
                    self.prompt_and_say("The team entered the fight.")
                    self.state = State.FIGHTING
                    self.fight()
            else:
                self.prompt += "The team entered the fight."
                self.fight()

bot = TestBot("#myaidungeon", "mymeugeu", "irc.oftc.net")
bot.start()
