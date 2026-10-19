# Start Studio locally: database, API, worker and website, each in its own window.
# Usage (from D:\studio):  powershell -ExecutionPolicy Bypass -File .\dev.ps1
$root = $PSScriptRoot

Write-Host "Starting Postgres (Docker Desktop must be running)..."
docker compose -f "$root\docker-compose.yml" up -d --wait db
if ($LASTEXITCODE -ne 0) { Write-Host "Docker is not running. Open Docker Desktop and try again."; exit 1 }

Push-Location "$root\api"
uv run python -m app.migrate
Pop-Location

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\api'; `$host.UI.RawUI.WindowTitle='Studio API'; uv run uvicorn app.main:app --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\api'; `$host.UI.RawUI.WindowTitle='Studio worker'; uv run python -m app.worker"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\web'; `$host.UI.RawUI.WindowTitle='Studio web'; npm run dev"

Write-Host ""
Write-Host "Studio is starting. In about 10 seconds open:"
Write-Host "  Website:  http://localhost:3000"
Write-Host "  App:      http://localhost:3000/app   (Sign in as developer)"
Write-Host "  API docs: http://localhost:8000/docs"
Write-Host "Close the three windows to stop."
