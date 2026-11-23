$ErrorActionPreference='Stop'
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$python='D:\REMIX_AUTO_ALIGN_V6_DEV\.venv-v8150-build\Scripts\python.exe'
$inno=Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'
$checks=[ordered]@{
  SOURCE_MANIFEST=(Test-Path (Join-Path $root 'RELEASE_SOURCE_MANIFEST.sha256'))
  BUILD_PYTHON=$false
  PYINSTALLER=$false
  INNO_SETUP=(Test-Path $inno)
  CODE_SIGNING_CERT=(@(Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert -ErrorAction SilentlyContinue).Count -gt 0)
  CLEAN_VM=((Get-Command Get-VM -ErrorAction SilentlyContinue) -or
            (Get-Command VBoxManage.exe -ErrorAction SilentlyContinue) -or
            (Get-Command vmrun.exe -ErrorAction SilentlyContinue))
}
if(Test-Path $python){
  & $python -c "raise SystemExit(0)" 2>$null
  $checks.BUILD_PYTHON=($LASTEXITCODE -eq 0)
}
if($checks.BUILD_PYTHON){
  & $python -c "import PyInstaller" 2>$null
  $checks.PYINSTALLER=($LASTEXITCODE -eq 0)
  & $python -c "from remix_duo.licensing.online import configured; raise SystemExit(0 if configured() else 25)"
  $checks.CLOUD_LICENSE=($LASTEXITCODE -eq 0)
} else {$checks.CLOUD_LICENSE=$false}
$checks.GetEnumerator() | ForEach-Object { Write-Output ("{0}={1}" -f $_.Key,$_.Value) }
if($checks.Values -contains $false){exit 2}
