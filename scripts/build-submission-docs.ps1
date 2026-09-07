<#
    Renders the submission markdown to HTML and PDF.

    The markdown is the source of truth. HTML and PDF are generated from it,
    never edited by hand, so there is no chance of three versions of a document
    disagreeing the night before a submission.

    Needs pandoc for markdown to HTML, and Microsoft Edge (already on every
    Windows machine) in headless mode for HTML to PDF. Edge rather than a
    separate PDF tool because it is the same engine that renders the HTML, so
    what prints is what you previewed.

    Usage:  pwsh scripts/build-submission-docs.ps1
#>

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$css = Join-Path $repo "scripts/docs.css"

$targets = @(
    "docs/s3-lab-work/01-lab-work-submission.md",
    "docs/s3-lab-work/02-lab-work-speaking-script.md",
    "docs/s3-working-demo/01-working-demo-runbook.md",
    "docs/s3-working-demo/02-working-demo-speaking-script.md",
    "docs/non-functional-requirements.md"
)

# Edge lives in one of two places depending on how Windows was installed.
$edge = @(
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not (Get-Command pandoc -ErrorAction SilentlyContinue)) {
    throw "pandoc not found. Install it from pandoc.org, then re-run."
}

foreach ($rel in $targets) {
    $md = Join-Path $repo $rel
    if (-not (Test-Path $md)) {
        Write-Warning "skipped, not found: $rel"
        continue
    }

    $html = [IO.Path]::ChangeExtension($md, ".html")
    $pdf = [IO.Path]::ChangeExtension($md, ".pdf")
    $title = (Get-Item $md).BaseName

    # --embed-resources so the HTML is one self-contained file that survives
    # being emailed or copied onto a pen drive without its stylesheet.
    pandoc $md `
        --standalone `
        --embed-resources `
        --css $css `
        --metadata title="$title" `
        --from gfm `
        --to html5 `
        --output $html
    Write-Output "html  $rel"

    if ($edge) {
        # Edge refuses to overwrite silently in some versions, so clear first.
        if (Test-Path $pdf) { Remove-Item $pdf -Force }
        $uri = ([Uri](Resolve-Path $html).Path).AbsoluteUri
        # Start-Process rather than calling Edge directly: headless Edge writes
        # harmless GPU and task-manager warnings to stderr, and PowerShell
        # turns any native stderr into a terminating error under
        # ErrorActionPreference = Stop. Redirecting them to a file keeps a
        # cosmetic warning from failing the whole build.
        $noise = Join-Path $env:TEMP "revix-edge-$([guid]::NewGuid()).log"
        Start-Process -FilePath $edge -Wait -NoNewWindow `
            -RedirectStandardError $noise `
            -ArgumentList @(
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            "--print-to-pdf=$pdf",
            $uri
        )
        Remove-Item $noise -Force -ErrorAction SilentlyContinue

        # Headless Edge can return before the file is flushed.
        $waited = 0
        while (-not (Test-Path $pdf) -and $waited -lt 30) {
            Start-Sleep -Milliseconds 500
            $waited++
        }
        if (Test-Path $pdf) {
            Write-Output "pdf   $rel"
        }
        else {
            Write-Warning "pdf failed for $rel; open the HTML and print to PDF"
        }
    }
    else {
        Write-Warning "Edge not found; open the HTML and print to PDF manually"
    }
}

Write-Output ""
Write-Output "Done. The markdown is the source; regenerate rather than editing the HTML or PDF."
