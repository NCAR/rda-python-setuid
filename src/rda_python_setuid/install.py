#!/usr/bin/env python3
#
##################################################################################
#
#     Title: pywrapper-install
#    Author: Zaihua Ji, zji@ucar.edu
#      Date: 2025-05-11
#   Purpose: Install helper for the pywrapper setuid C binary.
#            Replaces the manual gcc/chmod/ln steps with a single command.
#
#    Github: https://github.com/NCAR/rda-python-setuid.git
#
# Usage:
#   # 1. Compile and install pywrapper (run once per environment):
#   pywrapper-install --user gdexdata [--envhome $ENVHOME/bin/]
#
#   # 2. Create pgstart_USER entry so USER can run commands as themselves:
#   pywrapper-install --pgstart --user zji [--envhome $ENVHOME/bin/]
#
#   # 3. Create a symlink so a program runs as CommonUser via pywrapper (setuid):
#   pywrapper-install --link myprog --user gdexdata [--envhome $ENVHOME/bin/]
#
#   # 4. Simple install: symlink PROGRAM -> setuid_PROGRAM (no setuid, runs as current user):
#   pywrapper-install --link myprog --simple [--envhome $ENVHOME/bin/]
#
# Convention for wrapped programs:
#   The target package must register its connector entry point with a setuid_ prefix:
#      [project.scripts]
#      "setuid_dsarch" = "rda_python_dsarch.dsarch:main"
#   pip install places setuid_dsarch in the bin dir automatically.
#   pywrapper-install --link dsarch will chown setuid_dsarch to CommonUser and
#   chmod 700, so users cannot run it directly and must go through the setuid wrapper.
#   pywrapper-install --link dsarch --simple creates dsarch -> setuid_dsarch directly,
#   skipping setuid; the program runs as the current user.
#
##################################################################################

import argparse
import os
import shutil
import subprocess
import sys


def get_bindir():
   """Return the bin directory of the active Python environment."""
   return os.path.dirname(os.path.abspath(sys.executable))


def get_c_source():
   """Return path to pywrapper.c bundled with this package."""
   return os.path.join(os.path.dirname(__file__), 'pywrapper.c')


def run(cmd):
   print("  $", " ".join(cmd))
   subprocess.run(cmd, check=True)


def show_usage():
   usgfile = os.path.join(os.path.dirname(__file__), 'install.usg')
   os.system("more " + usgfile)
   sys.exit(0)


def main():

   if len(sys.argv) == 1:
      show_usage()

   parser = argparse.ArgumentParser(
      description="Compile and install the pywrapper setuid C binary."
   )
   parser.add_argument(
      '--envhome', default=None,
      help="Path to the venv bin/ directory (default: bin/ dir of the current Python executable)"
   )
   parser.add_argument(
      '--user', default=None,
      help="User name to own the setuid binary (required unless --simple is used)"
   )
   parser.add_argument(
      '--simple', action='store_true',
      help="Simple install: create symlink PROGRAM -> setuid_PROGRAM, skipping setuid (use with --link)"
   )
   group = parser.add_mutually_exclusive_group()
   group.add_argument(
      '--pgstart', action='store_true',
      help="Create pgstart_USER for running commands as USER (Mode 2)"
   )
   group.add_argument(
      '--link', metavar='PROGRAM',
      help="Create symlink PROGRAM -> pywrapper for running a fixed program as CommonUser (Mode 1)"
   )
   args = parser.parse_args()

   if not args.simple and args.user is None:
      parser.error("--user is required unless --simple is used")

   bindir = args.envhome or get_bindir()
   pywrapper = os.path.join(bindir, 'pywrapper')

   if args.link:
      target = os.path.join(bindir, args.link)
      script = os.path.join(bindir, 'setuid_{}'.format(args.link))
      if not os.path.exists(script):
         print("Error: {} not found. Install the package that provides it first.".format(script))
         sys.exit(1)
      if args.simple:
         # Simple install: symlink PROGRAM -> setuid_PROGRAM, no setuid, runs as current user.
         if os.path.lexists(target):
            print("Already exists: {}".format(target))
         else:
            os.symlink(script, target)
            print("Created: {} -> setuid_{}".format(target, args.link))
      else:
         # Mode 1: symlink PROGRAM -> pywrapper, then lock down setuid_PROGRAM
         # so users cannot bypass the setuid wrapper by running it directly.
         if os.path.lexists(target):
            print("Already exists: {}".format(target))
         else:
            os.symlink(pywrapper, target)
            print("Created: {} -> pywrapper".format(target))
         # chown and chmod 700: only CommonUser can execute setuid_PROGRAM directly.
         # pywrapper (running as CommonUser via setuid) can still execv it, but any
         # direct invocation by other users will get "permission denied".
         run(['sudo', '-u', args.user, 'chown', args.user, script])
         run(['sudo', '-u', args.user, 'chmod', '700', script])
         print("Locked: {} (chmod 700, owned by {})".format(script, args.user))

   elif args.pgstart:
      # Mode 2: copy pywrapper to pgstart_USER with setuid owned by USER
      if not os.path.exists(pywrapper):
         print("Error: {} not found. Run pywrapper-install --user COMMONUSER first.".format(pywrapper))
         sys.exit(1)
      target = os.path.join(bindir, 'pgstart_{}'.format(args.user))
      run(['sudo', '-u', args.user, 'cp', pywrapper, target])
      run(['sudo', '-u', args.user, 'chmod', '4750', target])
      print("Installed: {} (setuid, owned by {})".format(target, args.user))

   else:
      # Default: compile pywrapper.c and install pywrapper with setuid
      src = get_c_source()
      src_dest = os.path.join(bindir, 'pywrapper.c')
      shutil.copy(src, src_dest)
      print("Copied: {}".format(src_dest))
      run(['sudo', '-u', args.user, 'gcc', '-o', pywrapper, src_dest])
      run(['sudo', '-u', args.user, 'chmod', '4750', pywrapper])
      print("Installed: {} (setuid, owned by {})".format(pywrapper, args.user))


if __name__ == '__main__': main()
