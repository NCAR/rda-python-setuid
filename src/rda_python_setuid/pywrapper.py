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
from rda_python_common import PgLOG

#
# main function to excecute this script
#
def main():

   PgLOG.set_suid(PgLOG.PGLOG['EUID'])
   inc = 1
   print("********************************************************************")
   argv = sys.argv[1:]
   if argv:
      if argv[0] == "-env":
         print("Environment Variables:")
         for ename in sorted(os.environ):
            print("{}: {}".format(ename, os.environ[ename]))
         inc = 0
      elif argv[0] == "-inc":
         print("Including Paths:")
         for pname in sorted(sys.path):
            print(pname)
         inc = 0
      elif argv[0] == "-plg":
         print("PGLOG variables:")
         for vname in sorted(PgLOG.PGLOG):
            print("{}: {}".format(vname, PgLOG.PGLOG[vname]))
         inc = 0
      else:
         print("* {}: Unknown option".format(argv[0]))
   else:
      ruid = PgLOG.PGLOG['RUID']
      euid = PgLOG.PGLOG['EUID']
      ruser = pwd.getpwuid(ruid).pw_name
      euser = pwd.getpwuid(euid).pw_name
      print("* Your Login Name is {}({}) & Effective User Name is {}({}).".format(ruser, ruid, euser,euid))
      print("* To wrap your python script 'yourscript.py', you install it as")
      print("* an executable under $ENVHOME/bin/ and create a link to 'pywrapper'")
      print("* under $ENVHOME/bin/ as 'ln -s pywrapper yourscript'.")
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
