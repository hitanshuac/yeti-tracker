@echo off
echo Starting Yeti-Tracker FastAPI Server...

IF EXIST "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) ELSE (
    echo Virtual environment not found at venv\. Proceeding with global python...
)

echo.
echo Running Uvicorn...
python -m uvicorn src.main:app --reload

pause
