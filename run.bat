@echo off
echo ========================================
echo   Manhwa Recap Video Generator
echo ========================================
echo.

:: Activate virtual environment
call venv\Scripts\activate

:: Start the server
echo Starting server at http://localhost:8000
echo.
echo Open your browser and go to: http://localhost:8000/app
echo Press Ctrl+C to stop the server
echo.

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
