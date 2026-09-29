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

rem Cartella originale del plugin/power: lo script la usa al posto di __file__
rem (clone della power per il bug Kiro #6278, plugin.json per la versione).
for %%R in ("%~dp0..") do set "DS_PLUGIN_ROOT=%%~fR"

rem Claude Desktop e' un pacchetto MSIX: %APPDATA%\Claude e' virtualizzata e la
rem vedono solo i processi del pacchetto (questo cmd si'). Un Python a sua volta
rem pacchettizzato (Python Install Manager, alias in WindowsApps) NON la vede e
rem fallisce con "can't open file ... [Errno 2]". Si avvia quindi una copia dello
rem script in una cartella del profilo, fuori da AppData, che tutti vedono.
rem La copia si rifa' solo se lo script e' cambiato; se fallisce si usa l'originale.
set "HOSTDIR=%DS_HOST%"
if not defined HOSTDIR set "HOSTDIR=kiro"
set "RUNDIR=%USERPROFILE%\.ds-release\runtime\%HOSTDIR%"
set "RUNSCRIPT=%RUNDIR%\ds_release_mcp.py"
if not exist "%RUNDIR%" mkdir "%RUNDIR%" >nul 2>nul
fc /b "%SCRIPT%" "%RUNSCRIPT%" >nul 2>nul
if errorlevel 1 (
  rem copia su un nome temporaneo e poi rinomina: un'altra sessione che parte
  rem nello stesso momento non legge mai un file scritto a meta'
  set "TMPSCRIPT=%RUNDIR%\ds_release_mcp.!RANDOM!!RANDOM!.tmp"
  copy /y "%SCRIPT%" "!TMPSCRIPT!" >nul 2>nul
  if exist "!TMPSCRIPT!" (
    move /y "!TMPSCRIPT!" "%RUNSCRIPT%" >nul 2>nul
    if exist "!TMPSCRIPT!" del "!TMPSCRIPT!" >nul 2>nul
  )
)
fc /b "%SCRIPT%" "%RUNSCRIPT%" >nul 2>nul
if not errorlevel 1 set "SCRIPT=%RUNSCRIPT%"

rem 1) eseguibili reali, prima degli alias WindowsApps
for %%P in (
  "%LOCALAPPDATA%\Python\bin\python.exe"
) do (
  call :try %%P && goto :run
)
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
  "%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
  "%PROGRAMFILES%\Python314\python.exe"
  "%PROGRAMFILES%\Python313\python.exe"
  "%PROGRAMFILES%\Python312\python.exe"
  "%PROGRAMFILES%\Python311\python.exe"
) do (
  call :try %%P && goto :run
)

rem 2) comandi nel PATH (possono essere alias del Microsoft Store o del
rem Python Install Manager)
for %%C in ("py -3" "python3" "python") do (
  call :try %%~C && goto :run
)
call :try "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe" && goto :run

rem nessun interprete utilizzabile: messaggio leggibile nel pannello MCP Servers
if defined BLIND (
  echo [ds-release] ERRORE: Python 3 c'e' ma non riesce ad aprire lo script: 1>&2
  echo [ds-release]   %SCRIPT% 1>&2
  echo [ds-release] Succede con il Python del Microsoft Store o del Python Install Manager, 1>&2
  echo [ds-release] che non vedono le cartelle private di Claude. Controlla di poter scrivere 1>&2
  echo [ds-release] in %USERPROFILE%\.ds-release, oppure installa Python da python.org: 1>&2
  echo [ds-release]   winget install --id Python.Python.3.12 -e 1>&2
) else (
  echo [ds-release] ERRORE: Python 3 non trovato su questo PC. 1>&2
  echo [ds-release] Installalo da PowerShell:  winget install --id Python.Python.3.12 -e 1>&2
  echo [ds-release] Durante l'installazione spunta "Add python.exe to PATH". 1>&2
)
if /i "%DS_HOST%"=="claude" (
  echo [ds-release] Poi CHIUDI E RIAPRI Claude. 1>&2
) else (
  echo [ds-release] Poi CHIUDI E RIAPRI Kiro. 1>&2
)
exit /b 1

:try
rem %* = comando candidato; verifica che esegua davvero codice Python 3 E che
rem riesca ad aprire lo script (un Python pacchettizzato puo' non vederlo)
set "CAND=%*"
%CAND% -c "import sys; sys.exit(0 if sys.version_info[0]==3 else 1)" >nul 2>nul
if errorlevel 1 exit /b 1
%CAND% -c "import sys; open(sys.argv[1]).close()" "%SCRIPT%" >nul 2>nul
if errorlevel 1 (
  set "BLIND=1"
  exit /b 1
)
set "PYEXE=%CAND%"
exit /b 0

:run
echo [ds-release] Avvio con: %PYEXE% (%SCRIPT%) 1>&2
%PYEXE% "%SCRIPT%"
exit /b %errorlevel%
