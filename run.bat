@echo off
setlocal
cd /d "%~dp0"
rem DMT: the window (Python: numpy, Pillow, customtkinter in .\venv). Save renders with Main.jl when Julia is installed.
set "PY=venv\Scripts\python.exe"
if not exist "%PY%" (
    echo Setting up, once...
    py -3 -m venv venv || python -m venv venv || goto :error
)
fc /b requirements.txt venv\requirements.installed >nul 2>&1
if errorlevel 1 (
    "%PY%" -m pip install -r requirements.txt || goto :error
    copy /y requirements.txt venv\requirements.installed >nul
)
rem Julia's packages for Main.jl (ColorSchemes, PNGFiles), once, when Julia is there
set "JL="
where julia >nul 2>&1 && set "JL=julia"
if not defined JL for /d %%D in ("%LOCALAPPDATA%\Programs\Julia-*") do if exist "%%D\bin\julia.exe" set "JL=%%D\bin\julia.exe"
if defined JL if not exist "venv\julia.instantiated" (
    echo Getting Main.jl's Julia packages, once...
    "%JL%" --project=. -e "using Pkg; Pkg.instantiate()" && echo done> venv\julia.instantiated
)
"%PY%" dmt.py %*
exit /b %ERRORLEVEL%
:error
echo Setup failed: DMT needs Python 3.9 or newer.
pause
exit /b 1
