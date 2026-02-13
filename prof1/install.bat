@echo off
REM Install Chatterbox on Prof1 (Windows)
REM Run as Administrator
echo Installing Chatterbox for Prof1...
powershell -ExecutionPolicy Bypass -File services\install_service.ps1 -MachineId prof1
pause
