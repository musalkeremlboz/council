# COUNCIL installer for Windows.
#   irm https://raw.githubusercontent.com/musalkeremlboz/council/main/install.ps1 | iex
# Installs into %USERPROFILE%\.council (its own Python environment, no administrator rights), then
# runs `council install`, which starts the service, connects Claude Code, imports the memory you
# already have and turns on automatic updates.

function Install-Council {
    param([string[]]$Options)
    $repo = "musalkeremlboz/council"
    $dir = if ($env:COUNCIL_HOME) { $env:COUNCIL_HOME } else { Join-Path $HOME ".council" }

    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Host "COUNCIL could not be installed: git is not installed (https://git-scm.com/download/win)." -ForegroundColor Red
        return 1
    }
    $python = $null
    foreach ($candidate in @(@("py", "-3"), @("python"), @("python3"))) {
        $exe = $candidate[0]
        $pre = @($candidate | Select-Object -Skip 1)
        if (Get-Command $exe -ErrorAction SilentlyContinue) {
            & $exe @pre -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" *> $null
            if ($LASTEXITCODE -eq 0) { $python = $candidate; break }
        }
    }
    if (-not $python) {
        Write-Host "COUNCIL could not be installed: Python 3.11 or later is needed (https://www.python.org/downloads/)." -ForegroundColor Red
        return 1
    }

    if ($env:COUNCIL_SOURCE) {
        $source = $env:COUNCIL_SOURCE
    } else {
        $tag = "main"
        try {
            $tag = (Invoke-RestMethod "https://api.github.com/repos/$repo/releases/latest" -Headers @{ "User-Agent" = "council-install" }).tag_name
        } catch { }
        $source = "git+https://github.com/$repo@$tag"
    }

    Write-Host "Installing COUNCIL into $dir ..."
    $exe = $python[0]
    $pre = @($python | Select-Object -Skip 1)
    & $exe @pre -m venv (Join-Path $dir "venv")
    $venvPython = Join-Path $dir "venv\Scripts\python.exe"
    & $venvPython -m pip install --quiet --disable-pip-version-check --upgrade $source
    if ($LASTEXITCODE -ne 0) {
        Write-Host "COUNCIL could not be installed: the download failed." -ForegroundColor Red
        return 1
    }
    & $venvPython -m council.cli --data $dir install @Options
    return $LASTEXITCODE
}

$councilExit = Install-Council -Options $args
# Run as a file, report the result to the caller; pasted into a window, leave the window open.
if ($MyInvocation.MyCommand.Path) { exit $councilExit }
