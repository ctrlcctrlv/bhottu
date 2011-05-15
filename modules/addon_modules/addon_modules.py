# -*- coding: UTF-8 -*-
# ===========================================================================
#
#      File Name: addon_modules.py
#
#  Creation Date:
#  Last Modified: Sat 05 Feb 2011 05:44:39 PM CET
#
#
#         Author: gentoomen
#
#    Description:
""" Addon modules for bhottu
"""
# ===========================================================================
# Copyright (c) gentoomen

from config import *
from utils import *

import subprocess
import os
import re
import random
import time
import datetime
import urllib2
import sqlite3
import feedparser
import subprocess
#### VARIABLES ####

be_quiet = None
#repo_time = None
poll_timestamp = None
poll_timer = 0

#### DATABASE INITS ####
def bhottu_init():
    ##Poll
    dbExecute('''create table if not exists polls (
              pollID int auto_increment primary key,
              title varchar(255),
              status text,
              voters text )''')
    dbExecute('''create table if not exists items (
              itemID int auto_increment primary key,
              pollID int,
              item_index int,
              item varchar(255),
              votes int,
              index(pollID) )''')

    ## Colors
    ##Jargon
    # The jargon database structure is missing at the moment, because I do not have it at hand.

#### ADDONS ####

def AutoUpdate(parsed):
    if parsed['event'] == 'PRIVMSG':
        combostring = NICK + ", it's your birthday"
        if parsed['event_msg'].startswith(combostring):
            if authUser(parsed['event_nick']) == True:
                retcode = subprocess.call(["git", "pull", "origin", \
                        "master"])
                return_list = []
                if retcode == 0:
                    return_list.append(sendMsg(None, "YAY, brb cake!!"))
                    return_list.append('QUIT :mmmmm chocolate cake\n\r')
                    subprocess.Popen('./bhottu.py', shell=True)
                else:
                    return_list.append(sendMsg(None, "Hmph, no cake!!"))
                return return_list


def Poll(parsed):
    global poll_timestamp
    global poll_timer
    if parsed['event'] == 'PRIVMSG':
        #our combostrings/triggers
        trigger_open = NICK + ', open poll'
        trigger_close = NICK + ', close poll'
        trigger_vote = NICK + ', vote'
        trigger_search = NICK + ', search poll'
        trigger_show = NICK + ', show poll'
        trigger_delete = NICK + ', delete poll'
        trigger_timer = NICK + ', poll timer'

        message = parsed['event_msg']
        nick = parsed['event_nick']

        if message.startswith(trigger_open):
            if authUser(nick) == True:
                result = dbQuery("SELECT * FROM polls WHERE status='OPEN'")
                if len(result) > 0:
                    return sendMsg(None, 'Yeah why not start by voting on the already OPEN one..')
                else:
                    title = message.replace(trigger_open, '').lstrip()
                    if len(title) < 1:
                        return sendMsg(None, "What about actually asking something, numbnuts?")
                    dbExecute("INSERT INTO polls (title, status) VALUES (%s, %s)", [title, 'OPEN'])
                    log('Poll(): New poll opened'+ title)
                    return sendMsg(None, "Poll started! %s" % (title))

        elif message.startswith(trigger_close):
            if authUser(nick) == True:
                poll = dbQuery("SELECT pollID, title, status, voters FROM polls WHERE status='OPEN'")
                if len(poll) < 1:
                    return sendMsg(None, "Fun fact: You need to have an already open poll to close it!")
                else:
                    pollID = int(poll[0][0])
                    winner = dbQuery("SELECT itemID, pollID, item FROM items WHERE pollID=%s ORDER BY votes DESC", [pollID])
                    #for debugging
                    print winner
                    dbExecute("UPDATE polls SET status='CLOSED' WHERE pollID=%s", [pollID])
                    log('Poll(): Open poll closed')
                    poll_timer = 0
                    return_list = []
                    return_list.append(sendMsg(None, "Pool's closed."))
                    if len(winner) > 0:
                        return_list.append(sendMsg(None, "Aaaand the winner is... "+winner[0][2]))
                    return sendMsg(None, "Pool's closed.")

        elif message.startswith(trigger_vote):
            args = message.replace(trigger_vote, '')
            poll = dbQuery("SELECT pollID, title, status, voters FROM polls WHERE status='OPEN'")
            if len(poll) < 1:
                return sendMsg(None, "There's no poll open. Maybe you're seeing things?")
            if len(args) < 1: #this checks are there any arguments after stripping the trigger
                pollID = int(poll[0][0])
                title = poll[0][1]
                items = dbQuery("SELECT item_index, item, votes FROM items WHERE pollID=%s ORDER BY item_index", [pollID])
                log('Poll(): Listing open poll and items')
                return_list = [] # initializing a list to hold our return messages
                return_list.append(sendMsg(None, title))
                for item in items:
                    return_list.append(sendMsg(None, str(item[0]) + '. ' + str(item[1]) + ' (' + str(item[2]) + ')'))
                return_list.append(sendMsg(None, '0. <item>, Add a new poll item'))
                return return_list
            elif len(args) > 0:
                args = args.lstrip()
                args = args.split(' ', 1)
                try:
                    args[0] = int(args[0])
                except:
                    return sendMsg(None, "Those are some fine letters, pal. I've got some numbers, want to make a trade?")
                if args[0] == 0:
                    if len(args) > 1: #doing a len on list will return the number of elements in the list
                        item_title = args[1]
                        poll = dbQuery("SELECT pollID, title, status, voters FROM polls WHERE status='OPEN'")[0]
                        pollID = int(poll[0])
                        voters = poll[3]
                        if voters is not None:
                            voters = voters.split()
                            for item in voters:
                                if nick == item: return sendMsg(nick, 'you have voted already')
                            voters.append(nick)
                            voters = ' '.join(voters)
                        else:
                            voters = nick
                        nr_items = len(dbQuery("SELECT * FROM items WHERE pollID=%s", [pollID]))
                        dbExecute("INSERT INTO items (pollID, item_index, item, votes) VALUES (%s, %s, %s, %s)", \
                            [pollID, nr_items+1, item_title, 1])
                        dbExecute("UPDATE polls SET voters=%s WHERE pollID=%s", [voters, pollID])
                        log('Poll(): Adding new item to open poll '+item_title)
                        return sendMsg(None, "Vote added.")
                    else:
                        return sendMsg(None, "define the new item you camelhump")
                else:
                    poll = dbQuery("SELECT pollID, title, status, voters FROM polls WHERE status='OPEN'")[0]
                    pollID = int(poll[0])
                    voters = poll[3]
                    if voters is not None:
                        voters = voters.split()
                        for item in voters:
                            if nick == item:
                                log('Poll(): Dupe vote on open poll by'+nick)
                                return sendMsg(nick, 'you have voted already')
                        voters.append(nick)
                        voters = ' '.join(voters)
                    else:
                        voters = nick
                    item = dbQuery('SELECT itemID, votes FROM items WHERE pollID=%s AND item_index=%s', [pollID, args[0]])[0]
                    nr_votes = int(item[1])
                    dbExecute("UPDATE items SET votes=%s WHERE itemID=%s", [nr_votes+1, int(item[0])])
                    dbExecute("UPDATE polls SET voters=%s WHERE pollID=%s", [voters, pollID])
                    log('Poll(): '+nick+' voted on poll')
                    return sendMsg(None, "Vote casted!!")
                    #except:
                    #    return sendMsg(None, "you broke the poll goddam!!!")
            else:
                return sendMsg(None, "you broke the poll goddam!!!")
        elif message.startswith(trigger_search):
            #if authUser(nick) == True:
            args = message.replace(trigger_search, '').lstrip()
            derp = dbQuery("SELECT pollID, title, status, voters FROM polls WHERE title LIKE %s", ['%' + args + '%'])
            log('Poll(): searching poll titles from db')
            #for debugging
            print derp
            if len(derp) > 3:
                return sendMsg(None, str(len(derp)) + \
                        ' entries found, refine your search')
            else:
                return_list = []
                for idk in derp:
                    return_list.append(sendMsg(None, str(idk[0]) + ' ' + idk[1]))
                return return_list
        elif message.startswith(trigger_show):
            #if authUser(nick) == True:
            args = message.replace(trigger_show, '').lstrip()
            try:
                int(args)
            except:
                return sendMsg(None, 'you need to give me a index nr. of the poll')
            title = dbQuery("SELECT title FROM polls WHERE pollID=%s", [args])
            items = dbQuery("SELECT item_index, item, votes FROM items WHERE pollID=%s ORDER BY votes DESC", [args])
            if len(title) == 0:
                return sendMsg(None, 'Poll %s not found.' % args)
            nr_votes = 0
            return_list = []
            for item in items:
                nr_votes += int(item[2])
            return_list.append(sendMsg(None, title[0][0]+' ('+str(nr_votes)+')'))
            for item in items:
                    return_list.append(sendMsg(None, str(item[0]) + '. ' + str(item[1]) + ' (' + str(item[2]) + ')'))
            return return_list
        elif message.startswith(trigger_delete):
            if authUser(nick) == True:
                args = message.replace(trigger_delete, '').lstrip()
                try:
                    int(args)
                except:
                    return sendMsg(None, 'argument needs to be an integer')
                dbExecute("DELETE FROM polls WHERE pollID=%s", [args])
                dbExecute("DELETE FROM items WHERE pollID=%s", [args])
                log('Poll(): deleted poll ID: '+args)
                return sendMsg(None, 'deleted poll ID: '+args)
        elif message.startswith(trigger_timer):
            if authUser(nick) == True:
                result = dbQuery("SELECT * FROM polls WHERE status='OPEN'")
                if len(result) < 1:
                    return sendMsg(None, 'you can only set a timer for a OPEN poll')
                else:
                    poll_timer = message.replace(trigger_timer, '').lstrip()
                    try:
                        int(poll_timer)
                    except:
                        return sendMsg(None, 'interval needs to be an integer and in hours')
                    poll_timestamp = datetime.datetime.now()
                    log('Poll(): Timer set on open poll: '+poll_timer+' hours')
                    return sendMsg(None, 'Poll timer started and set to: '+poll_timer+' minutes')
        else:
            return None
    if int(poll_timer) > 0:
        if datetime.datetime.now() - poll_timestamp > datetime.timedelta(minutes=int(poll_timer)):
            pollID = int(dbQuery("SELECT pollID FROM polls WHERE status='OPEN'")[0][0])
            winner = dbQuery("SELECT item FROM items WHERE ident=%s ORDER BY votes DESC", [pollID])
            #for debugging
            print winner
            dbExecute("UPDATE polls SET status='CLOSED' WHERE pollID=%s", [pollID])
            log('Poll(): Timer closed open poll')
            poll_timer = 0
            return_list = []
            return_list.append(sendMsg(None, "Pool's closed."))
            if len(winner) > 0:
                return_list.append(sendMsg(None, "Aaaand the winner is... "+winner[0][0]))
            return return_list

def Statistics(parsed):
    #funcs
    def top10Ever(parsed):
        reply = dbQuery("SELECT DISTINCT name FROM `lines`")
        top10 = []
        for line in reply:
            count = dbQuery("SELECT COUNT(*) FROM `lines` WHERE name=%s",\
                               [line[0]])
            top10.append([line,count])
        listhing = sorted(top10, key=lambda listed: listed[1], reverse=True)
        count = 0
        top10reply = ''
        while count != 10:
            top10reply = top10reply + str(count+1)+". "+\
                        str(listhing[count][0][0])+" ["+str(listhing[count][1][0][0])+"] "
            count+=1
        log('Statistics(): top 10 chatters')
        return top10reply

    def Mpm():
        diffdate = datetime.datetime.now() - datetime.datetime(2010, 12, 17, 00, 24, 42)
        reply = dbQuery("SELECT COUNT(*) FROM `lines`")
        mpm = (( diffdate.days * 24 * 60 ) + ( diffdate.seconds / 60 )) / float(reply[0][0])
        log('Statistics(): messages per minute '+str(mpm))
        return mpm

    def lineAvg(parsed):
        message = parsed['event_msg']
        nick = message.split(NICK+", line average of")[1].lstrip().rstrip()
        L = dbQuery("SELECT message FROM `lines` WHERE name=%s",\
                        [nick])[0::]
        if len(L) < 1: return "division by zero"
        total_len = 0
        for s in L:
            total_len += len(s[0])
        avg = total_len / len(L)
        return "%s's line length average is %s" % (nick, str(avg))

    #triggers
    if parsed['event'] == "PRIVMSG":
        if parsed['event_msg'] == NICK+", top10ever":
            return sendMsg(None, top10Ever(parsed))
        if parsed['event_msg'] == NICK+", mpm":
            return sendMsg(None, str(Mpm())+' messages per minute')
        if parsed['event_msg'].startswith(NICK+", line average of "):
            return sendMsg(None, lineAvg(parsed))

def Roulette(parsed):
    if parsed['event'] == 'PRIVMSG':
        if parsed['event_msg'] == 'roulette':
            if random.randrange(0, 6) == 5:
                return('KICK %s %s :%s \r\n' % (CHANNEL, parsed['event_nick'], 'CONGRATULATIONS, YOU WON THE GRAND PRIZE!'))
            else:
                return sendMsg(None, "You get to live for now.")

def Load(parsed):
    if parsed['event'] == 'PRIVMSG':
        if parsed['event_msg'] == NICK+', load average':
            load = os.popen('cat /proc/loadavg').read()
            return sendMsg(None, '%s' % (load))

def Interjection(parsed):
    if parsed['event'] == 'PRIVMSG':
        if re.search('\slinux(?!\w)', parsed['event_msg'], re.IGNORECASE):
            return sendMsg(None, "I would just like to interject for a moment, what you know as Linux is in fact, GNU/Linux or as I have taken to calling it, Unity.")


"""
def Clo(parsed):


    if parsed['event'] == 'PRIVMSG':



"""
