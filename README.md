RDA Python package, including a C code wrapper, to execute commandline applications
via setuid for effective and common user names.

## Overview

`rda_python_setuid` provides a C binary (`pywrapper`) that acquires a setuid effective
user, then `execv`s a Python entry point script.  This allows Python programs to run
as a designated common user (e.g. `gdexdata`) without requiring `sudo` access.

Two modes are supported:

- **Mode 1 (CommonUser program):** a symlink `dsarch -> pywrapper` runs `setuid_dsarch`
  as the common user.
- **Mode 2 (pgstart specialist):** a copy `pgstart_zji` runs any command as specialist
  `zji` via `pgstart.py`, restricted to authorized users.

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
automatically.  `pywrapper-install -l/--link` locks it down to `chmod 700` so users
cannot bypass the setuid wrapper by running it directly.

## Environment setup

### Option A — Python venv (DECS machines)

```bash
python3 -m venv $ENVHOME          # e.g. /glade/u/home/gdexdata/gdexmsenv
source $ENVHOME/bin/activate
pip install rda_python_setuid rda_python_dsarch ...
```

### Option B — Conda (DAV/Casper)

```bash
conda create -n pg-gdex python=3.10
conda activate pg-gdex
pip install rda_python_setuid rda_python_dsarch ...
```

The conda environment is typically at `/glade/work/gdexdata/conda-envs/pg-gdex`.

## Installation

After setting up the environment and installing packages, run `pywrapper-install`
with no arguments to display the full user guide:

```bash
pywrapper-install
```

### Full setuid setup (requires sudo access to CommonUser)

```bash
# 1. Install the target package (pulls in rda_python_setuid automatically):
pip install rda_python_dsarch

# 2. Compile pywrapper C binary (once per environment):
pywrapper-install

# 3. Wire up each program as a setuid entry:
pywrapper-install -l dsarch

# 4. Optionally, allow a specialist to run commands as themselves:
pywrapper-install -p -u zji
```

### Simple install (no sudo required, runs as current user)

Users who do not need the setuid mechanism can skip steps 2–4 and create a
direct symlink from `dsarch` to `setuid_dsarch`:

```bash
pip install rda_python_dsarch
pywrapper-install -l dsarch -s
```

## Runtime flow

```
user runs:  dsarch [args]
              |  (symlink -> pywrapper, setuid bit -> EUID=gdexdata)
pywrapper.c:  execv(bin/setuid_dsarch, args)
              |  (chmod 700, only gdexdata can exec directly)
setuid_dsarch: calls dsarch:main() as gdexdata
```

## Github

<https://github.com/NCAR/rda-python-setuid>
