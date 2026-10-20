@echo off
setlocal
rem ModDesk builder. Produces:
rem    ModDesk-Setup.exe  - the installer (folder picker, shortcuts, updates in place). Share/run this one.
rem    ModDesk\ModDesk.exe - a portable copy you can also run straight from here.
rem Updating later does NOT need this: use Settings > Updates in ModDesk (moddesk.py from a file or GitHub).
rem Needs Python 3.9+ from python.org with "Add python.exe to PATH" ticked.
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
  if not defined CI pause
  exit /b 1
)
for %%F in (moddesk.py launcher.py installer.py make_payload.py) do (
  if not exist %%F (
    echo %%F must be in the same folder as build.bat.
    if not defined CI pause
    exit /b 1
  )
)

python -m pip install --upgrade pyinstaller
if errorlevel 1 (
  echo Could not install PyInstaller.
  if not defined CI pause
  exit /b 1
)
rem Optional: in-app browser windows (uses the Edge WebView2 that Windows 10/11 already has).
python -m pip install --upgrade pywebview
if errorlevel 1 echo (pywebview could not be installed - links will open in your normal browser instead.)

set ICONARG=
if exist icon.ico set ICONARG=--icon "%~dp0icon.ico"

if exist _dist rmdir /s /q _dist
if exist _stage rmdir /s /q _stage
python -m PyInstaller --noconfirm --onedir --windowed --name ModDesk %ICONARG% ^
  --distpath "%~dp0_dist" --workpath "%~dp0_work" --specpath "%~dp0_work" ^
  --collect-all webview --exclude-module unittest --exclude-module pydoc --exclude-module doctest ^
  "%~dp0launcher.py"
if errorlevel 1 (
  echo Build failed.
  if not defined CI pause
  exit /b 1
)

rem Clean program files only (no user data) go into _stage; that is what the installer carries.
robocopy "_dist\ModDesk" "_stage" /E /NFL /NDL /NJH /NJS /NP >nul
mkdir _stage\app
copy /Y moddesk.py _stage\app\moddesk.py >nul
if exist icon.png copy /Y icon.png _stage\icon.png >nul
if exist icon.ico copy /Y icon.ico _stage\icon.ico >nul

rem Portable copy: copy over the existing ModDesk folder so its location (and a pinned icon) never change.
if not exist ModDesk mkdir ModDesk
robocopy "_stage" "ModDesk" /E /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (
  echo Could not copy the files. Is ModDesk.exe still running? Close it and run build.bat again.
  if not defined CI pause
  exit /b 1
)

python make_payload.py _stage payload.zip
if errorlevel 1 (
  echo Could not make payload.zip.
  if not defined CI pause
  exit /b 1
)
python -m PyInstaller --noconfirm --onefile --windowed --name ModDesk-Setup %ICONARG% ^
  --distpath "%~dp0_dist2" --workpath "%~dp0_work2" --specpath "%~dp0_work2" ^
  --add-data "%~dp0payload.zip;." --add-data "%~dp0icon.ico;." ^
  --exclude-module unittest --exclude-module pydoc --exclude-module doctest ^
  "%~dp0installer.py"
if errorlevel 1 (
  echo Setup build failed.
  if not defined CI pause
  exit /b 1
)
copy /Y "_dist2\ModDesk-Setup.exe" "ModDesk-Setup.exe" >nul

rmdir /s /q _dist 2>nul
rmdir /s /q _dist2 2>nul
rmdir /s /q _work 2>nul
rmdir /s /q _work2 2>nul
rmdir /s /q _stage 2>nul
del payload.zip 2>nul

echo.
echo Done!
echo   ModDesk-Setup.exe     the installer (pick a folder, shortcuts, updates in place, keeps your data)
echo   ModDesk\ModDesk.exe   portable copy, runs from where it is
echo.
echo   Updating later: Settings ^> Updates in ModDesk (moddesk.py from a file or GitHub). No rebuild needed.
echo.
if not defined CI pause
