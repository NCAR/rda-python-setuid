#!/usr/bin/env python3
#
##################################################################################
#
#     Title: setup_guide
#    Author: Zaihua Ji, zji@ucar.edu
#      Date: 2026-05-21
#   Purpose: Shared setuid setup guide displayed when a package's setuid_* entry
#            point is invoked directly (i.e. before pywrapper symlinks are
#            configured).  Each package's setuid entry point calls
#            show_setup_guide(pkgname, appnames) with its own metadata.
#
#    Github: https://github.com/NCAR/rda-python-setuid.git
#
##################################################################################

import os
import sys


def show_setup_guide(obj, pkgname, appnames):
   """Display the setuid setup guide if invoked directly, otherwise return.

   When a package's setuid entry point (e.g. ``setuid_dsarch``) is invoked
   directly before pywrapper symlinks are set up, ``obj.get_command()``
   returns the literal ``setuid_<appname>`` (no prefix stripping, since
   euid is the real user, not COMMONUSER).  In that case this function reads
   ``setuid_setup.usg`` bundled with rda_python_setuid, substitutes
   ``{PKGNAME}`` and ``{APPNAMES}``, prints the guide, and exits.

   When invoked via the pywrapper symlink (euid = COMMONUSER), the
   ``setuid_`` prefix is stripped by ``get_command()``, the membership
   check fails, and this function returns silently so the program runs
   normally.

   Args:
      obj: An instance derived from PgLOG (e.g. DsArch, RdaCp); provides
         ``get_command()`` with access to ``self.PGLOG['COMMONUSER']``.
      pkgname: Distribution name (e.g. ``rda_python_dsarch``).
      appnames: List of program names provided by the package that need
         setuid (e.g. ``['dsarch']`` or ``['rdacp', 'rdakill', 'rdamod']``).
   """
   if obj.get_command(sys.argv[0]) not in ['setuid_' + a for a in appnames]:
      return
   usgfile = os.path.join(os.path.dirname(__file__), 'setuid_setup.usg')
   with open(usgfile) as f:
      text = f.read()
   text = text.replace('{PKGNAME}', pkgname)
   text = text.replace('{APPNAMES}', '   '.join(appnames))
   print(text)
   sys.exit(0)
