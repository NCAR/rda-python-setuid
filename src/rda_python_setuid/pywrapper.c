/***************************************************************************************\
 *
 *    Title: pywrapper.c
 *   Author: Zaihua Ji, zji@ucar.edu
 *     Date: 2025-03-17
 *  Purpose: C wrapper to start any executable python code as an effective user
 *
 * Instruction:
 *    python -m venv $ENVHOME
 *    python -m pip install rda_python_setuid
 *
 *    # Compile pywrapper and set setuid bit (owned by CommonUser):
 *    pywrapper-install --user CommonUser [--envhome $ENVHOME/bin]
 *
 *    # For an existing python program, $ENVHOME/bin/CommonProgram.py, to execute it
 *    # as the common user (Mode 1 - symlink):
 *    pywrapper-install --link CommonProgram [--envhome $ENVHOME/bin]
 *    CommonProgram [options]
 *
 *    # For a specialist to run commands as themselves via pgstart (Mode 2):
 *    pywrapper-install --pgstart --user EffectUser [--envhome $ENVHOME/bin]
 *    pgstart_EffectUser EffectProgram [options]
 *
 *           N: python 3 release number, it is 10 for Python 3.10.12
 *  CommonUser: a common user login name, such as gdexdata, for GDEXMS configuration
 *  EffectUser: any user login name in the same group of the common user
 *    $ENVHOME: /glade/u/home/gdexdata/rdamsenv (venv) on DECS machines, and
 *              /glade/work/gdexdata/conda-envs/pg-rda (conda) on DAV
 *
 * Convention:
 *    Any Python package whose program is to be run via pywrapper must register
 *    its connector entry point with a setuid_ prefix in pyproject.toml, e.g.:
 *       [project.scripts]
 *       "setuid_dsarch" = "rda_python_dsarch.dsarch:main"
 *    pip install places setuid_dsarch in $ENVHOME/bin/.  pywrapper locates it by
 *    prepending setuid_ to the invoked program name.  No manual script creation needed.
 *    pywrapper-install --link will chown setuid_dsarch to CommonUser and chmod 700,
 *    preventing direct execution by other users while still allowing pywrapper
 *    (which runs with EUID=CommonUser via the setuid bit) to execv it.
 *
 \***************************************************************************************/

#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <limits.h>
#include <libgen.h>

int is_executable(const char *filename) {
   struct stat sb;

   if(stat(filename, &sb) == 0 && sb.st_mode & S_IXUSR) {
      return 1;
   } else {
      return 0;
   }
}

/* main program */
int main(int argc, char *argv[]) {
   char *name;
   char cname[80], prog[PATH_MAX];
   char exepath[PATH_MAX];
   char *fpath;
   ssize_t exelen;
   char pgstart[] = "pgstart";
   char **apntr = argv;

   exelen = readlink("/proc/self/exe", exepath, sizeof(exepath) - 1);
   if(exelen == -1) {
      perror("readlink /proc/self/exe");
      exit(1);
   }
   exepath[exelen] = '\0';
   fpath = dirname(exepath);

   name = strrchr(argv[0], '/');
   strncpy(cname, (name == NULL ? argv[0] : ++name), sizeof(cname) - 1);
   cname[sizeof(cname) - 1] = '\0';

   if(strstr(cname, pgstart) == cname) {
      if(argc == 1 || argv[1][0] == '-') {
         strncpy(cname, pgstart, sizeof(cname) - 1);
      } else {
         argv += 1;
         name = strrchr(argv[0], '/');
         strncpy(cname, (name == NULL ? argv[0] : ++name), sizeof(cname) - 1);
         cname[sizeof(cname) - 1] = '\0';
      }
   }
   if(snprintf(prog, sizeof(prog), "%s/setuid_%s", fpath, cname) >= (int)sizeof(prog)) {
      fprintf(stderr, "pywrapper: path too long\n");
      exit(1);
   }
   if(is_executable(prog) == 0) {
      /* fall back to cname.py for backward compatibility */
      if(snprintf(prog, sizeof(prog), "%s/%s.py", fpath, cname) >= (int)sizeof(prog)) {
         fprintf(stderr, "pywrapper: path too long\n");
         exit(1);
      }
      if(is_executable(prog) == 0) {
         if(snprintf(prog, sizeof(prog), "%s/pgstart.py", fpath) >= (int)sizeof(prog)) {
            fprintf(stderr, "pywrapper: path too long\n");
            exit(1);
         }
         argv = apntr;
      }
   }
   execv(prog, argv);  /* call Python script */
   perror(prog);       /* execv only returns on error */
   exit(1);
}
