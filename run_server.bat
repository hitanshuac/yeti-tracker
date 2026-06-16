@echo off
echo Starting Yeti-Tracker FastAPI Server...

IF EXIST "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) ELSE (
    echo Virtual environment not found at venv\. Proceeding with global python...
)

echo.
echo Running Streamlit...
venv\Scripts\python.exe -m streamlit run app.py

pause
