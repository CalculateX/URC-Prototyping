@echo off
title URC Ground Station Launcher

echo Launching Base Station...

:: 1. Open the browser
start http://127.0.0.1:5000

:: 2. Run the app directly
python app.py

pause