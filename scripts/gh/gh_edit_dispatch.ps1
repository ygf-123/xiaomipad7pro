param(
    [Parameter(Mandatory = $true)][string]$Token
)
$ErrorActionPreference = 'Stop'
$H = @{
    Authorization = "Bearer $Token"
    'User-Agent'  = 'dsh-agent'
    Accept        = 'application/vnd.github+json'
}
$repo = 'ygf-123/buildGKI-6.1.138-android14'
$api = "https://api.github.com/repos/$repo"

"=== 0. auth check ==="
$me = Invoke-RestMethod -Uri 'https://api.github.com/user' -Headers $H
"authenticated as: $($me.login)"

"=== 1. current workflow ==="
$f = Invoke-RestMethod -Uri "$api/contents/.github/workflows/build.yaml" -Headers $H
$txt = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($f.content))
($txt -split "`n" | Where-Object { $_ -match 'repo init' }) | ForEach-Object { $_.Trim() }

"=== 2. switch branch to android14-6.1-2025-06 (6.1.138) ==="
$new = $txt -replace 'common-android14-6\.1-2025-07', 'common-android14-6.1-2025-06'
if ($new -ne $txt) {
    $body = @{
        message = 'build: switch GKI branch to android14-6.1-2025-06 (6.1.138) to match firmware GKI modules'
        content = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($new))
        sha     = $f.sha
        branch  = 'main'
    } | ConvertTo-Json
    $res = Invoke-RestMethod -Method Put -Uri "$api/contents/.github/workflows/build.yaml" -Headers $H -Body $body -ContentType 'application/json'
    "committed: $($res.commit.sha)"
}
else {
    "no change needed (already 2025-06 or pattern not found)"
}

"=== 3. verify fragment still has namespaces ==="
try {
    $fr = Invoke-RestMethod -Uri "$api/contents/droidspaces_requires.fragment" -Headers $H
    $ftxt = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($fr.content))
    ($ftxt -split "`n" | Where-Object { $_ -match 'NS|SYSVIPC|DEVTMPFS' }) | ForEach-Object { $_.Trim() }
}
catch { "fragment read failed: $($_.Exception.Message)" }

"=== 4. dispatch build ==="
$dispatch = @{
    ref    = 'main'
    inputs = @{
        remove_abi_gki_protected_exports = 'false'
        lto                              = 'none'
        kernel_configuration             = 'true'
        patch                            = 'true'
        patch_file                       = '001.GKI-below-6.12-fix_sysvipc_kabi_6_7_8.patch'
    }
} | ConvertTo-Json -Depth 5
Invoke-RestMethod -Method Post -Uri "$api/actions/workflows/build.yaml/dispatches" -Headers $H -Body $dispatch -ContentType 'application/json'
"dispatched OK"
Start-Sleep -Seconds 25
$runs = Invoke-RestMethod -Uri "$api/actions/runs?per_page=3" -Headers $H
$runs.workflow_runs | Select-Object run_number, id, status, conclusion, head_sha | Format-Table -AutoSize | Out-String
