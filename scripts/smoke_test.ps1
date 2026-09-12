param(
  [Parameter(Mandatory=$true)][string]$ApiUrl,
  [Parameter(Mandatory=$true)][string]$ApiKey
)
$ErrorActionPreference = 'Stop'
$requestId = 'smoke-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
$body = @{ request_id = $requestId; message = 'Busco comprar una casa de tres recámaras en Guadalajara.' } | ConvertTo-Json
Write-Host '1/3 unauthorized boundary (expect 401)'
try {
  Invoke-RestMethod -Method Post -Uri $ApiUrl -ContentType 'application/json' -Body $body | Out-Null
  throw 'Expected 401 but request succeeded.'
} catch {
  if ($_.Exception.Response.StatusCode.value__ -ne 401) { throw }
}
Write-Host '2/3 authorized inference (expect cached=false)'
$first = Invoke-RestMethod -Method Post -Uri $ApiUrl -ContentType 'application/json' -Headers @{ 'x-eai-key' = $ApiKey } -Body $body
if ($first.cached -ne $false) { throw 'First request should not be cached.' }
Write-Host '3/3 idempotent replay (expect cached=true)'
$second = Invoke-RestMethod -Method Post -Uri $ApiUrl -ContentType 'application/json' -Headers @{ 'x-eai-key' = $ApiKey } -Body $body
if ($second.cached -ne $true) { throw 'Second request should be cached.' }
Write-Host 'SMOKE PASS' -ForegroundColor Green
