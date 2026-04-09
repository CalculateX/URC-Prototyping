@echo off
title URC Clean Reinstall

echo === 1. Initializing Conda ===
call C:\Users\sande\miniconda3\Scripts\activate.bat

echo === 2. Removing the broken environment (Nuclear Option) ===
call conda remove --name urc_ground_station --all -y

echo === 3. Physically deleting lingering files (The TRUE Nuclear Option) ===
:: Conda remove often leaves broken pip files behind. This annihilates them.
if exist "C:\Users\sande\miniconda3\envs\urc_ground_station" (
    rmdir /s /q "C:\Users\sande\miniconda3\envs\urc_ground_station"
    echo Old environment folder destroyed.
) else (
    echo No lingering folder found.
)

echo === 4. Clearing Conda Cache ===
call conda clean --all -y

echo === 5. Creating fresh from YAML ===
call conda env create -f environment.yaml

echo.
echo === Reinstall Complete. You can now run launch_site.bat ===
pause