RDA Python package, including a C code wrapper, to execute commandline applications
via setuid for effective and common user names.

## Overview

`rda_python_setuid` provides a C binary (`pywrapper`) that acquires a setuid effective
user, then `execv`s a Python entry point script.  This allows Python programs to run
as a designated common user (e.g. `gdexdata`) without requiring `sudo` access.

Three modes are supported:

- **Mode 1 (CommonUser program):** a symlink `dsarch -> pywrapper` runs `setuid_dsarch`
  as the common user.
- **Mode 2 (pgstart specialist):** a copy `pgstart_<loginname>` (e.g. `pgstart_zji`)
  runs any command as `<loginname>` via `pgstart.py`.  `<loginname>` can be any
  user that belongs to the same group as `PGLOG['COMMONUSER']`.  Execution is
  restricted to authorized callers (see `pgstart.py` below).
- **Mode 3 (cmwrapper, callers outside the group):** a dedicated binary compiled
  from `cmwrapper.c` and installed `4755` runs ONE fixed program as the common
  user for any user on the machine, including users outside the common user's
  group (see "cmwrapper" below).  With `-s|--simple` the same binary is installed
  `755` with no setuid, which publishes ONE program of this environment to users
  who have no environment of their own.

Two Python entry points are packaged alongside the C wrapper:

- **`pywrapper.py`** — the default fallback target executed when `pywrapper.c`
  cannot resolve a matching `setuid_<program>` entry point.  Acquires the
  effective UID via `PgLOG.set_suid()`, prints the caller's real and effective
  user names, and shows the `pyproject.toml` snippet plus the
  `pywrapper-install -l <program>` command needed to wrap a new script.
  Diagnostic flags `-env`, `-inc`, and `-plg` dump the environment variables,
  `sys.path`, and `PGLOG` dictionary respectively — handy for verifying the
  setuid environment before wiring up a real program.

- **`pgstart.py`** — the Mode 2 launcher invoked through a `pgstart_<loginname>`
  copy of `pywrapper`.  Reads the real/effective UIDs from `PGLOG`, then
  permits execution only if the real user is in
  `[PGLOG['ADMINUSER'], euser, PGLOG['COMMONUSER']]`
  (i.e. the admin specialist `PGLOG['ADMINUSER']` — default `zji` — the
  effective user themselves, or the shared common user); unauthorized callers receive
  an informational message and exit.  After authorization it parses leading
  flag tokens — `-bg` (background via `subprocess.Popen`), `-fg` (explicit
  foreground, default), `-cwd <dir>` (chdir before exec), and the same
  `-env`/`-inc`/`-plg` diagnostics as `pywrapper.py` — and then runs the
  remaining arguments as a command (`subprocess.run`/`Popen`) under the
  effective UID, logging a host/program/timestamp/user line to `pgstart.log`.

## Dependency requirement

Any Python package whose programs are to be run via the setuid mechanism must declare
`rda_python_setuid` as a dependency in its `pyproject.toml`:

```toml
[project]
dependencies = [
  "rda_python_setuid",
  ...
]
```

It must also register each wrapped program's connector entry point with a `setuid_`
prefix:

```toml
[project.scripts]
"setuid_dsarch" = "rda_python_dsarch.dsarch:main"
```

`pip install` then places `setuid_dsarch` in the environment's `bin/` directory
automatically.  `pywrapper-install -l/--link` creates the symlink
`dsarch -> pywrapper`; running `dsarch` goes through the setuid wrapper, which
execs `setuid_dsarch` as CommonUser.

The `main()` of each wrapped program (e.g. `rda_python_dsarch/dsarch.py`) must
also call `show_setup_guide()` at the top of `main()`, passing an instance of
the program's class along with the package name and list of setuid program
names:

```python
def main():
   from rda_python_setuid.setup_guide import show_setup_guide
   object = DsArch()
   show_setup_guide(object, 'rda_python_dsarch', ['dsarch'])
   ...
```

When `setuid_dsarch` is invoked directly (before pywrapper symlinks are set
up, so euid ≠ CommonUser), `show_setup_guide()` prints the shared setuid setup
guide and exits.  When invoked via the `dsarch -> pywrapper` symlink (euid =
CommonUser), `get_command()` strips the `setuid_` prefix, the check inside
`show_setup_guide()` fails, and the program runs normally.

## Environment setup

Create a Python environment first; package installs in the next section run
inside whichever environment you activate here.

### Option A — Python venv (DECS machines)

```bash
python3 -m venv $ENVHOME          # e.g. /glade/u/home/gdexdata/gdexmsenv
source $ENVHOME/bin/activate
```

### Option B — Conda (DAV/Casper)

```bash
conda create --prefix $ENVHOME python=3.12   # e.g. /glade/work/gdexdata/conda-envs/pg-gdex
conda activate $ENVHOME
```

## Installing rda-python-setuid

Pick whichever install mode fits your workflow.  All four pull in the
transitive dependency (`rda_python_common`) automatically.  Once installed,
the `pywrapper-install` CLI is available for the setuid wiring steps below.

For local development, clone this repo alongside your project and install it
in editable mode so that changes are picked up without re-installing:

```bash
git clone https://github.com/NCAR/rda-python-setuid.git
cd rda-python-setuid
pip install -e .
```

To test a specific branch (e.g. an in-progress feature or fix branch), pass
`-b/--branch` to `git clone`:

```bash
git clone -b <branch-name> https://github.com/NCAR/rda-python-setuid.git
cd rda-python-setuid
pip install -e .
```

For a regular (non-editable) install from a checkout:

```bash
pip install /path/to/rda-python-setuid
```

For a production install on a system that uses the published distribution:

```bash
pip install rda_python_setuid
```

## Setuid wrapper setup

With `rda_python_setuid` installed in the active environment, run
`pywrapper-install` with no arguments to display the full user guide:

```bash
pywrapper-install
```

### Full setuid setup (requires sudo access to CommonUser)

```bash
# 1. Install the target package (pulls in rda_python_setuid automatically):
pip install rda_python_dsarch

# 2. Compile pywrapper C binary (once per environment):
pywrapper-install -c|--compile

# 3. Wire up each program as a setuid entry (specify name or use 'all'):
pywrapper-install -l|--link dsarch
pywrapper-install -l|--link all           # auto-link every setuid_* entry not yet linked

# 4. Optionally, install a pgstart_<loginname> binary so <loginname> (any user
#    in the same group as PGLOG['COMMONUSER']) can run commands as themselves
#    via the setuid wrapper.  Same command in both cases — only the invoker
#    differs:
#
#    4a. If PGLOG['ADMINUSER'] (default zji) can `sudo -u <loginname>`, the
#        admin sets it up on the user's behalf:
pywrapper-install -p|--pgstart -n|--username <loginname>
#
#    4b. Otherwise <loginname> runs the same command themselves (no sudo
#        from ADMINUSER required, since they already are <loginname>):
pywrapper-install -p|--pgstart -n|--username <loginname>
```

### Update an existing installation (no sudo required)

When the package is upgraded and a new `pywrapper.c` is bundled, use `-u/--update`
to recompile and reinstall all setuid binaries without needing `sudo`.  The existing
`pgstart_*` binaries in `bin/` are used to perform the privileged operations:

```bash
pywrapper-install -u|--update [-n|--username gdexdata] [-e|--envhome $ENVHOME]
```

### Simple install (no sudo required, runs as current user)

Users who do not need the setuid mechanism can skip steps 2–4 and create a
direct symlink from `dsarch` to `setuid_dsarch`:

```bash
pip install rda_python_dsarch
pywrapper-install -l|--link dsarch -s|--simple
pywrapper-install -l|--link all -s|--simple   # or link all setuid_* entries at once
```

### cmwrapper (Mode 3, for callers outside the CommonUser group)

`pywrapper` is installed `4750`, so only members of the common user's group can
execute it.  That group restriction is what makes it safe for `pywrapper` to pick
the program to run from `basename(argv[0])`: anyone who can execute it can already
reach every `setuid_*` entry in `bin/` just by naming the symlink differently.

`cmwrapper` is for the opposite case — letting users who are **not** in the common
user's group run one specific program as the common user.  It is installed `4755`,
i.e. executable by everyone, so nothing about what it runs may come from the caller:

- the absolute path of the script to exec, and the program name, are baked into the
  binary at compile time, so it cannot be symlinked under another name to reach a
  different program;
- the environment is replaced with a fixed whitelist (`HOME`, `USER`, `LOGNAME`,
  `TERM`, `LANG`, `TZ`, a fixed `PATH` and `PYTHONNOUSERSITE=1`), so `PYTHONPATH`,
  `PYTHONHOME`, `LD_PRELOAD`, `LD_LIBRARY_PATH` and the `PGLOG` path variables
  (`DSDHOME`, `DSSHOME`, `LOGPATH`, `COMMONUSER`, ...) cannot be used to run
  arbitrary code, or redirect where files are written, as the common user.

One binary is compiled per wrapped program:

```bash
# Install bin/gdexdrop as a 4755 binary that execs bin/setuid_gdexdrop:
pywrapper-install -m|--cmlink gdexdrop

# Same, but installed into a common area already on everyone's PATH:
pywrapper-install -m|--cmlink gdexdrop -d|--destdir /glade/u/home/gdexdata/bin

# Point it at a script somewhere other than bin/setuid_gdexdrop:
pywrapper-install -m|--cmlink gdexdrop -t|--target /path/to/setuid_gdexdrop
```

Only wrap a program that does its own authorization and confines where it writes,
such as `gdexdrop`, which checks its caller against an access list and copies only
into the requested dataset directory.  Never wrap a general purpose program such as
`gdexcp`: at `4755` that would let any user on the machine read or overwrite any
file of the common user.

### cmwrapper with no setuid, to publish a program of this environment

Add `-s|--simple` to compile the binary `755` with no setuid bit.  Nothing runs as
another user; the binary exists only so that users who do not have this environment,
and cannot activate a venv or a conda environment, can still run one of its programs
by name — `gdexls`, for example:

```bash
# Install /glade/u/apps/contrib/gdexls, a 755 binary that execs bin/gdexls:
pywrapper-install -m|--cmlink gdexls -s|--simple -d|--destdir /glade/u/apps/contrib
```

Since there is no privilege change, sanitizing the environment would buy no security
and would only break the caller's own settings, so the caller's environment is passed
through except for `PYTHONPATH`, `PYTHONHOME` and `PYTHONSTARTUP`, which would send
the program to another environment's modules.  The default `-t|--target` is
`bin/PROGRAM` rather than `bin/setuid_PROGRAM`, and no `sudo` access is required.

## Runtime flow

```
user runs:  dsarch [args]
              |  (symlink -> pywrapper, setuid bit -> EUID=gdexdata)
pywrapper.c:  execv(bin/setuid_dsarch, args)
setuid_dsarch: calls dsarch:main() as gdexdata

user runs:  gdexdrop [args]
              |  (dedicated 4755 binary, setuid bit -> EUID=gdexdata)
cmwrapper.c:  execve(bin/setuid_gdexdrop, args, sanitized env)
setuid_gdexdrop: calls gdexdrop:main() as gdexdata

user runs:  gdexls [args]
              |  (dedicated 755 binary, no setuid, -DCMSIMPLE)
cmwrapper.c:  execv(bin/gdexls, args)
gdexls:       calls gdexls:main() as the calling user
```

## Github

<https://github.com/NCAR/rda-python-setuid>
