# Test Google Calendar Connection Locally
# Run this script to test the Google Calendar connection

Write-Host "🧪 Testing Google Calendar Connection..." -ForegroundColor Cyan
Write-Host ""

# Check if backend is running
Write-Host "1. Checking if backend is running..." -ForegroundColor Yellow
try {
    $healthCheck = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET -TimeoutSec 5
    if ($healthCheck.StatusCode -eq 200) {
        Write-Host "   ✅ Backend is running" -ForegroundColor Green
    }
} catch {
    Write-Host "   ❌ Backend is NOT running. Please run: docker compose up" -ForegroundColor Red
    exit 1
}

# Check Google status
Write-Host ""
Write-Host "2. Checking Google connection status..." -ForegroundColor Yellow
try {
    $statusResponse = Invoke-WebRequest -Uri "http://localhost:8000/socialanywhere/google/status" -Method GET
    $statusData = $statusResponse.Content | ConvertFrom-Json
    if ($statusData.connected) {
        Write-Host "   ✅ Google is already connected!" -ForegroundColor Green
        Write-Host "   You can now use Google Calendar features." -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Google is not connected yet" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "3. Testing Google connect endpoint..." -ForegroundColor Yellow
        try {
            $connectResponse = Invoke-WebRequest -Uri "http://localhost:8000/socialanywhere/google/connect" -Method GET -MaximumRedirection 0 -ErrorAction SilentlyContinue
        } catch {
            if ($_.Exception.Response.StatusCode -eq 302 -or $_.Exception.Response.StatusCode.value__ -eq 302) {
                $location = $_.Exception.Response.Headers.Location
                Write-Host "   ✅ Connect endpoint is working!" -ForegroundColor Green
                Write-Host "   📍 Redirect URL: $location" -ForegroundColor Cyan
                
                if ($location -like "*accounts.google.com*") {
                    Write-Host "   ✅ Redirecting to Google (correct!)" -ForegroundColor Green
                    Write-Host ""
                    Write-Host "🌐 Opening Google OAuth in browser..." -ForegroundColor Cyan
                    Start-Process $location
                } else {
                    Write-Host "   ❌ ERROR: Redirect URL is wrong! Should go to accounts.google.com" -ForegroundColor Red
                    Write-Host "   Current redirect: $location" -ForegroundColor Red
                }
            } else {
                Write-Host "   ❌ Error: $($_.Exception.Message)" -ForegroundColor Red
            }
        }
    }
} catch {
    Write-Host "   ❌ Error checking status: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "📝 Next steps:" -ForegroundColor Cyan
Write-Host "   1. If Google OAuth opened in browser, complete the consent" -ForegroundColor White
Write-Host "   2. You'll be redirected back to: http://localhost:8000/socialanywhere/oauth/callback" -ForegroundColor White
Write-Host "   3. After that, Google Calendar will be connected!" -ForegroundColor White
Write-Host ""




