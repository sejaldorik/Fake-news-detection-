Write-Host "Creating Python Virtual Environment..." -ForegroundColor Cyan
python -m venv venv

Write-Host "Activating Virtual Environment..." -ForegroundColor Cyan
.\venv\Scripts\Activate.ps1

Write-Host "Installing Requirements..." -ForegroundColor Cyan
pip install -r requirements.txt

Write-Host "Checking if model is already trained..." -ForegroundColor Cyan
if (!(Test-Path "model.pkl")) {
    Write-Host "Model not found. Starting training process (This may take a few minutes)..." -ForegroundColor Yellow
    python train_model.py
} else {
    Write-Host "Model already trained!" -ForegroundColor Green
}

Write-Host "Starting Flask App..." -ForegroundColor Green
python app.py
