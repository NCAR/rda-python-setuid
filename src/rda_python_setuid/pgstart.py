#!/usr/bin/env python3
#
##################################################################################
#
#     Title: pgstart
#    Author: Zaihua Ji, zji@ucar.edu
#      Date: 10/17/2020
#            2025-03-18 transferred to package rda_python_setuid from
#            https://github.com/NCAR/rda-utility-programs.git
#   Purpose: python script to start up an application in background
#            for individual specialist
#
#    Github: https://github.com/NCAR/rda-python-setuid.git
#
##################################################################################

import os
import sys
import re
import pwd
from rda_python_common import PgLOG

#
# main function to excecute this script
#
def main():

   permit = 1
   PgLOG.PGLOG['LOGFILE'] = "pgstart.log"
   aname = PgLOG.get_command()
   bckgrd = ""
   workdir = None
   argv = sys.argv[1:]

   PgLOG.set_suid(PgLOG.PGLOG['EUID'])
   if PgLOG.PGLOG['CURUID'] != PgLOG.PGLOG['RDAUSER'] and PgLOG.PGLOG['CURUID'] != "zji": permit = 0

   while argv:
      ms = re.match(r'^-(\w+)$', argv[0])
      if not ms: break
      argv.pop(0)
      opt = ms.group(1)
      if opt == "bg":
         bckgrd = " &"
      elif opt == "cwd":
         if argv: workdir = argv.pop(0)
      elif opt != "fg":
         display_message(opt)

   if not (permit and argv):
      ruid = PgLOG.PGLOG['RUID']
      euid = PgLOG.PGLOG['EUID']
      ruser = pwd.getpwuid(ruid).pw_name
      euser = pwd.getpwuid(euid).pw_name
      print("********************************************************************")
      print("* Your Login Name is {}({}) & Effective User Name is {}({}).".format(ruser, ruid, euser, euid))
      print("* Pass a command or options -(plg|env|inc) to run '{}'.".format(aname))
      if not permit:
         print("* You must be '{}' to execute a command as user '{}'.".format(PgLOG.PGLOG['RDAUSER'], euser))
      print("********************************************************************")
      sys.exit(0)

   cmd = PgLOG.argv_to_string(argv)
   
   msg = "{}-{}{}-{}".format(PgLOG.PGLOG['HOSTNAME'], aname, PgLOG.current_datetime(), PgLOG.PGLOG['CURUID'])
   if workdir:
      msg += "-" + workdir
      os.chdir(workdir)

   PgLOG.pglog("{}: {}".format(msg, cmd), PgLOG.MSGLOG)
   os.system(cmd + bckgrd)
   sys.exit(0)

#
#  display message acording to the option passed in
#
def display_message(option):

   if option == "env":
      print("Environment Variables:")
      for ename in sorted(os.environ):
         print("{}: {}".format(ename, os.environ[ename]))
   elif option == "inc":
      print("Including Paths:")
      for pname in sorted(sys.path):
         print(pname)
   elif option == "plg":
      print("PGLOG variables:")
      for vname in sorted(PgLOG.PGLOG):
         print("{}: {}".format(vname, PgLOG.PGLOG[vname]))
   else:
      print("* {}: Unknown option".format(option))

   sys.exit(0)

#
# call main() to start program
#
if __name__ == "__main__": main()
