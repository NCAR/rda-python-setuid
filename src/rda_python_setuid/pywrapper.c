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
 *    cd $ENVHOME/bin/
 *    cp ../lib/python3.N/site-packages/rda_python_setuid/pywrapper.c ./
 *    sudo -u CommonUser gcc -o pywrapper $ENVHOME/bin/pywrapper.c
 *    sudo -u CommonUser chmod 4750 pywrapper
 *
 *    For an existing python program, $ENVHOME/bin/CommonProgram.py, to execute it
 *    as the common user:
 *    sudo -u CommonUser ln -s pywrapper CommonProgram
 *    CommonProgram [options]
 *
 *    For an existing python program, $ENVHOME/bin/EffectProgram.py, to execute it
 *    as the effective user:
 *    sudo -u EffectUser cp pywrapper pgstart_EffectUser
 *    sudo -u EffectUser chmod 4750 pgstart_EffectUser
 *    pgstart_EffectUser EffectProgram [options]
 *
 *           N: python 3 release number, it is 10 for Python 3.10.12
 *  CommonUser: a common user login name, such as rdadata, for RDAMS configuration
 *  EffectUser: any user login name in the same group of the common user
 *    $ENVHOME: /glade/u/home/rdadata/rdamsenv (venv) on DECS machines, and
 *              /glade/work/rdadata/conda-envs/pg-rda (conda) on DAV
 *
 \***************************************************************************************/

#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
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
   char cname[80], prog[255];
   char file[] = __FILE__;
   char *fpath = dirname(file);
   char pgstart[] = "pgstart";
   char **apntr = argv;

   name = strrchr(argv[0], '/');
   strcpy(cname, (name == NULL ? argv[0] : ++name));

   if(strstr(cname, pgstart) == cname) {
      if(argc == 1 || argv[1][0] == '-') {
         strcpy(cname, pgstart);
      } else {
         argv += 1;
         name = strrchr(argv[0], '/');
         strcpy(cname, (name == NULL ? argv[0] : ++name));
      }
   }
   sprintf(prog, "%s/%s.py", fpath, cname);
   if(is_executable(prog) == 0) {
      sprintf(prog, "%s/pgstart.py", fpath);
      argv = apntr;
   }
   execv(prog, argv);  /* call Python script */
}
