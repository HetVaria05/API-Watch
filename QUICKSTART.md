# Quick Start – APIWatch

## Setup and Run (copy-paste these commands)

```powershell
# 1. Navigate to the project
cd "d:\API Testing & Monitoring Tool\apiwatch"

# 2. Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 in your browser.

## Run Tests

```powershell
cd "d:\API Testing & Monitoring Tool\apiwatch"
.\venv\Scripts\Activate.ps1
pytest -v
```
