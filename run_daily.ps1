$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

Write-Host ""[1/8] fetch""      ; python scripts/fetch.py
Write-Host ""[2/8] indicators"" ; python scripts/indicators.py
Write-Host ""[3/8] regime""     ; python scripts/regime.py
Write-Host ""[4/8] screen""     ; python scripts/screen.py
Write-Host ""[5/8] verify""     ; python scripts/verify.py
Write-Host ""[6/8] track""      ; python scripts/track.py
Write-Host ""[7/8] render""     ; python scripts/render.py
Write-Host ""[8/8] notify""     ; python scripts/notify.py
Write-Host ""done.""
