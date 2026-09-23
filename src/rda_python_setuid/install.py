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
#   # 0. Display this user guide:
#   pywrapper-install
#
#   # 1. Compile and install pywrapper (run once per environment):
#   pywrapper-install -c [-n gdexdata] [-e $ENVHOME]
#
#   # 2. Create pgstart_USER entry so USER can run commands as themselves:
#   pywrapper-install -p [-n zji] [-e $ENVHOME]
#
#   # 3. Create a symlink so a program runs as CommonUser via pywrapper (setuid):
#   pywrapper-install -l myprog [-n gdexdata] [-e $ENVHOME]
#
#   # 3b. Auto-link all discovered setuid_* entries that are not yet linked:
#   pywrapper-install -l all [-e $ENVHOME]
#
#   # 4. Simple install: symlink PROGRAM -> setuid_PROGRAM (no setuid, runs as current user):
#   pywrapper-install -l myprog -s [-e $ENVHOME]
#
#   # 5. Update existing installation (recompile and reinstall all setuid binaries):
#   pywrapper-install -u [-n gdexdata] [-e $ENVHOME]
#
#   # 6. Compile a dedicated 4755 cmwrapper binary, so users outside the CommonUser
#   #    group can run one fixed program as CommonUser:
#   pywrapper-install -m myprog [-t SCRIPT] [-d DESTDIR] [-n gdexdata] [-e $ENVHOME]
#
#   # 6b. Compile it 755 with no setuid, to publish a program of this environment to
#   #     users who do not have the environment at all:
#   pywrapper-install -m myprog -s [-t SCRIPT] [-d DESTDIR] [-e $ENVHOME]
#
# Convention for wrapped programs:
#   The target package must register its connector entry point with a setuid_ prefix:
#      [project.scripts]
#      "setuid_dsarch" = "rda_python_dsarch.dsarch:main"
#   pip install places setuid_dsarch in the bin dir automatically.
#   pywrapper-install --link dsarch creates the symlink dsarch -> pywrapper, so
#   users invoking dsarch go through the setuid wrapper which execs setuid_dsarch
#   as CommonUser.
#   pywrapper-install --link dsarch --simple creates dsarch -> setuid_dsarch directly,
#   skipping setuid; the program runs as the current user.
#
##################################################################################

import argparse
import os
import re
import shutil
import subprocess
import sys


def get_bindir():
   """Return the bin directory of the active Python environment."""
   return os.path.dirname(os.path.abspath(sys.executable))


def get_c_source(name='pywrapper.c'):
   """Return path to a C source file bundled with this package."""
   return os.path.join(os.path.dirname(__file__), name)


def run(cmd):
   print("  $", " ".join(cmd))
   subprocess.run(cmd, check=True)


def show_usage():
   usgfile = os.path.join(os.path.dirname(__file__), 'install.usg')
   os.system("more " + usgfile)
   sys.exit(0)


def main():

   parser = argparse.ArgumentParser(
      description="Compile and install the pywrapper setuid C binary."
   )
   parser.add_argument(
      '-e', '--envhome', default=None,
      help="Path to the venv root directory containing bin/ (default: parent of the current Python executable's bin/ dir)"
   )
   parser.add_argument(
      '-n', '--username', default=None,
      help="User name to own the setuid binary (default: current login user for -p/--pgstart, gdexdata otherwise)"
   )
   parser.add_argument(
      '-s', '--simple', action='store_true',
      help="Simple install, skipping setuid: symlink PROGRAM -> setuid_PROGRAM with -l/--link, or a 755 cmwrapper binary with -m/--cmlink"
   )
   group = parser.add_mutually_exclusive_group()
   group.add_argument(
      '-c', '--compile', action='store_true',
      help="Compile pywrapper.c and install bin/pywrapper as a setuid binary (run once per environment)"
   )
   group.add_argument(
      '-p', '--pgstart', action='store_true',
      help="Create pgstart_USER for running commands as USER (Mode 2)"
   )
   group.add_argument(
      '-l', '--link', metavar='PROGRAM',
      help="Create symlink PROGRAM -> pywrapper for running a fixed program as CommonUser (Mode 1); use 'all' to auto-link every setuid_* entry not yet linked"
   )
   group.add_argument(
      '-m', '--cmlink', metavar='PROGRAM',
      help="Compile a dedicated 4755 cmwrapper binary for PROGRAM, so users outside the CommonUser group can run it (Mode 3); add -s/--simple for a 755 binary with no setuid"
   )
   group.add_argument(
      '-u', '--update', action='store_true',
      help="Update an existing installation: recompile pywrapper and reinstall all pgstart_USER setuid binaries"
   )
   parser.add_argument(
      '-t', '--target', default=None,
      help="Absolute path of the python script a cmwrapper binary execs (default: BINDIR/setuid_PROGRAM, or BINDIR/PROGRAM with -s/--simple; use with -m/--cmlink)"
   )
   parser.add_argument(
      '-d', '--destdir', default=None,
      help="Directory to install a cmwrapper binary into, such as a common area on everyone's PATH (default: BINDIR; use with -m/--cmlink)"
   )
   args = parser.parse_args()

   if not (args.compile or args.pgstart or args.link or args.cmlink or args.update):
      show_usage()

   if args.username is None and not args.simple:
      import pwd
      if args.pgstart:
         args.username = pwd.getpwuid(os.getuid()).pw_name
      else:
         args.username = 'gdexdata'

   bindir = os.path.join(args.envhome, 'bin') if args.envhome else get_bindir()
   pywrapper = os.path.join(bindir, 'pywrapper')

   if args.link:
      # For appname -> pywrapper links, run `ln -s` via pgstart_<commonuser> so
      # the resulting symlink is owned by the common user (pywrapper owner).
      pgstart_common = None
      if not args.simple and os.path.exists(pywrapper):
         import pwd
         common_user = pwd.getpwuid(os.stat(pywrapper).st_uid).pw_name
         pgstart_common = os.path.join(bindir, 'pgstart_' + common_user)
         if not os.path.exists(pgstart_common):
            print("Error: {} not found. Run pywrapper-install --pgstart --username {} first.".format(pgstart_common, common_user))
            sys.exit(1)

      if args.link.lower() == 'all':
         # Discover all setuid_* entries in bindir and link any that are missing
         appnames = sorted(
            f[len('setuid_'):] for f in os.listdir(bindir) if f.startswith('setuid_')
         )
         if not appnames:
            print("No setuid_* entries found in {}".format(bindir))
         for appname in appnames:
            target = os.path.join(bindir, appname)
            script = os.path.join(bindir, 'setuid_' + appname)
            if args.simple:
               if os.path.lexists(target):
                  print("Already exists: {}".format(target))
               else:
                  os.symlink(script, target)
                  print("Created: {} -> setuid_{}".format(target, appname))
            else:
               if os.path.lexists(target):
                  print("Already exists: {}".format(target))
               else:
                  run([pgstart_common, 'ln', '-s', pywrapper, target])
                  print("Created: {} -> pywrapper".format(target))
      else:
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
            # Mode 1: symlink PROGRAM -> pywrapper. setuid_PROGRAM is left with its
            # default ownership/permissions so it can be loaded and executed normally.
            if os.path.lexists(target):
               print("Already exists: {}".format(target))
            else:
               run([pgstart_common, 'ln', '-s', pywrapper, target])
               print("Created: {} -> pywrapper".format(target))

   elif args.pgstart:
      # Mode 2: create pgstart_USER with setuid owned by USER.
      # When USER already owns pywrapper (i.e. the common user), pywrapper is
      # already setuid owned by USER, so a symlink is sufficient; otherwise
      # copy pywrapper and chmod 4750 as USER.
      if not os.path.exists(pywrapper):
         print("Error: {} not found. Run pywrapper-install --compile --username COMMONUSER first.".format(pywrapper))
         sys.exit(1)
      target = os.path.join(bindir, 'pgstart_{}'.format(args.username))
      import pwd
      pywrapper_owner = pwd.getpwuid(os.stat(pywrapper).st_uid).pw_name
      if args.username == pywrapper_owner:
         if os.path.lexists(target):
            os.remove(target)
         os.symlink(pywrapper, target)
         print("Linked: {} -> pywrapper (setuid, owned by {})".format(target, args.username))
      else:
         curuser = pwd.getpwuid(os.getuid()).pw_name
         sudo_prefix = [] if curuser == args.username else ['sudo', '-u', args.username]
         run(sudo_prefix + ['cp', pywrapper, target])
         run(sudo_prefix + ['chmod', '4750', target])
         print("Installed: {} (setuid, owned by {})".format(target, args.username))

   elif args.compile:
      # Compile pywrapper.c and install pywrapper with setuid
      src = get_c_source()
      src_dest = os.path.join(bindir, 'pywrapper.c')
      shutil.copy(src, src_dest)
      print("Copied: {}".format(src_dest))
      run(['sudo', '-u', args.username, 'gcc', '-o', pywrapper, src_dest])
      run(['sudo', '-u', args.username, 'chmod', '4750', pywrapper])
      print("Installed: {} (setuid, owned by {})".format(pywrapper, args.username))

   elif args.cmlink:
      # Mode 3: compile a dedicated cmwrapper binary for one program and install it
      # 4755, so users outside the CommonUser group can run it.  The program path is
      # baked in at compile time and the environment is sanitized by cmwrapper.c, so
      # no symlink under another name can reach a different program.
      # With -s/--simple the binary is 755 with no setuid, which publishes a program
      # of this environment to users who do not have the environment at all.
      if not re.match(r'^\w+$', args.cmlink):
         print("Error: invalid program name '{}', expecting word characters only.".format(args.cmlink))
         sys.exit(1)
      if args.target:
         script = args.target
      else:
         script = os.path.join(bindir, args.cmlink if args.simple else 'setuid_' + args.cmlink)
      if not (os.path.isabs(script) and re.match(r'^[\w/.-]+$', script)):
         print("Error: {} of -t/--target must be an absolute path of word characters, '/', '.' and '-'.".format(script))
         sys.exit(1)
      if not os.path.exists(script):
         print("Error: {} not found. Install the package that provides it first.".format(script))
         sys.exit(1)
      destdir = args.destdir if args.destdir else bindir
      target = os.path.join(destdir, args.cmlink)
      if os.path.abspath(target) == os.path.abspath(script):
         print("Error: the binary {} would overwrite the script it execs; give -d/--destdir or -t/--target.".format(target))
         sys.exit(1)
      src = get_c_source('cmwrapper.c')
      src_dest = os.path.join(bindir, 'cmwrapper.c')
      shutil.copy(src, src_dest)
      print("Copied: {}".format(src_dest))
      cmd = ['gcc', '-DCMPROG="{}"'.format(args.cmlink), '-DCMEXEC="{}"'.format(script)]
      if args.simple: cmd.append('-DCMSIMPLE')
      prefix = [] if args.simple else ['sudo', '-u', args.username]
      run(prefix + cmd + ['-o', target, src_dest])
      run(prefix + ['chmod', '755' if args.simple else '4755', target])
      if args.simple:
         print("Installed: {} (no setuid, execs {})".format(target, script))
      else:
         print("Installed: {} (setuid, owned by {}, execs {})".format(target, args.username, script))

   elif args.update:
      # Update an existing installation: recompile pywrapper and reinstall all setuid binaries
      pgstart_files = sorted(f for f in os.listdir(bindir) if f.startswith('pgstart_'))
      if not pgstart_files:
         print("Error: No pgstart_* binaries found in {}".format(bindir))
         sys.exit(1)
      if not os.path.exists(pywrapper):
         print("Error: {} not found.".format(pywrapper))
         sys.exit(1)

      gdexuser = args.username
      pgstart_gdexdata = os.path.join(bindir, 'pgstart_' + gdexuser)
      if not os.path.exists(pgstart_gdexdata):
         print("Error: {} not found.".format(pgstart_gdexdata))
         sys.exit(1)

      update_tmp = os.path.join(bindir, 'update_tmp')
      os.makedirs(update_tmp, exist_ok=True)
      print("Created: {}".format(update_tmp))

      # Symlink pgstart.py into update_tmp so pywrapper instances running from
      # update_tmp can find it via the fpath/pgstart.py fallback lookup.
      bindir_pgstart_py = os.path.join(bindir, 'pgstart.py')
      update_pgstart_py = os.path.join(update_tmp, 'pgstart.py')
      if not os.path.lexists(update_pgstart_py):
         os.symlink(bindir_pgstart_py, update_pgstart_py)
         print("Linked: {} -> {}".format(update_pgstart_py, bindir_pgstart_py))

      # Copy each non-gdex pgstart_USERNAME into update_tmp using itself, then chmod 4750
      for fname in pgstart_files:
         username = fname[len('pgstart_'):]
         if username == gdexuser:
            continue
         src_pgstart = os.path.join(bindir, fname)
         dst_pgstart = os.path.join(update_tmp, fname)
         run([src_pgstart, 'cp', src_pgstart, update_tmp + '/'])
         run([src_pgstart, 'chmod', '4750', dst_pgstart])

      # Copy pywrapper into update_tmp as gdexdata, chmod, then hardlink as pgstart_gdexdata
      update_pywrapper = os.path.join(update_tmp, 'pywrapper')
      update_pgstart_gdexdata = os.path.join(update_tmp, 'pgstart_' + gdexuser)
      run([pgstart_gdexdata, 'cp', pywrapper, update_tmp + '/'])
      run([pgstart_gdexdata, 'chmod', '4750', update_pywrapper])
      run([pgstart_gdexdata, 'ln', update_pywrapper, update_pgstart_gdexdata])

      # Compile new pywrapper using update_tmp/pgstart_gdexdata
      src = get_c_source()
      src_dest = os.path.join(bindir, 'pywrapper.c')
      shutil.copy(src, src_dest)
      print("Copied: {}".format(src_dest))
      run([update_pgstart_gdexdata, 'gcc', '-o', pywrapper, src_dest])
      run([update_pgstart_gdexdata, 'chmod', '4750', pywrapper])
      print("Compiled: {} (setuid, owned by {})".format(pywrapper, gdexuser))

      # Recreate each pgstart_* in bindir using the corresponding update_tmp/pgstart_*
      for fname in sorted(f for f in os.listdir(update_tmp) if f.startswith('pgstart_')):
         username = fname[len('pgstart_'):]
         update_pgstart = os.path.join(update_tmp, fname)
         target = os.path.join(bindir, fname)
         if username == gdexuser:
            run([update_pgstart_gdexdata, 'ln', '-sf', pywrapper, target])
            print("Linked: {} -> pywrapper (setuid, owned by {})".format(target, gdexuser))
         else:
            run([update_pgstart, 'cp', pywrapper, target])
            run([update_pgstart, 'chmod', '4750', target])
            print("Updated: {} (setuid, owned by {})".format(target, username))

      # Clean up the temporary working directory
      shutil.rmtree(update_tmp)
      print("Removed: {}".format(update_tmp))


if __name__ == '__main__': main()
