# DMT: the window (Python: numpy, Pillow, customtkinter in .\venv). Save renders with Main.jl when Julia is installed.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$Py = "venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    Write-Host "Setting up, once..."
    if (Get-Command py -ErrorAction SilentlyContinue) { py -3 -m venv venv } else { python -m venv venv }
}
$stamp = "venv\requirements.installed"
if (-not (Test-Path $stamp) -or (Get-FileHash requirements.txt).Hash -ne (Get-FileHash $stamp).Hash) {
    & $Py -m pip install -r requirements.txt
    Copy-Item requirements.txt $stamp -Force
}
$Jl = (Get-Command julia -ErrorAction SilentlyContinue).Source
if (-not $Jl) { $Jl = Get-ChildItem "$env:LOCALAPPDATA\Programs\Julia-*\bin\julia.exe" -ErrorAction SilentlyContinue | Select-Object -Last 1 -ExpandProperty FullName }
if ($Jl -and -not (Test-Path "venv\julia.instantiated")) {
    Write-Host "Getting Main.jl's Julia packages, once..."
    & $Jl --project=. -e "using Pkg; Pkg.instantiate()"
    if ($LASTEXITCODE -eq 0) { Set-Content "venv\julia.instantiated" "done" }
}
& $Py dmt.py @args
