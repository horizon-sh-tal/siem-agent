@echo off
REM Install Chatterbox on Prof2 (Windows)
REM Run as Administrator
echo Installing Chatterbox for Prof2...
powershell -ExecutionPolicy Bypass -File services\install_service.ps1 -MachineId prof2
pause
