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
import subprocess
from rda_python_common.pg_log import PgLOG

def main():
   """Entry point for pgstart.

   Checks whether the real user is authorized (must be the effective user or
   the GDEX common user), then executes the supplied command as the effective
   user.  Supports foreground/background execution and optional working-directory
   change via command-line options.

   Options (prefix with '-'):
      bg   -- run command in background (non-blocking)
      fg   -- run command in foreground (default, no-op flag)
      cwd  -- change to the next argument as working directory before running
      env  -- print environment variables and exit
      inc  -- print sys.path include paths and exit
      plg  -- print PGLOG variables and exit
   """
   pglog = PgLOG()
   permit = False
   pglog.PGLOG['LOGFILE'] = "pgstart.log"
   aname = PgLOG.get_command()
   bckgrd = False
   workdir = None
   argv = sys.argv[1:]

   ruid = pglog.PGLOG['RUID']
   euid = pglog.PGLOG['EUID']
   ruser = pwd.getpwuid(ruid).pw_name
   euser = pwd.getpwuid(euid).pw_name
   if ruser == euser or ruser == pglog.PGLOG['GDEXUSER']: permit = True
   pglog.set_suid(euid)

   while argv:
      ms = re.match(r'^-(\w+)$', argv[0])
      if not ms: break
      argv.pop(0)
      opt = ms.group(1)
      if opt == "bg":
         bckgrd = True
      elif opt == "cwd":
         if argv: workdir = argv.pop(0)
      elif opt != "fg":
         display_message(pglog, opt)

   if not (permit and argv):
      print("********************************************************************")
      print("* Your Login Name is {}({}) & Effective User Name is {}({}).".format(ruser, ruid, euser, euid))
      print("* Pass a command or options -(bg|fg|cwd|env|inc|plg) to run '{}'.".format(aname))
      if not permit:
         print("* You must be '{}' or '{}' to execute a command as user '{}'.".format(euser, pglog.PGLOG['GDEXUSER'], euser))
      print("********************************************************************")
      sys.exit(0)

   cmd = pglog.argv_to_string(argv)

   msg = "{}-{}{}-{}".format(pglog.PGLOG['HOSTNAME'], aname, pglog.current_datetime(), pglog.PGLOG['CURUID'])
   if workdir:
      msg += "-" + workdir
      os.chdir(workdir)

   pglog.pglog("{}: {}".format(msg, cmd), PgLOG.MSGLOG)
   if bckgrd:
      subprocess.Popen(argv)
   else:
      subprocess.run(argv)
   sys.exit(0)

def display_message(pglog, option):
   """Print diagnostic information for the given option and exit.

   Args:
      pglog (PgLOG): Initialized PgLOG instance.
      option (str): One of 'env' (environment variables), 'inc' (sys.path),
                    or 'plg' (PGLOG dict).  Prints an error for unknown values.
   """
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
      for vname in sorted(pglog.PGLOG):
         print("{}: {}".format(vname, pglog.PGLOG[vname]))
   else:
      print("* {}: Unknown option".format(option))

   sys.exit(0)

#
# call main() to start program
#
if __name__ == "__main__": main()
