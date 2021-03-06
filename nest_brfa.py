#! /usr/bin/python

# nest.py -- a python interface to the Nest Thermostat
# by Scott M Baker, smbaker@gmail.com, http://www.smbaker.com/
#
# Usage:
#    'nest.py help' will tell you what to do and how to do it
#
# Licensing:
#    This is distributed unider the Creative Commons 3.0 Non-commecrial,
#    Attribution, Share-Alike license. You can use the code for noncommercial
#    purposes. You may NOT sell it. If you do use it, then you must make an
#    attribution to me (i.e. Include my name and thank me for the hours I spent
#    on this)
#
# Acknowledgements:
#    Chris Burris's Siri Nest Proxy was very helpful to learn the nest's
#       authentication and some bits of the protocol.
#
# Version 0.1 2015-12 Adding info for home nest, and saving values in SQL
# crontab for saving temperature in temp file to work as probe for temp.py
# 4,9,14,19,24,29,34,39,44,49,54,59 * * * * python /home/pi/pynest/nest_brfa.py --user bruno@famillefaucon.be --password Kate013. curtemp >/home/pi/pynest/temp
# crontab for saving data in sql table
# */5 * * * * python /home/pi/pynest/nest_brfa.py --user bruno@famillefaucon.be --password Kate013. save

import urllib
import urllib2
import sys
import time
import datetime
import MySQLdb
from optparse import OptionParser

#-----------------------------------------------------------------#
#  constants : use your own values / utilisez vos propres valeurs #
#-----------------------------------------------------------------#
PATH_THERM = "/home/pi/consumption/" #path to this script
PATH_LOG = "/home/pi/consumption/log" #path to this script
DB_SERVER ='localhost'  # MySQL : IP server (localhost if mySQL is on the same machine)
DB_USER='*user*'     # MySQL : user
DB_PWD='********'            # MySQL : password
DB_BASE='consumption'     # MySQL : database name

try:
   import json
except ImportError:
   try:
       import simplejson as json
   except ImportError:
       print "No json library available. I recommend installing either python-json"
       print "or simpejson."
       sys.exit(-1)

class Nest:
    def __init__(self, username, password, serial=None, index=0, units="F"):
        self.username = username
        self.password = password
        self.serial = serial
        self.units = units
        self.index = index

    def loads(self, res):
        if hasattr(json, "loads"):
            res = json.loads(res)
        else:
            res = json.read(res)
        return res

#----------------------------------------------------------# 
    def query_db(sql):
        global backup_mode
        global backup_row
        print sql
        db = MySQLdb.connect(DB_SERVER, DB_USER, DB_PWD, DB_BASE)
        cursor = db.cursor() # creation du curseur
        if backup_mode == 0:
            #cursor.execute(sql) #execution de la requete
            #db.commit()
            db.close()

    def login(self):
        data = urllib.urlencode({"username": self.username, "password": self.password})

        req = urllib2.Request("https://home.nest.com/user/login",
                              data,
                              {"user-agent":"Nest/1.1.0.10 CFNetwork/548.0.4"})

        res = urllib2.urlopen(req).read()

        res = self.loads(res)

        self.transport_url = res["urls"]["transport_url"]
        self.access_token = res["access_token"]
        self.userid = res["userid"]

    def get_status(self):
        req = urllib2.Request(self.transport_url + "/v2/mobile/user." + self.userid,
                              headers={"user-agent":"Nest/1.1.0.10 CFNetwork/548.0.4",
                                       "Authorization":"Basic " + self.access_token,
                                       "X-nl-user-id": self.userid,
                                       "X-nl-protocol-version": "1"})

        res = urllib2.urlopen(req).read()

        res = self.loads(res)

        self.structure_id = res["structure"].keys()[0]

        if (self.serial is None):
            self.device_id = res["structure"][self.structure_id]["devices"][self.index]
            self.serial = self.device_id.split(".")[1]

        self.status = res

        #print "res.keys", res.keys()
        #print "res[structure][structure_id].keys", res["structure"][self.structure_id].keys()
        #print "res[device].keys", res["device"].keys()
        #print "res[device][serial].keys", res["device"][self.serial].keys()
        #print "res[shared][serial].keys", res["shared"][self.serial].keys()

    def temp_in(self, temp):
        if (self.units == "F"):
            return (temp - 32.0) / 1.8
        else:
            return temp

    def temp_out(self, temp):
        if (self.units == "F"):
            return temp*1.8 + 32.0
        else:
            return temp

    def show_status(self):
        shared = self.status["shared"][self.serial]
        device = self.status["device"][self.serial]

        allvars = shared
        allvars.update(device)

        for k in sorted(allvars.keys()):
             print k + "."*(32-len(k)) + ":", allvars[k]

    def show_curtemp(self):
        temp = self.status["shared"][self.serial]["current_temperature"]
        #temp = self.temp_out(temp)

        print "%0.2f" % temp

    def show_curheat(self):
        temp = self.status["shared"][self.serial]["hvac_heater_state"]
        #temp = self.temp_out(temp)

        print "%0.0f" % temp

    def show_curtarget(self):
        temp = self.status["shared"][self.serial]["target_temperature"]
        #temp = self.temp_out(temp)

        print "%0.1f" % temp

    def save_conso(self):
         targettemp = self.status["shared"][self.serial]["target_temperature"]
         heater = self.status["shared"][self.serial]["hvac_heater_state"]        
         curtemp = self.status["shared"][self.serial]["current_temperature"]
         curhumid = self.status["device"][self.serial]["current_humidity"]
#self.status["shared"][self.serial]["current_humidity"]        

#         print "%0.1f" % curtemp 
#         print "%0.1f" % curhumid
#         print "%0.1f" % targettemp 
#         print "%s" % heater  

         d1 = datetime.datetime.now()
         d2 = d1.replace(minute=5*(d1.minute // 5))
         datebuff = d2.strftime('%Y-%m-%d %H:%M:00') #formating date for mySQL
         
         sql = """INSERT INTO PiNest (date, temp, humid, target, heat) VALUES ('%s','%0.2f','%0.2f','%0.2f', '%0.2f')
         """ % (datebuff, curtemp, curhumid, targettemp, heater)
#         print sql

         db = MySQLdb.connect(DB_SERVER, DB_USER, DB_PWD, DB_BASE)
         cursor = db.cursor() # creation du curseur
         cursor.execute(sql) #execution de la requete
         db.commit()
         db.close() 

    def set_temperature(self, temp):
        temp = self.temp_in(temp)

        data = '{"target_change_pending":true,"target_temperature":' + '%0.1f' % temp + '}'
        req = urllib2.Request(self.transport_url + "/v2/put/shared." + self.serial,
                              data,
                              {"user-agent":"Nest/1.1.0.10 CFNetwork/548.0.4",
                               "Authorization":"Basic " + self.access_token,
                               "X-nl-protocol-version": "1"})

        res = urllib2.urlopen(req).read()

        print res

    def set_fan(self, state):
        data = '{"fan_mode":"' + str(state) + '"}'
        req = urllib2.Request(self.transport_url + "/v2/put/device." + self.serial,
                              data,
                              {"user-agent":"Nest/1.1.0.10 CFNetwork/548.0.4",
                               "Authorization":"Basic " + self.access_token,
                               "X-nl-protocol-version": "1"})

        res = urllib2.urlopen(req).read()

        print res

def create_parser():
   parser = OptionParser(usage="nest [options] command [command_options] [command_args]",
        description="Commands: fan temp",
        version="unknown")

   parser.add_option("-u", "--user", dest="user",
                     help="username for nest.com", metavar="USER", default=None)

   parser.add_option("-p", "--password", dest="password",
                     help="password for nest.com", metavar="PASSWORD", default=None)

   parser.add_option("-c", "--celsius", dest="celsius", action="store_true", default=False,
                     help="use celsius instead of farenheit")

   parser.add_option("-s", "--serial", dest="serial", default=None,
                     help="optional, specify serial number of nest thermostat to talk to")

   parser.add_option("-i", "--index", dest="index", default=0, type="int",
                     help="optional, specify index number of nest to talk to")


   return parser

def help():
    print "syntax: nest [options] command [command_args]"
    print "options:"
    print "   --user <username>      ... username on nest.com"
    print "   --password <password>  ... password on nest.com"
    print "   --celsius              ... use celsius (the default is farenheit)"
    print "   --serial <number>      ... optional, specify serial number of nest to use"
    print "   --index <number>       ... optional, 0-based index of nest"
    print "                                (use --serial or --index, but not both)"
    print
    print "commands: temp, fan, show, curtemp, curhumid"
    print "    temp <temperature>    ... set target temperature"
    print "    fan [auto|on]         ... set fan state"
    print "    show                  ... show everything"
    print "    curtemp               ... print current temperature"
    print "    curhumid              ... print current humidity"
    print "    save                  ... save values in database"
    print
    print "examples:"
    print "    nest.py --user joe@user.com --password swordfish temp 73"
    print "    nest.py --user joe@user.com --password swordfish fan auto"
    print "    nest_brfa.py --user bruno@famillefaucon.be --password Kate013. curtemp >/home/pi/pynest/temp"
    print "    nest_brfa.py --user bruno@famillefaucon.be --password Kate013. save"

def main():
    parser = create_parser()
    (opts, args) = parser.parse_args()

    if (len(args)==0) or (args[0]=="help"):
        help()
        sys.exit(-1)

    if (not opts.user) or (not opts.password):
        #print "how about specifying a --user and --password option next time?"
        #sys.exit(-1)
        opts.user = "bruno@famillefaucon.be"
        opts.password = "Kate013."

    if opts.celsius:
        units = "C"
    else:
        units = "F"

    n = Nest(opts.user, opts.password, opts.serial, opts.index, units=units)
    n.login()
    n.get_status()

    cmd = args[0]

    if (cmd == "temp"):
        if len(args)<2:
            print "please specify a temperature"
            sys.exit(-1)
        n.set_temperature(int(args[1]))
    elif (cmd == "fan"):
        if len(args)<2:
            print "please specify a fan state of 'on' or 'auto'"
            sys.exit(-1)
        n.set_fan(args[1])
    elif (cmd == "show"):
        n.show_status()
    elif (cmd == "curtemp"):
        n.show_curtemp()
    elif (cmd == "save"):
        n.save_conso()
    elif (cmd == "curtarget"):
        n.show_curtarget()
    elif (cmd == "curhumid"):  
        print n.status["device"][n.serial]["current_humidity"]
    elif (cmd == "curheat"):
        n.show_curheat() 
    else:
        print "misunderstood command:", cmd
        print "do 'nest.py help' for help"

if __name__=="__main__":
   main()





