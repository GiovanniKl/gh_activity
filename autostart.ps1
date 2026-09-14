Set-Location "$PSScriptRoot\backend"

.\venv\Scripts\activate

$serverUrl = "http://127.0.0.1:8000"

# Open the browser a couple seconds after uvicorn starts, in the background,
# without blocking or closing the main window.
Start-Job -ScriptBlock {
    param($url)
    Start-Sleep -Seconds 2
    Start-Process $url
} -ArgumentList $serverUrl | Out-Null

Write-Host "Starting server at $serverUrl - press Ctrl+C to stop." -ForegroundColor Cyan

uvicorn app.main:app --host 127.0.0.1 --port 8000

Write-Host "Server stopped."
Read-Host "Press Enter to close this window"
