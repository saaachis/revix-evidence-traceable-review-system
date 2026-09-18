<#
    Regenerates the quality reports into build/reports/.

    These are committed and published to Pages, because GitHub shows an HTML
    file as source rather than as a page, and a coverage report nobody can
    click through is a coverage report nobody opens.

    Two of the six tools produce a browsable report. Ruff and Xenon
    deliberately produce none: a gate's answer is pass or fail and the build
    already carries it.

    Usage:  pwsh scripts/build-reports.ps1
#>

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$out = Join-Path $repo "build/reports"

Write-Output "== coverage =="
uv run pytest --cov --cov-report="html:$out/coverage" --cov-report=term |
    Select-Object -Last 3

# coverage.py writes a .gitignore containing "*" into its own output
# directory, which silently excludes the whole report from the repository.
# Removing it is the difference between these being committed and being
# mysteriously absent.
$selfIgnore = Join-Path $out "coverage/.gitignore"
if (Test-Path $selfIgnore) {
    Remove-Item $selfIgnore -Force
    Write-Output "   removed coverage's own .gitignore"
}

Write-Output "== type precision =="
# --html-report needs lxml, which is in the dev group for exactly this.
uv run mypy packages/revix_core/src pipeline/src apps/api/src `
    --html-report "$out/typing" --txt-report "$out/typing" | Select-Object -Last 1

Write-Output "== machine-readable exports =="
uv run radon cc packages/revix_core/src pipeline/src apps/api/src -j |
    Out-File -Encoding utf8 (Join-Path $out "complexity.json")
uv run radon mi packages/revix_core/src pipeline/src apps/api/src -j |
    Out-File -Encoding utf8 (Join-Path $out "maintainability.json")
Write-Output "   complexity.json, maintainability.json"

Write-Output ""
Write-Output "Done. build/reports/index.html links them; Pages serves them at /reports/."
