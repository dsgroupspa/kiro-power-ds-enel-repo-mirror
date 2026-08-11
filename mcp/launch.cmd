@echo off
rem Avvia il server MCP trovando Python 3 anche quando NON e' nel PATH.
rem Ogni candidato viene provato davvero (gli stub del Microsoft Store
rem "esistono" ma non eseguono nulla, quindi il solo where.exe non basta).
setlocal enabledelayedexpansion

set "SCRIPT=%~dp0ds_release_mcp.py"
if not exist "%SCRIPT%" (
  echo [ds-release] ERRORE: script non trovato: %SCRIPT% 1>&2
  exit /b 1
)

rem 1) comandi nel PATH, in ordine di preferenza
for %%C in ("py -3" "python3" "python") do (
  call :try %%~C && goto :run
)

rem 2) percorsi tipici delle installazioni Windows (per-utente e di sistema)
for %%D in (
  "%LOCALAPPDATA%\Programs\Python"
  "%PROGRAMFILES%\Python"
  "%PROGRAMFILES(x86)%\Python"
  "C:\Python"
) do (
  if exist %%D (
    for /f "delims=" %%P in ('dir /b /o-n "%%~D*" 2^>nul') do (
      call :try "%%~D%%P\python.exe" && goto :run
    )
    call :try "%%~D\python.exe" && goto :run
  )
)
for %%P in (
  "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
  "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe"
  "%PROGRAMFILES%\Python313\python.exe"
  "%PROGRAMFILES%\Python312\python.exe"
  "%PROGRAMFILES%\Python311\python.exe"
) do (
  call :try %%P && goto :run
)

rem nessun interprete utilizzabile: messaggio leggibile nel pannello MCP Servers
echo [ds-release] ERRORE: Python 3 non trovato su questo PC. 1>&2
echo [ds-release] Installalo da PowerShell:  winget install --id Python.Python.3.12 -e 1>&2
echo [ds-release] Durante l'installazione spunta "Add python.exe to PATH". 1>&2
echo [ds-release] Poi CHIUDI E RIAPRI Kiro. 1>&2
exit /b 1

:try
rem %* = comando candidato; verifica che esegua davvero codice Python 3
set "CAND=%*"
%CAND% -c "import sys; sys.exit(0 if sys.version_info[0]==3 else 1)" >nul 2>nul
if errorlevel 1 exit /b 1
set "PYEXE=%CAND%"
exit /b 0

:run
echo [ds-release] Avvio con: %PYEXE% 1>&2
%PYEXE% "%SCRIPT%"
exit /b %errorlevel%
