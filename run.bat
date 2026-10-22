@echo off
setlocal
rem Starts MySQL (Docker) and the API with auto-reload at http://localhost:8000
rem Usage: run.bat [port]

cd /d "%~dp0"

set "PORT=%~1"
if "%PORT%"=="" set "PORT=8000"

if not exist ".venv\Scripts\python.exe" (
    echo [error] .venv not found. Create it first:
    echo     python -m venv .venv
    echo     .venv\Scripts\python -m pip install -r requirements-dev.txt
    exit /b 1
)

if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo [info] Created .env from .env.example. Change JWT_SECRET before real use.
)

docker info >nul 2>&1
if errorlevel 1 (
    echo [error] Docker is not running. Start Docker Desktop and try again.
    exit /b 1
)

echo [info] Starting MySQL...
docker compose up -d mysql
if errorlevel 1 exit /b 1

echo [info] Waiting for MySQL to accept connections...
set /a TRIES=0
:wait_mysql
docker compose exec -T mysql mysqladmin ping -uapp -papp --silent >nul 2>&1
if not errorlevel 1 goto mysql_ready
set /a TRIES+=1
if %TRIES% geq 30 (
    echo [error] MySQL did not start in time. See: docker compose logs mysql
    exit /b 1
)
timeout /t 2 /nobreak >nul
goto wait_mysql

:mysql_ready
echo [info] MySQL is ready.

echo [info] Applying database migrations...
".venv\Scripts\python.exe" -m alembic upgrade head
if errorlevel 1 (
    echo [error] Migrations failed. See the message above.
    exit /b 1
)

echo [info] API:  http://localhost:%PORT%/api/v1/health
echo [info] Docs: http://localhost:%PORT%/docs
echo [info] Press Ctrl+C to stop.
".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port %PORT%
