#!/usr/bin/python
# -*- coding: utf-8 -*-
 
#=========================================================================
#              thermo.py
#-------------------------------------------------------------------------
# Original sources by JahisLove - 2014, june
# version 0.1 2014-06-16
#-------------------------------------------------------------------------
# Modifications done by Bruno Faucon - 2015, Augustus
# version 0.2 2015-08-21
#
#-------------------------------------------------------------------------
# This script read the temperatures of 3 ds18b20 probes on the 1wire
# and save the values in a MySQL database
#
#
# tested with python on Raspberry pi distribution: Raspbian GNU/Linux 7 (wheezy) 
# and Server Apache/2.2.22 (Debian) MySQL: 5.5.43
#-------------------------------------------------------------------------
#
# la base de données doit avoir cette structure:
# CREATE TABLE `PiTemp` (
#  `id` int(11) NOT NULL AUTO_INCREMENT,
#  `date` datetime NOT NULL,
#  `sonde1` decimal(3,1) NOT NULL,
#  `sonde2` decimal(3,1) NOT NULL,
#  `sonde3` decimal(3,1) NOT NULL,
#  PRIMARY KEY (`id`)
#  ) 
#ENGINE=InnoDB  DEFAULT CHARSET=latin1 AUTO_INCREMENT=28 ;
# 
#===================================================================
 
#----------------------------------------------------------#
#             package importation                          #
#----------------------------------------------------------#
import os
import time
import datetime
import MySQLdb   # MySQLdb must be installed by yourself
from threading import Timer
#import sqlite3
 
#-----------------------------------------------------------------#
#  constants : use your own values / utilisez vos propres valeurs #
#-----------------------------------------------------------------#
PATH_THERM = "/home/pi/consumption/" #path to this script
PATH_LOG = "/home/pi/consumption/log" #path to this script
DB_SERVER ='localhost'  # MySQL : IP server (localhost if mySQL is on the same machine)
DB_USER='root'     # MySQL : user
DB_PWD='Kate0130'            # MySQL : password
DB_BASE='consumption'     # MySQL : database name
 
# vous pouvez ajouter ou retirer des sondes en modifiant les 5 lignes ci dessous
# ainsi que la derniere ligne de ce script : querydb(....
counter1 = "/mnt/1wire/1D.B2D50D000000/counter.A"
counter2 = "/mnt/1wire/1D.B2D50D000000/counter.B"
counters = [counter1, counter2]
counter_value = [0, 0]
old1 = "/home/pi/consumption/oldcountA"
old2 = "/home/pi/consumption/oldcountB"
olds = [old1, old2]
old_value = [0, 0]
 
#----------------------------------------------------------#
#             Variables                                    #
#----------------------------------------------------------#

#----------------------------------------------------------#
#     definition : database query                          #
#----------------------------------------------------------#
def query_db(sql):
    db = MySQLdb.connect(DB_SERVER, DB_USER, DB_PWD, DB_BASE)
    cursor = db.cursor()
    cursor.execute(sql)
    db.commit()
    db.close() 

#----------------------------------------------------------#
#     definition : new query for sonde                     #
#----------------------------------------------------------#
def read_counter(counter):
    try:
        f = open(counter, 'r')
        lines = f.readlines()
        f.close()
        c = int(lines[0])
    except:
        print "Elec Counter not reachable please take action"
        c = '0'
    finally:
        return c

#----------------------------------------------------------#
#     definition : calculate delta between old and new     #
#                  counter                                 #
#----------------------------------------------------------#
def get_delta(counter,newvalue):
    try:
        delta = 0
        if not os.path.exists(counter):
           target = open(counter, 'w')
           target.write(str(newvalue))
           target.close()
           delta = newvalue 
        else:
           target = open(counter, 'r')
           lines = target.readlines()
           oldvalue = int(lines[0])
           target.close()
           target = open(counter, 'w+')
           target.write(str(newvalue))
           target.close()
           delta = newvalue - oldvalue 
    except:
        print "issue with delta calculation"
        return '0'
    finally:
        return delta



#----------------------------------------------------------#
#             code principal                               #
#----------------------------------------------------------#
 
# initialize Raspberry GPIO and DS18B20
#os.system('sudo /sbin/modprobe w1-gpio')
#os.system('sudo /sbin/modprobe w1-therm')
#time.sleep(2)

d1 = datetime.datetime.now()
d2 = d1.replace(minute=5*(d1.minute // 5))
startHP = d2.replace(hour=07, minute=02, second=0, microsecond=0)
startHC = d2.replace(hour=22, minute=02, second=0, microsecond=0)
datebuff = d2.strftime('%Y-%m-%d %H:%M:00') #formating date for mySQL
 
for (i, counter) in enumerate(counters):
    newvalue = read_counter(counter)
#    print newvalue
#    print olds[i]
    delta = get_delta(olds[i],newvalue)
    counters[i] = delta
#ecriture dans la base
if (d2.weekday() >= 5) or (d2 < startHP) or (d2 > startHC):
#    print ('HC')
    sql="INSERT INTO PiElec (date, HC1, HP1, HC2, HP2) VALUES ('" + datebuff + "','" + str(counters[0]) + "','0','"+ str(counters[1]) + "','0')"
else:
#    print ('HP')
    sql="INSERT INTO PiElec (date, HP1, HC1, HP2, HC2) VALUES ('" + datebuff + "','" + str(counters[0]) + "','0','"+ str(counters[1]) + "','0')"
#print (sql)
query_db(sql) # on INSERT dans la base

