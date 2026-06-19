# Yeti-Tracker Bootstrap Guide

Follow these instructions to provision the local environment and launch the Gamified Yeti-Tracker dashboard.

## 1. Environment Initialization
Ensure you have Python 3.11+ installed.
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Secrets Management (12-Factor App)
The application relies on the Groq API for both the frictionless Text Ingestion and the secondary Yeti Advisor.
1. Create the secrets directory: `mkdir .secrets`
2. Create the file: `echo "" > .secrets\.env`
3. Add your key: `GROQ_API_KEY=gsk_your_key_here`

## 3. Verify Static Assets
Ensure that the Gamification assets were successfully generated and exist:
- `data/assets/tier2.jpg`
- `data/assets/tier3.jpg`

## 4. Run the Dashboard
Execute the convenience batch script to launch Streamlit:
```powershell
.\run_server.bat
```

## 5. Automated Testing Validation
Before pushing any changes, enforce the SRE SOP by running:
```powershell
.\venv\Scripts\ruff check .
.\venv\Scripts\pytest tests\ -v
```
