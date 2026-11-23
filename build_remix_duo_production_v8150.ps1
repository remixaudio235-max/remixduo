# RemiX Duo 8.150 production Windows build. No QA runtime/license override.
$ErrorActionPreference = 'Stop'
$env:PYTHONNOUSERSITE = '1'
$source = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = 'D:\REMIX_AUTO_ALIGN_V6_DEV\.venv-v8150-build\Scripts\python.exe'
$inno = Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'
if (!(Test-Path $python)) { throw 'MISSING_BUILD_PYTHON' }
if (!(Test-Path $inno)) { throw 'MISSING_INNO_SETUP' }
if (!(Test-Path (Join-Path $source 'RELEASE_SOURCE_MANIFEST.sha256'))) {
    throw 'MISSING_RELEASE_SOURCE_MANIFEST'
}
$env:PATH = @((Split-Path -Parent $python),"$env:SystemRoot\System32",
              $env:SystemRoot,(Split-Path -Parent $inno)) -join ';'
Set-Location $source
$cythonLib=Join-Path $source 'build\cython_lib'
$cythonTemp=Join-Path $source 'build\cython_temp'
& $python (Join-Path $source 'build_cython_protected_v8154.py') `
  --output $cythonLib --temp $cythonTemp
if ($LASTEXITCODE -ne 0) { throw 'CYTHON_PROTECTED_BUILD_FAILED' }
$cythonManifest=Join-Path $cythonLib 'CYTHON_PROTECTED_MANIFEST.json'
if (!(Test-Path $cythonManifest)) { throw 'MISSING_CYTHON_PROTECTED_MANIFEST' }
$cythonHiddenImports=Join-Path $cythonLib 'CYTHON_HIDDEN_IMPORTS.txt'
if (!(Test-Path $cythonHiddenImports)) { throw 'MISSING_CYTHON_HIDDEN_IMPORTS' }

# Commercial builds must fail before PyInstaller when the pinned V3/V4 online
# endpoint/key pair is not configured. Never fall back to the QA license.
& $python -c "from remix_duo.licensing.online import configured; raise SystemExit(0 if configured() else 25)"
if ($LASTEXITCODE -ne 0) { throw 'PRODUCTION_ONLINE_LICENSE_NOT_CONFIGURED' }

function Run-PyInstaller([string[]]$Arguments) {
    & $python -m PyInstaller @Arguments
    if ($LASTEXITCODE -ne 0) { throw "PYINSTALLER_FAILED: $LASTEXITCODE" }
}

$cythonBinaryArgs = @()
Get-ChildItem -LiteralPath $cythonLib -Recurse -Filter '*.pyd' | ForEach-Object {
    $relative = $_.FullName.Substring($cythonLib.Length).TrimStart('\')
    $destination = Split-Path -Parent $relative
    if ([string]::IsNullOrWhiteSpace($destination)) { $destination = '.' }
    $cythonBinaryArgs += '--add-binary'
    $cythonBinaryArgs += ($_.FullName + ';' + $destination)
}
if ($cythonBinaryArgs.Count -lt 2) { throw 'NO_CYTHON_BINARIES' }
$cythonImportArgs = @()
Get-Content -LiteralPath $cythonHiddenImports | Where-Object { $_.Trim() } | ForEach-Object {
    $cythonImportArgs += '--hidden-import'
    $cythonImportArgs += $_.Trim()
}

$mainArguments = @(
  '--noconfirm','--clean','--onedir','--windowed','--name','RemiXDuo',
  '--icon',"$source\remixduo_app.ico",
  '--add-binary',"D:\REMIX_AUTO_ALIGN_V6_DEV\.venv-v8150-build\Lib\site-packages\PyQt6\Qt6\bin\Qt6*.dll;PyQt6",
  '--distpath',"$source\dist",'--workpath',"$source\build\main",
  '--specpath',"$source\build\specs",'--paths',$cythonLib,
  '--paths',$source,'--paths',"$source\src",
  '--collect-data','remix_duo',
  '--add-data',"$source\src\remix_duo\resources;remix_duo/resources",
  '--runtime-hook',"$source\production_runtime_hook_v8150.py",
  '--add-data',"$source\remix_dou_swirl_toolbar32.png;.",
  '--add-data',"$source\remix_activation_logo.jpg;.",
  '--add-data',"$source\V812_MAG_TITLE_TEMPLATE.png;.",
  '--add-data',"$source\V812_PHASE_TITLE_TEMPLATE.png;.",
  '--add-data',"$source\smaart_title_signatures_v03.npz;.",
  '--add-data',"$cythonManifest;.",
  '--hidden-import','remix_duo_online_license_v878',
  '--hidden-import','_remixduo_native',
  '--hidden-import','remix_duo.licensing.gate',
  '--hidden-import','remix_duo.licensing.online',
  '--hidden-import','remix_duo.update.github_release',
  '--hidden-import','win32timezone','--hidden-import','pythoncom',
  '--hidden-import','pywintypes','--hidden-import','pywinauto.controls.uiawrapper',
  '--exclude-module','torch','--exclude-module','tensorflow',
  '--exclude-module','pytest','--exclude-module','matplotlib',
  '--exclude-module','IPython','--exclude-module','pandas',
  '--exclude-module','skimage','--exclude-module','sympy',
  '--exclude-module','numba','--exclude-module','pygame',
  '--exclude-module','librosa','--exclude-module','cv2',
  "$source\main.py"
)
Run-PyInstaller ($mainArguments + $cythonBinaryArgs + $cythonImportArgs)
Run-PyInstaller @(
  '--noconfirm','--clean','--onefile','--windowed',
  '--name','RemiXDuoSmaartWatcher','--distpath',"$source\dist",
  '--icon',"$source\remixduo_app.ico",
  '--workpath',"$source\build\watcher",'--specpath',"$source\build\specs",
  '--paths',$source,'--paths',"$source\src",'--collect-data','remix_duo',
  '--add-data',"$source\src\remix_duo\resources;remix_duo/resources",
  '--hidden-import','psutil','--hidden-import','win32api',
  '--hidden-import','smaart_api_v3_v4_readonly_v873',
  '--exclude-module','tensorflow','--exclude-module','torch',
  '--exclude-module','pytest',"$source\smaart_autostart_v875.py"
)
Run-PyInstaller @(
  '--noconfirm','--clean','--onefile','--console',
  '--name','RemiXDuoSmaartSetup','--distpath',"$source\dist",
  '--icon',"$source\remixduo_app.ico",
  '--workpath',"$source\build\setup",'--specpath',"$source\build\specs",
  '--paths',$source,'--paths',"$source\src",'--collect-data','remix_duo',
  '--add-data',"$source\src\remix_duo\resources;remix_duo/resources",
  '--hidden-import','smaart_discovery_v875','--hidden-import','psutil',
  '--hidden-import','win32api','--exclude-module','tensorflow',
  '--exclude-module','torch','--exclude-module','pytest',
  "$source\smaart_postinstall_v875.py"
)

$main=Join-Path $source 'dist\RemiXDuo\RemiXDuo.exe'
foreach($check in @('--cython-selfcheck','--qt-selfcheck','--online-license-selfcheck','--updater-selfcheck',
                    '--autoeq-selfcheck','--autofir-selfcheck','--package-selfcheck')) {
    $process=Start-Process -FilePath $main -ArgumentList $check -PassThru -WindowStyle Hidden
    if(!$process.WaitForExit(30000)) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        throw "FROZEN_SELF_CHECK_TIMEOUT: $check"
    }
    if($process.ExitCode -ne 0) { throw "FROZEN_SELF_CHECK_FAILED: $check / $($process.ExitCode)" }
}
& $inno (Join-Path $source 'remix_duo_production_v8150.iss')
if($LASTEXITCODE -ne 0) { throw "INNO_SETUP_FAILED: $LASTEXITCODE" }
$setup=Join-Path $source 'dist\installer\RemiXDuo_Setup_V8.150.exe'
if(!(Test-Path $setup)) { throw 'MISSING_FINAL_SETUP' }
Write-Host ('UNSIGNED_SETUP=' + $setup)
Write-Host ('UNSIGNED_SETUP_SHA256=' + (Get-FileHash $setup -Algorithm SHA256).Hash)
Write-Host 'SIGNING_REQUIRED_BEFORE_RELEASE'
