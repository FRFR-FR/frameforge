#requires -Version 5.1
[CmdletBinding()]
param([switch]$SkipAndroid)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$ToolsRoot = Join-Path $env:LOCALAPPDATA "GAMEFORGE/tools"
$AndroidSdk = Join-Path $env:LOCALAPPDATA "Android/Sdk"
$GodotVersion = "4.4.1"
$BlenderVersion = "4.5.16"
$Work = Join-Path $env:TEMP "gameforge-install"
New-Item -ItemType Directory -Force -Path $ToolsRoot, $Work | Out-Null

function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = @($machine, $user, $env:Path) -join ";"
}
function Add-UserPath([string]$PathToAdd) {
    $current = [Environment]::GetEnvironmentVariable("Path", "User")
    $parts = @($current -split ";" | Where-Object { $_ })
    if ($parts -notcontains $PathToAdd) {
        [Environment]::SetEnvironmentVariable("Path", (($parts + $PathToAdd) -join ";"), "User")
    }
}
function Install-WingetPackage([string]$Id) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "Windows Package Manager (winget) is missing. Install Microsoft's App Installer, then rerun."
    }
    Write-Host "Installing package: $Id" -ForegroundColor Cyan
    & winget install --exact --id $Id --silent --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) {
        & winget list --exact --id $Id
        if ($LASTEXITCODE -ne 0) { throw "winget failed to install $Id (exit $LASTEXITCODE)." }
    }
    Refresh-Path
}
function Download-File([string]$Url, [string]$Path) {
    Write-Host "Downloading $Url" -ForegroundColor Cyan
    Invoke-WebRequest -Uri $Url -OutFile $Path -UseBasicParsing
    if (-not (Test-Path $Path) -or (Get-Item $Path).Length -lt 100000) {
        throw "Download was missing or suspiciously small: $Path"
    }
}

Write-Host "GAMEFORGE setup — Windows" -ForegroundColor Green
# 1. Git and Python 3.12.
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Install-WingetPackage "Git.Git" }
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { Install-WingetPackage "Python.Python.3.12" }
$Python = $null
try { $Python = (& py -3.12 -c "import sys; print(sys.executable)" 2>$null).Trim() } catch {}
if (-not $Python -or -not (Test-Path $Python)) {
    Install-WingetPackage "Python.Python.3.12"
    Refresh-Path
    $Python = (& py -3.12 -c "import sys; print(sys.executable)").Trim()
}
if ((& $Python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim() -ne "3.12") {
    throw "Python 3.12 was not found. Install Python 3.12 and rerun."
}

# 2. Blender 4.5 LTS: keep the Blender 4.x API family used by the current builder.
$BlenderMsi = Join-Path $Work "blender-$BlenderVersion-windows-x64.msi"
$BlenderUrl = "https://download.blender.org/release/Blender4.5/blender-$BlenderVersion-windows-x64.msi"
$BlenderCandidates = @(
    "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
    "C:\Program Files\Blender Foundation\Blender $BlenderVersion\blender.exe"
)
$BlenderExe = $BlenderCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $BlenderExe) {
    Download-File $BlenderUrl $BlenderMsi
    $p = Start-Process msiexec.exe -ArgumentList @("/i", $BlenderMsi, "/qn", "/norestart") -Wait -PassThru
    if ($p.ExitCode -notin @(0, 3010)) { throw "Blender installer failed: $($p.ExitCode)" }
    $BlenderExe = $BlenderCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $BlenderExe) { throw "Blender $BlenderVersion installed, but blender.exe was not found." }
$BlenderDir = Split-Path $BlenderExe
if ($env:Path -notlike "*$BlenderDir*") { $env:Path = "$BlenderDir;$env:Path" }
Add-UserPath $BlenderDir

# 3. FFmpeg/FFprobe with libass support.
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue) -or -not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
    Install-WingetPackage "Gyan.FFmpeg"
    Refresh-Path
}
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue) -or -not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
    throw "FFmpeg or FFprobe is not on PATH. Open a new PowerShell terminal and rerun."
}
$FilterList = & ffmpeg -hide_banner -filters 2>&1 | Out-String
if ($FilterList -notmatch "(?m)\bass\s" -or $FilterList -notmatch "(?m)\bsubtitles\s") {
    throw "This FFmpeg build lacks the ASS/libass subtitle filters."
}

# 4. Godot 4.4.1 and matching export templates.
$GodotDir = Join-Path $ToolsRoot "godot-$GodotVersion"
$GodotExe = Join-Path $GodotDir "Godot_v$GodotVersion-stable_win64.exe"
if (-not (Test-Path $GodotExe)) {
    $GodotZip = Join-Path $Work "Godot_v$GodotVersion-stable_win64.exe.zip"
    Download-File "https://github.com/godotengine/godot/releases/download/$GodotVersion-stable/Godot_v$GodotVersion-stable_win64.exe.zip" $GodotZip
    New-Item -ItemType Directory -Force -Path $GodotDir | Out-Null
    Expand-Archive -Path $GodotZip -DestinationPath $GodotDir -Force
}
if (-not (Test-Path $GodotExe)) { throw "Godot 4.4.1 executable was not found after extraction." }
if ($env:Path -notlike "*$GodotDir*") { $env:Path = "$GodotDir;$env:Path" }
Add-UserPath $GodotDir
$TemplateRoot = Join-Path $env:APPDATA "Godot/export_templates/$GodotVersion.stable"
if (-not (Test-Path (Join-Path $TemplateRoot "android_debug.apk"))) {
    $TemplateZip = Join-Path $Work "Godot_v$GodotVersion-stable_export_templates.zip"
    Download-File "https://github.com/godotengine/godot/releases/download/$GodotVersion-stable/Godot_v$GodotVersion-stable_export_templates.tpz" $TemplateZip
    $TemplateTemp = Join-Path $Work "godot-templates"
    if (Test-Path $TemplateTemp) { Remove-Item $TemplateTemp -Recurse -Force }
    Expand-Archive -Path $TemplateZip -DestinationPath $TemplateTemp -Force
    $TemplateSource = Join-Path $TemplateTemp "templates"
    if (-not (Test-Path $TemplateSource)) { $TemplateSource = $TemplateTemp }
    New-Item -ItemType Directory -Force -Path $TemplateRoot | Out-Null
    Copy-Item -Path (Join-Path $TemplateSource "*") -Destination $TemplateRoot -Recurse -Force
    Set-Content -Path (Join-Path $TemplateRoot "version.txt") -Value "$GodotVersion.stable" -Encoding ASCII
}
$env:GAMEFORGE_GODOT = $GodotExe
[Environment]::SetEnvironmentVariable("GAMEFORGE_GODOT", $GodotExe, "User")

# 5. OpenJDK 17 and Android SDK command-line tools.
if (-not $SkipAndroid) {
    Install-WingetPackage "EclipseAdoptium.Temurin.17.JDK"
    $Jdk = Get-ChildItem "C:\Program Files\Eclipse Adoptium" -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "jdk-17*" } | Sort-Object Name -Descending | Select-Object -First 1
    if (-not $Jdk) { throw "Temurin JDK 17 was installed but its directory was not located." }
    $env:JAVA_HOME = $Jdk.FullName
    $env:Path = (Join-Path $Jdk.FullName "bin") + ";" + $env:Path
    [Environment]::SetEnvironmentVariable("JAVA_HOME", $Jdk.FullName, "User")

    $CmdToolsZip = Join-Path $Work "commandlinetools-win-15859902_latest.zip"
    Download-File "https://dl.google.com/android/repository/commandlinetools-win-15859902_latest.zip" $CmdToolsZip
    $ExpectedHash = "90ae805d20434428bffcb699c290860f19bb5f66a67e6b330067e3de801fb04a"
    $ActualHash = (Get-FileHash -Algorithm SHA256 $CmdToolsZip).Hash.ToLowerInvariant()
    if ($ActualHash -ne $ExpectedHash) { throw "Android command-line tools checksum mismatch." }

    $AndroidLatest = Join-Path $AndroidSdk "cmdline-tools/latest"
    New-Item -ItemType Directory -Force -Path $AndroidLatest | Out-Null
    $CmdTemp = Join-Path $Work "android-cmdline-tools"
    if (Test-Path $CmdTemp) { Remove-Item $CmdTemp -Recurse -Force }
    Expand-Archive -Path $CmdToolsZip -DestinationPath $CmdTemp -Force
    Copy-Item -Path (Join-Path $CmdTemp "cmdline-tools/*") -Destination $AndroidLatest -Recurse -Force
    $SdkManager = Join-Path $AndroidLatest "bin/sdkmanager.bat"
    if (-not (Test-Path $SdkManager)) { throw "Android sdkmanager.bat was not found." }
    $env:ANDROID_HOME = $AndroidSdk
    $env:ANDROID_SDK_ROOT = $AndroidSdk
    [Environment]::SetEnvironmentVariable("ANDROID_HOME", $AndroidSdk, "User")
    [Environment]::SetEnvironmentVariable("ANDROID_SDK_ROOT", $AndroidSdk, "User")

    Write-Host "Accepting Android SDK licence agreements..." -ForegroundColor Cyan
    1..40 | ForEach-Object { "y" } | & $SdkManager "--sdk_root=$AndroidSdk" --licenses
    if ($LASTEXITCODE -ne 0) { throw "Android SDK licence acceptance failed." }
    & $SdkManager "--sdk_root=$AndroidSdk" --install "platform-tools" "build-tools;34.0.0" "platforms;android-34" "cmdline-tools;latest" "cmake;3.10.2.4988404" "ndk;23.2.8568313"
    if ($LASTEXITCODE -ne 0) { throw "Android SDK package installation failed." }
    $env:Path = (Join-Path $AndroidLatest "bin") + ";" + (Join-Path $AndroidSdk "platform-tools") + ";" + $env:Path
}

# 6. Python dependencies: Pocket TTS followed by WhisperX forced alignment.
$Venv = Join-Path $RepoRoot ".venv"
if (-not (Test-Path (Join-Path $Venv "Scripts/python.exe"))) {
    & $Python -m venv $Venv
    if ($LASTEXITCODE -ne 0) { throw "Could not create the GAMEFORGE Python virtual environment." }
}
$VenvPython = Join-Path $Venv "Scripts/python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r (Join-Path $RepoRoot "gameforge/cutscenes/requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Pocket TTS or cutscene Python dependencies failed to install." }
& $VenvPython -m pip install whisperx
if ($LASTEXITCODE -ne 0) { throw "WhisperX installation failed." }
& $VenvPython -m pip check
if ($LASTEXITCODE -ne 0) { throw "Python dependency consistency check failed." }

# Optional first-run model downloads. Explicitly require the user to confirm that
# they have reviewed and accepted the Kyutai model and voice-specific license terms.
$ModelConsent = Read-Host "Have you reviewed and accepted the Kyutai model/voice terms? Type YES to download TTS weights, all nine voices and the WhisperX aligner now"
if ($ModelConsent -ceq "YES") {
    & $VenvPython (Join-Path $RepoRoot "setup/fetch_models.py")
    if ($LASTEXITCODE -ne 0) { throw "Model prefetch failed; check model access and Hugging Face terms." }
} else {
    Write-Host "Model weights not downloaded yet. Run .venv\\Scripts\\python.exe setup\\fetch_models.py after accepting the model/voice terms." -ForegroundColor Yellow
}

# 7. Final installation verification.
$DoctorArgs = @((Join-Path $RepoRoot "setup/verify_install.py"), "--python", $VenvPython, "--blender", $BlenderExe, "--godot", $GodotExe)
if (-not $SkipAndroid) { $DoctorArgs += @("--android-sdk", $AndroidSdk) }
& $VenvPython @DoctorArgs
if ($LASTEXITCODE -ne 0) { throw "GAMEFORGE verification found missing components." }

Write-Host ""
Write-Host "GAMEFORGE toolchain installation completed." -ForegroundColor Green
if (-not $SkipAndroid) {
    Write-Host "Open Godot and configure Editor Settings > Export > Android:" -ForegroundColor Yellow
    Write-Host "  Java SDK: $($env:JAVA_HOME)"
    Write-Host "  Android SDK: $AndroidSdk"
}
Write-Host "TTS and alignment model weights download on first use; check model terms before the first run."
