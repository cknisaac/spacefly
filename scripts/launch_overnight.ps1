param([switch]$StartTraining)

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$env:PYTHONPATH = (Join-Path $projectRoot 'src')
if (-not $StartTraining) {
    Push-Location $projectRoot
    try {
        python -m scripts.overnight_synthetic
    } finally {
        Pop-Location
    }
    exit $LASTEXITCODE
}

$outputDir = Join-Path $projectRoot 'docs/figures/overnight_synthetic'
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
$pythonExe = (Get-Command python).Source
$process = Start-Process -FilePath $pythonExe `
    -ArgumentList @('-m', 'scripts.overnight_synthetic', '--start-training') `
    -WorkingDirectory $projectRoot -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $outputDir 'stdout.log') `
    -RedirectStandardError (Join-Path $outputDir 'stderr.log') -PassThru
Write-Output "Started synthetic training process PID $($process.Id). Progress: $(Join-Path $outputDir 'status.json')"
