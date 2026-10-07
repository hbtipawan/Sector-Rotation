@echo off
REM Run the whole pipeline on your own Windows PC and open the site.
REM No login or keys needed. Double-click this file.

cd /d "%~dp0"
python -m pip install -q -r requirements.txt || goto :fail
python scripts\update_reference.py
python scripts\fetch_prices.py %* || goto :fail
python scripts\compute.py || goto :fail

echo.
echo Done. Opening http://localhost:8000  (close this window to stop the local site)
start "" http://localhost:8000
cd docs
python -m http.server 8000
exit /b 0

:fail
echo.
echo Something failed - read the message above.
pause
exit /b 1
