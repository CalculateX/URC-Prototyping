@echo off
title URC Environment Setup

:: 1. Initialize Conda using your specific path
call C:\Users\sande\miniconda3\Scripts\activate.bat

:: 2. Check if environment exists to decide between create or update
conda env list | findstr "urc_ground_station" > nul
if %errorlevel% equ 0 (
    echo Environment found. Updating...
    call conda env update -f environment.yml --prune
) else (
    echo Environment not found. Creating from YAML...
    call conda env create -f environment.yml
)

echo.
echo Setup Complete!
pause