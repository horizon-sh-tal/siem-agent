@echo off
REM SIEM Agent – Windows Installer
REM Run as Administrator
echo Installing SIEM Agent for Windows...
powershell -ExecutionPolicy Bypass -File services\install_service.ps1
pause
