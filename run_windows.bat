@echo off
setlocal enabledelayedexpansion

rem Set environment variables
set DATABASE_URL=postgresql://sahdude:CS467@209.46.124.94:5432/postgres
set RABBITMQ_URL=amqp://guest:guest@209.46.124.94:5672/
set POSTGRES_USER=sahdude
set POSTGRES_PASSWORD=CS467
set POSTGRES_HOST=209.46.124.94
set POSTGRES_PORT=5432
set POSTGRES_DB=postgres
set JWT_SECRET_KEY=your-secret-key-here

rem Add more environment variables as needed

rem Get service name from command line
set SERVICE=%1

rem Activate virtual environment
call %~dp0venv\Scripts\activate.bat

rem Set PYTHONPATH
set PYTHONPATH=%~dp0;%PYTHONPATH%

rem Start service with START command
cd %~dp0services\%SERVICE%
start /B python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info > logs\%SERVICE%.log 2>&1

echo %SERVICE% service started in background