@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  where py >nul 2>nul
  if errorlevel 1 (
    python -m venv .venv
  ) else (
    py -3 -m venv .venv
  )
  if errorlevel 1 goto error
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error
".venv\Scripts\python.exe" -m sistema_almacen.users --ensure
if errorlevel 1 goto error
echo.
echo TintaStock - abre http://127.0.0.1:8001
echo Presiona Ctrl+C para detener el servidor.
".venv\Scripts\python.exe" -m uvicorn sistema_almacen.main:app --host 127.0.0.1 --port 8001
if errorlevel 1 goto error
exit /b 0
:error
echo No se pudo iniciar TintaStock. Comprueba Python 3.10 o superior.
pause
exit /b 1
