@echo off
setlocal
set "ROOT=D:\REMIX_AUTO_ALIGN_V6_DEV"
set "SOURCE=%ROOT%\windows_v8_27_MAG_NATIVE_SYNC_QA"
set "PY=D:\REMIX_SIGNAL_AUTOEQ_PARALLEL_QA_20261029\.venv\Scripts"
if not exist "%SOURCE%\overlay_v7.py" (
  echo HOLD: Canonical RemiX Dou source missing
  exit /b 2
)
if not exist "%PY%\python.exe" (
  echo HOLD: RemiX Python environment missing
  exit /b 2
)
"%PY%\python.exe" "%ROOT%\VERIFY_REMIX_DOU_MAIN.py" --launch-check
if errorlevel 1 (
  echo HOLD: RemiX Dou ownership/duplicate/active-source guard did not pass
  exit /b 2
)
cd /d "%SOURCE%"
start "RemiX Dou V8.42" "%PY%\pythonw.exe" "%SOURCE%\overlay_v7.py"
endlocal
