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
from random import randrange, shuffle

import unicodedata

api_url = "https://api.textsynth.com"
# read from environment variable TEXTSYNTH_API_SECRET_KEY
api_key = os.environ["TEXTSYNTH_API_SECRET_KEY"]
openai_api_key = os.environ["OPENAI_API_SECRET_KEY"]
# engine to use
api_engine = "boris_6B"

def textsynth_yes_or_no(prompt):
    response = requests.post(
            api_url + "/v1/engines/" + api_engine + "/completions",
            headers = { "Authorization": "Bearer " + api_key },
            json = { "prompt": prompt, "max_tokens": 2, "logit_bias": {"46": 50, "9019": 50, "15419": 50, "13": 50}, "top_k": 1 })
    resp = response.json()
    if "text" in resp: 
        r = resp['text']
        print(prompt, r)
        return r == "Oui"
    else:
        print("ERROR", resp)
        assert False

def yes_or_no(prompt):
    response = requests.post('https://api.openai.com/v1/completions',
            headers = { "Authorization": "Bearer " + openai_api_key },
            json = { "prompt": prompt, "max_tokens": 1, "logit_bias": {"8505": 100, "3919": 100}, "top_p": 1.0, "model": "text-davinci-002" })
    resp = response.json()
    print(resp)
    if "text" in resp['choices'][0]: 
        r = resp['choices'][0]['text']
        print(prompt, r)
        return r == "yes"
    else:
        print("ERROR", resp)
        assert False

class TestBot(irc.bot.SingleServerIRCBot):
    def select_word(self):
        with open("/usr/share/dict/french") as f:
            lines = f.readlines()
            shuffle(lines)
            self.word = lines[0].split("\n")[0]
        print("Chosing word '" + self.word + "'")
        self.prompt = "Le mot à trouver est " + self.word + ". Q: "
        if "'" in self.word:
            self.select_word()

    def __init__(self, channel, nickname, server, port=6667):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.channel = channel
        self.select_word()

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

    def on_action(self, c, e):
        print("Got action", e.arguments[0], e.source)
        msg = e.arguments[0]
        nick = e.source.split("!")[0]
        print("..." + nick)

    def say(self, msg, replace = True):
        print("> " + msg)
        self.connection.privmsg(self.channel, msg.replace('\n', '').replace('\r', ''))

    def do_command(self, e, cmd):
        nick = e.source.nick
        c = self.connection

        cmd = unicodedata.normalize('NFC', cmd)

        if cmd == "!disconnect":
            self.disconnect()
        elif cmd == "!die":
            self.die()
        elif cmd == "!next":
            self.say("Le mot était " + self.word + ".")
            self.select_word()
        elif not " " in cmd:
            if cmd == self.word:
                self.say("Congrats.")
                self.select_word()
            else:
                self.say("Nope.")
        else:
            if yes_or_no(self.prompt + cmd + ". R:", ):
                self.say("Oui.")
            else:
                self.say("Non.")


bot = TestBot("#semantle", "mymeugeu", "irc.oftc.net")
bot.start()
