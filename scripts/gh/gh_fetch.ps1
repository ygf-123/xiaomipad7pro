param(
    [Parameter(Mandatory = $true)][string]$Token,
    [int]$RunId = 0,
    [switch]$Wait
)
$ErrorActionPreference = 'Stop'
$H = @{
    Authorization = "Bearer $Token"
    'User-Agent'  = 'dsh-agent'
    Accept        = 'application/vnd.github+json'
}
$repo = 'ygf-123/buildGKI-6.1.138-android14'
$api = "https://api.github.com/repos/$repo"

if ($RunId -eq 0) {
    $runs = Invoke-RestMethod -Uri "$api/actions/runs?per_page=5" -Headers $H
    $run = $runs.workflow_runs | Where-Object { $_.status -ne 'completed' } | Select-Object -First 1
    if (-not $run) { $run = $runs.workflow_runs | Select-Object -First 1 }
    $RunId = $run.id
}
"watching run id $RunId"

if ($Wait) {
    while ($true) {
        $r = Invoke-RestMethod -Uri "$api/actions/runs/$RunId" -Headers $H
        "{0}  status={1} conclusion={2}" -f (Get-Date -Format 'HH:mm:ss'), $r.status, $r.conclusion
        if ($r.status -eq 'completed') { break }
        Start-Sleep -Seconds 60
    }
}

$r = Invoke-RestMethod -Uri "$api/actions/runs/$RunId" -Headers $H
"final: status=$($r.status) conclusion=$($r.conclusion) head_sha=$($r.head_sha)"

$arts = Invoke-RestMethod -Uri "$api/actions/runs/$RunId/artifacts" -Headers $H
$arts.artifacts | Select-Object name, size_in_bytes, expired | Format-Table -AutoSize | Out-String

$img = $arts.artifacts | Where-Object { $_.name -eq 'Image' -and -not $_.expired }
if ($img) {
    $out = Join-Path $PSScriptRoot 'gki_Image.zip'
    "downloading artifact '$($img.name)' ($($img.size_in_bytes) bytes) ..."
    Invoke-WebRequest -Uri "$api/actions/artifacts/$($img.id)/zip" -Headers $H -OutFile $out
    "saved: $out"
    $sm = $arts.artifacts | Where-Object { $_.name -eq 'System.map' -and -not $_.expired }
    if ($sm) {
        Invoke-WebRequest -Uri "$api/actions/artifacts/$($sm.id)/zip" -Headers $H -OutFile (Join-Path $PSScriptRoot 'gki_System.map.zip')
        "saved: gki_System.map.zip"
    }
    $mods = $arts.artifacts | Where-Object { $_.name -eq 'modules' -and -not $_.expired }
    if ($mods) {
        Invoke-WebRequest -Uri "$api/actions/artifacts/$($mods.id)/zip" -Headers $H -OutFile (Join-Path $PSScriptRoot 'gki_modules.zip')
        "saved: gki_modules.zip"
    }
}
else {
    "no unexpired 'Image' artifact found"
}
