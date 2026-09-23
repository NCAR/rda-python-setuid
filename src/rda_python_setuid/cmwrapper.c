/***************************************************************************************\
 *
 *    Title: cmwrapper.c
 *   Author: Zaihua Ji, zji@ucar.edu
 *     Date: 2026-09-23
 *  Purpose: C wrapper to start ONE fixed python program as an effective user, for
 *           callers who are NOT in the common user's group (Mode 4755).
 *
 * Difference from pywrapper.c:
 *    pywrapper is installed 4750, so only members of the common user's group can
 *    execute it, and it picks the program to exec from basename(argv[0]) with the
 *    directory taken from /proc/self/exe.  That is safe only because of the 4750
 *    group restriction: anyone who can run it can already run every setuid_* entry
 *    in the bin directory just by naming the symlink differently.
 *
 *    cmwrapper is installed 4755, i.e. executable by EVERY user on the machine, so
 *    neither the program nor its directory may come from the caller:
 *      - the absolute path of the program to exec is baked in at compile time as
 *        CMEXEC, and the program name reported to the program is baked in as CMPROG;
 *      - the environment is replaced with a fixed whitelist, so PYTHONPATH,
 *        PYTHONHOME, LD_PRELOAD, LD_LIBRARY_PATH and the PGLOG path variables
 *        (DSDHOME, DSSHOME, LOGPATH, COMMONUSER, ...) cannot be used to run
 *        arbitrary code, or redirect where files are written, as the common user.
 *
 *    One cmwrapper binary is therefore compiled per wrapped program; it can NOT be
 *    symlinked under another name to reach a different program.
 *
 * IMPORTANT: a program wrapped by cmwrapper is callable by anybody, so it must do
 *    its own authorization (as gdexdrop does with its access list) and must confine
 *    where it writes.  Do NOT wrap a general purpose program such as gdexcp.
 *
 * Instruction:
 *    # Compile and install bin/PROGRAM as a 4755 setuid binary owned by CommonUser:
 *    pywrapper-install -m|--cmlink PROGRAM [-n|--username CommonUser] [-e|--envhome $ENVHOME]
 *
 *    # Compile it 755 with no setuid, to publish a program of an environment to
 *    # users who do not have that environment (-DCMSIMPLE):
 *    pywrapper-install -m|--cmlink PROGRAM -s|--simple [-d|--destdir DIR]
 *
 *    With -DCMSIMPLE there is no privilege change, so the caller's environment is
 *    kept except for PYTHONPATH, PYTHONHOME and PYTHONSTARTUP, which would send the
 *    program to another environment's modules.  Sanitizing the rest would buy no
 *    security and would only break the caller's own settings.
 *
 \***************************************************************************************/

#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#ifndef CMPROG
#error "CMPROG must be defined at compile time, e.g. -DCMPROG=\"gdexdrop\""
#endif
#ifndef CMEXEC
#error "CMEXEC must be defined at compile time, e.g. -DCMEXEC=\"/env/bin/setuid_gdexdrop\""
#endif

#ifdef CMSIMPLE

/* Python variables of the caller that would make the wrapped program load modules
   from somewhere other than its own environment. */
static const char *dropvars[] = {"PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", NULL};

#else

#define CMPATH "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

/* Environment variables passed through from the caller.  Everything else is
   dropped; in particular every PYTHON*, LD_* and PGLOG path variable. */
static const char *keepvars[] = {"HOME", "USER", "LOGNAME", "TERM", "LANG", "TZ", NULL};

#endif

/* main program */
int main(int argc, char *argv[]) {
   (void)argc;

#ifdef CMSIMPLE

   /* No privilege change, so sanitizing the environment buys no security and can
      only break the caller's own settings.  Only the Python variables that would
      send the program to another environment's modules are dropped. */
   int i;

   for(i = 0; dropvars[i] != NULL; i++) unsetenv(dropvars[i]);
   argv[0] = (char *)CMPROG;
   execv(CMEXEC, argv);

#else

   char *envp[16];
   char *value, *entry;
   size_t len;
   int i, n = 0;

   for(i = 0; keepvars[i] != NULL; i++) {
      value = getenv(keepvars[i]);
      if(value == NULL) continue;
      len = strlen(keepvars[i]) + strlen(value) + 2;
      entry = malloc(len);
      if(entry == NULL) {
         perror(CMPROG ": malloc");
         exit(1);
      }
      snprintf(entry, len, "%s=%s", keepvars[i], value);
      envp[n++] = entry;
   }
   envp[n++] = (char *)"PATH=" CMPATH;
   envp[n++] = (char *)"PYTHONNOUSERSITE=1";   /* ignore ~/.local site-packages */
   envp[n] = NULL;

   argv[0] = (char *)CMPROG;   /* the program identifies itself by this name */
   execve(CMEXEC, argv, envp);

#endif

   perror(CMEXEC);   /* exec only returns on error */
   exit(1);
}
