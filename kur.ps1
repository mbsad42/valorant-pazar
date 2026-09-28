# Kurulum: bağımlılıkları yükler, Telegram'ı dener, her gece 03:07'de çalışacak Windows görevini oluşturur.
# Çalıştırma: kur.bat'a çift tıkla.
$ErrorActionPreference = "Stop"
$dir = $PSScriptRoot
Set-Location $dir

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py -or $py -like "*WindowsApps*") { $py = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" }
if (-not (Test-Path $py)) { Write-Host "Python bulunamadı."; exit 1 }

if (-not (Test-Path "$dir\config.env")) {
    Copy-Item "$dir\config.env.example" "$dir\config.env"
    Write-Host "config.env oluşturuldu. Açılan dosyayı doldurup kaydet, sonra kur.bat'ı tekrar çalıştır."
    Start-Process notepad "$dir\config.env"
    exit 0
}

Write-Host "Bağımlılıklar yükleniyor..."
& $py -m pip install -q -r requirements.txt

Write-Host "Telegram deneniyor..."
& $py -m valstore --test-notify
if ($LASTEXITCODE -ne 0) { Write-Host "Telegram çalışmadı. config.env'deki TELEGRAM_TOKEN ve TELEGRAM_CHAT_ID'yi kontrol et."; exit 1 }

$arg = "-NoProfile -WindowStyle Hidden -Command `"Set-Location '$dir'; & '$py' -m valstore *>> pazar-log.txt`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg
$triggers = @((New-ScheduledTaskTrigger -Daily -At 03:07), (New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME))
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -RunOnlyIfNetworkAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5)
Register-ScheduledTask -TaskName "ValorantPazar" -Action $action -Trigger $triggers -Settings $settings -Force | Out-Null
Write-Host "Görev oluşturuldu: her gün 03:07 ve her oturum açılışında çalışır."

Write-Host "Pazar şimdi bir kez çekiliyor..."
& $py -m valstore --force
Write-Host "Bitti."
