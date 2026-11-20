@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0infra\start-client.ps1" %*
