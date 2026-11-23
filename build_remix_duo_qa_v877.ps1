# RemiX Duo V8.77 QA Windows Installer - clean local build
# Never run GUI/Smaart/Generator/SoundCard; only compile and produce artifacts.
# Cloudflare production release MUST NOT use the QA runtime hook.
$ErrorActionPreference = 'Stop'
$env:PYTHONNOUSERSITE = '1'
$source = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = 'D:\REMIX_SIGNAL_AUTOEQ_PARALLEL_QA_20261029\.venv\Scripts\python.exe'
$inno = 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
if (!(Test-Path $python)) { throw 'MISSING_BUILD_PYTHON' }
if (!(Test-Path $inno)) { throw 'MISSING_INNO_SETUP' }
$safePathEntries = @(
    (Split-Path -Parent $python),
    "$env:SystemRoot\System32",
    $env:SystemRoot,
    (Split-Path -Parent $inno)
)
$env:PATH = $safePathEntries -join ';'
Write-Host ('QA_BUILD_PATH_SANITIZED=' + $env:PATH)
Set-Location $source
function Run-PyInstaller([string[]]$Arguments) {
    & $python -m PyInstaller @Arguments
    if ($LASTEXITCODE -ne 0) { throw "PYINSTALLER_FAILED: $LASTEXITCODE" }
}
Run-PyInstaller @(
      '--noconfirm', '--clean', '--onedir', '--windowed',
      '--name', 'RemiXDuo_QA',
      '--distpath', "$source\dist", '--workpath', "$source\build\pyinstaller_light",
      '--specpath', "$source\build\specs", '--paths', "$source", '--paths', "$source\src",
      '--collect-data', 'remix_duo',
      '--add-data', "$source\src\remix_duo\resources;remix_duo/resources",
      '--runtime-hook', "$source\qa_runtime_hook_remix_duo_v877.py",
      '--add-data', "$source\remix_dou_swirl_toolbar32.png;.",
      '--add-data', "$source\remix_activation_logo.jpg;.",
      '--add-data', "$source\V812_MAG_TITLE_TEMPLATE.png;.",
      '--add-data', "$source\V812_PHASE_TITLE_TEMPLATE.png;.",
      '--hidden-import', 'remix_duo_license_v874',
      '--hidden-import', 'remix_duo_cloud_license_v876',
      '--hidden-import', 'win32timezone', '--hidden-import', 'pythoncom',
      '--hidden-import', 'pywintypes',
      '--hidden-import', 'pywinauto.controls.uiawrapper',
      '--exclude-module', 'torch', '--exclude-module', 'tensorflow',
      '--exclude-module', 'pytest', '--exclude-module', 'matplotlib',
      '--exclude-module', 'IPython', '--exclude-module', 'pandas',
      '--exclude-module', 'skimage', '--exclude-module', 'sympy',
      '--exclude-module', 'numba', '--exclude-module', 'pygame',
      '--exclude-module', 'librosa', '--exclude-module', 'cv2',
      "$source\overlay_v7.py"
)
Run-PyInstaller @(
      '--noconfirm', '--clean', '--onefile', '--windowed',
      '--name', 'RemiXDuoSmaartWatcher',
      '--distpath', "$source\dist", '--workpath', "$source\build\watcher",
      '--specpath', "$source\build\specs", '--paths', "$source", '--paths', "$source\src",
      '--collect-data', 'remix_duo',
      '--add-data', "$source\src\remix_duo\resources;remix_duo/resources",
      '--hidden-import', 'psutil', '--hidden-import', 'win32api',
      '--hidden-import', 'smaart_api_v3_v4_readonly_v873',
      '--exclude-module', 'tensorflow', '--exclude-module', 'torch',
      '--exclude-module', 'pytest',
      "$source\smaart_autostart_v875.py"
)
Run-PyInstaller @(
      '--noconfirm', '--clean', '--onefile', '--console',
      '--name', 'RemiXDuoSmaartSetup',
      '--distpath', "$source\dist", '--workpath', "$source\build\setup_helper",
      '--specpath', "$source\build\specs", '--paths', "$source", '--paths', "$source\src",
      '--collect-data', 'remix_duo',
      '--add-data', "$source\src\remix_duo\resources;remix_duo/resources",
      '--hidden-import', 'smaart_discovery_v875',
      '--hidden-import', 'psutil', '--hidden-import', 'win32api',
      '--exclude-module', 'tensorflow', '--exclude-module', 'torch',
      '--exclude-module', 'pytest',
      "$source\smaart_postinstall_v875.py"
)
foreach ($relative in @(
    'dist\RemiXDuo_QA\RemiXDuo_QA.exe',
    'dist\RemiXDuoSmaartWatcher.exe',
    'dist\RemiXDuoSmaartSetup.exe'
)) {
    if (!(Test-Path (Join-Path $source $relative))) {
        throw "MISSING_EXE: $relative"
    }
}
$main = Join-Path $source 'dist\RemiXDuo_QA\RemiXDuo_QA.exe'
$qtCheck = Start-Process -FilePath $main -ArgumentList '--qt-selfcheck' `
    -PassThru -WindowStyle Hidden
if (!$qtCheck.WaitForExit(30000)) {
    Stop-Process -Id $qtCheck.Id -Force -ErrorAction SilentlyContinue
    throw "QT_RUNTIME_SELF_CHECK_TIMEOUT: $($qtCheck.Id)"
}
if ($qtCheck.ExitCode -ne 0) {
    throw "QT_RUNTIME_SELF_CHECK_FAILED: $($qtCheck.ExitCode)"
}
$onlineCheck = Start-Process -FilePath $main `
    -ArgumentList '--online-license-selfcheck' -PassThru -WindowStyle Hidden
if (!$onlineCheck.WaitForExit(30000)) {
    Stop-Process -Id $onlineCheck.Id -Force -ErrorAction SilentlyContinue
    throw "ONLINE_LICENSE_SELF_CHECK_TIMEOUT: $($onlineCheck.Id)"
}
if ($onlineCheck.ExitCode -ne 0) {
    throw "ONLINE_LICENSE_SELF_CHECK_FAILED: $($onlineCheck.ExitCode)"
}
$selfCheck = Start-Process -FilePath $main -ArgumentList '--package-selfcheck' `
    -PassThru -WindowStyle Hidden
if (!$selfCheck.WaitForExit(30000)) {
    Stop-Process -Id $selfCheck.Id -Force -ErrorAction SilentlyContinue
    throw "PACKAGE_SELF_CHECK_TIMEOUT: $($selfCheck.Id)"
}
if ($selfCheck.ExitCode -notin @(0, 22)) {
    throw "PACKAGE_SELF_CHECK_FAILED: $($selfCheck.ExitCode)"
}
Write-Host ('PACKAGE_SELF_CHECK_LICENSE_STATUS=' + $selfCheck.ExitCode)
& $inno (Join-Path $source 'remix_duo_qa_v877_installer.iss')
if ($LASTEXITCODE -ne 0) { throw "INNO_SETUP_FAILED: $LASTEXITCODE" }
$setup = Join-Path $source 'dist\installer\RemiXDuo_QA_Setup_V8.87.exe'
if (!(Test-Path $setup)) { throw 'MISSING_FINAL_SETUP' }
Write-Host ('QA_SETUP=' + $setup)
Write-Host ('QA_SETUP_SIZE_BYTES=' + (Get-Item $setup).Length)
Write-Host ('QA_SETUP_SHA256=' + (Get-FileHash $setup -Algorithm SHA256).Hash)
Write-Host 'QA_ONLINE_PRO_STYLE_LICENSE_ENABLED'
