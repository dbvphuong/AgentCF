@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%~dp0apps\client\src"
set "PYTHONUTF8=1"
echo Keep run.bat open for Server and Web. This window runs the Skill 0 test PC.
"%~dp0.venv\Scripts\python.exe" "%~dp0apps\client\scripts\skill0_test_project.py" serve
if errorlevel 1 pause
endlocal
