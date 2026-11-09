#!/usr/bin/env bash
# DMT: the window (Python: numpy, Pillow, customtkinter in ./venv). Save renders with Main.jl when Julia is installed.
set -e
cd "$(dirname "$0")"
PY=venv/bin/python
[ -x venv/Scripts/python.exe ] && PY=venv/Scripts/python.exe
if [ ! -x "$PY" ]; then
    echo "Setting up, once..."
    python3 -m venv venv
    PY=venv/bin/python
    [ -x venv/Scripts/python.exe ] && PY=venv/Scripts/python.exe
fi
if ! cmp -s requirements.txt venv/requirements.installed; then
    "$PY" -m pip install -r requirements.txt
    cp requirements.txt venv/requirements.installed
fi
if command -v julia >/dev/null 2>&1 && [ ! -f venv/julia.instantiated ]; then
    echo "Getting Main.jl's Julia packages, once..."
    julia --project=. -e "using Pkg; Pkg.instantiate()" && echo done > venv/julia.instantiated
fi
exec "$PY" dmt.py "$@"
