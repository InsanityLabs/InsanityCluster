@echo off
REM Quick start script for dashboard development (Windows)

echo ======================================
echo Starting Insanity Cluster Dashboard
echo ======================================

REM Check if node is available
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js not found. Please install Node.js 20+
    exit /b 1
)

REM Check if dashboard dependencies are installed
if not exist "dashboard\node_modules\" (
    echo [INFO] Installing dashboard dependencies...
    cd dashboard
    call npm install
    cd ..
)

REM Start the dashboard
echo.
echo [SUCCESS] Starting dashboard on http://localhost:5173
echo.
echo Note: Make sure the backend API is running on http://localhost:8000
echo       You can start it with: python -m insanity_cluster.surface.main
echo.

cd dashboard
npm run dev
