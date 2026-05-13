#!/usr/bin/env python3
#
##################################################################################
#
#     Title: pywrapper
#    Author: Zaihua Ji, zji@ucar.edu
#      Date: 10/17/2020
#            2025-03-18 transferred to package rda_python_setuid from
#            https://github.com/NCAR/rda-utility-programs.git
#   Purpose: default python script for pywrapper.c program to show the instruction
#            of how to wrapper a python script under pywrapper
#
#    Github: https://github.com/NCAR/rda-python-setuid.git
#
##################################################################################

import os
import sys
import pwd
from rda_python_common.pg_log import PgLOG

def main():
   """Entry point for setuid_pywrapper (the default pywrapper.c fallback target).

   When pywrapper.c cannot find a matching setuid_<program> entry point, it
   falls back to executing this script.  Prints UID information and setup
   instructions, or dumps diagnostic information when a flag is supplied.

   Options:
      -env  -- print environment variables and exit
      -inc  -- print sys.path include paths and exit
      -plg  -- print PGLOG variables and exit
   """
   pglog = PgLOG()
   pglog.set_suid(pglog.PGLOG['EUID'])
   inc = True
   print("********************************************************************")
   argv = sys.argv[1:]
   if argv:
      if argv[0] == "-env":
         print("Environment Variables:")
         for ename in sorted(os.environ):
            print("{}: {}".format(ename, os.environ[ename]))
         inc = False
      elif argv[0] == "-inc":
         print("Including Paths:")
         for pname in sorted(sys.path):
            print(pname)
         inc = False
      elif argv[0] == "-plg":
         print("PGLOG variables:")
         for vname in sorted(pglog.PGLOG):
            print("{}: {}".format(vname, pglog.PGLOG[vname]))
         inc = False
      else:
         print("* {}: Unknown option".format(argv[0]))
   else:
      ruid = pglog.PGLOG['RUID']
      euid = pglog.PGLOG['EUID']
      ruser = pwd.getpwuid(ruid).pw_name
      euser = pwd.getpwuid(euid).pw_name
      print("* Your Login Name is {}({}) & Effective User Name is {}({}).".format(ruser, ruid, euser, euid))
      print("* To wrap a Python program 'yourscript', register its entry point")
      print("* with a setuid_ prefix in pyproject.toml:")
      print("*    [project.scripts]")
      print("*    \"setuid_yourscript\" = \"your_package.module:main\"")
      print("* Then run: pywrapper-install -l yourscript")
   if inc:
      print("* Include -env to show environment variables")
      print("* Include -inc to show included paths")
      print("* Include -plg to show PGLOG variables")

   print("********************************************************************\n")

   sys.exit(0)

#
# call main() to start program
#
if __name__ == "__main__": main()
