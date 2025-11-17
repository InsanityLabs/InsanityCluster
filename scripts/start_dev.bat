@echo off
REM Development startup script for Insanity Cluster with Dashboard (Windows)

echo ========================================
echo Starting Insanity Cluster Development
echo ========================================

REM Check if docker-compose is available
where docker-compose >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] docker-compose not found. Please install Docker Desktop.
    exit /b 1
)

REM Check if node is available
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js not found. Please install Node.js 20+.
    exit /b 1
)

REM Start infrastructure services
echo.
echo [INFO] Starting infrastructure services...
docker-compose up -d postgres redis qdrant

REM Wait for services
echo [INFO] Waiting for services to be ready...
timeout /t 5 /nobreak >nul

REM Check if virtual environment exists
if not exist "venv\" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo [INFO] Activating Python virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies if needed
if not exist "venv\.installed" (
    echo [INFO] Installing Python dependencies...
    pip install -r requirements.txt
    echo. > venv\.installed
)

REM Run database migrations
echo [INFO] Running database migrations...
alembic upgrade head

REM Start backend API server
echo.
echo [SUCCESS] Starting backend API server on http://localhost:8000
start "Insanity Cluster API" cmd /k "venv\Scripts\activate.bat && python -m insanity_cluster.surface.main"

REM Wait for backend to start
timeout /t 3 /nobreak >nul

REM Start dashboard dev server
echo [SUCCESS] Starting dashboard dev server on http://localhost:5173
start "Insanity Cluster Dashboard" cmd /k "cd dashboard && npm run dev"

echo.
echo ========================================
echo Development environment is ready!
echo ========================================
echo Backend API:  http://localhost:8000
echo Dashboard:    http://localhost:5173
echo Grafana:      http://localhost:3000 (admin/admin)
echo Prometheus:   http://localhost:9090
echo.
echo Press any key to stop all services...
pause >nul

REM Cleanup
echo.
echo [INFO] Stopping services...
docker-compose down
taskkill /FI "WINDOWTITLE eq Insanity Cluster API*" /F >nul 2>nul
taskkill /FI "WINDOWTITLE eq Insanity Cluster Dashboard*" /F >nul 2>nul
echo [SUCCESS] All services stopped
