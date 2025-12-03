@echo off
REM GreenTech Painting - QuickBooks API Server (Windows)
REM Starts the API server for VBA integration

echo Starting GreenTech QuickBooks API Server...
echo.

cd /d "%~dp0"
python start_server.py

pause


