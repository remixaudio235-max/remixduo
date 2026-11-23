# Offscreen unit/Qt suite; excludes scripts that control real Windows/Smaart UI.
$ErrorActionPreference = 'Stop'
$env:QT_QPA_PLATFORM = 'offscreen'
$taskPython = 'D:\REMIX_SIGNAL_AUTOEQ_PARALLEL_QA_20261029\.venv\Scripts\python.exe'
Set-Location $PSScriptRoot
$taskTests = Get-ChildItem -File 'test*.py' | Where-Object {
    $_.Name -notin @('test_hide_other_window_v7.py','test_live_sync_probe.py',
                    'test_uia_scroll_restore.py','test_v7_gui.py')
} | Select-Object -ExpandProperty Name
& $taskPython -m pytest -q @taskTests --tb=short
exit $LASTEXITCODE
