@echo off
REM Launch OkSentinel Flask Web Application
REM This batch file runs the Flask web server

echo Starting OkSentinel Web Application...
echo.
echo Server will be available at: http://localhost:5000
echo Press Ctrl+C to stop the server
echo.

python webapp/server.py

pause

