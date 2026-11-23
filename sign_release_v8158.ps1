param([Parameter(Mandatory=$true)][string]$Thumbprint)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$signtool=(Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin" `
  -Filter signtool.exe -Recurse -ErrorAction SilentlyContinue |
  Sort-Object FullName -Descending | Select-Object -First 1).FullName
if(!$signtool){throw 'SIGNTOOL_NOT_FOUND'}
$cert=Get-Item "Cert:\CurrentUser\My\$Thumbprint" -ErrorAction Stop
if(!$cert.HasPrivateKey){throw 'CODE_SIGNING_PRIVATE_KEY_MISSING'}
$targets=@(
  'dist\RemiXDuo\RemiXDuo.exe',
  'dist\RemiXDuoSmaartWatcher.exe',
  'dist\RemiXDuoSmaartSetup.exe',
  'dist\installer\RemiXDuo_Setup_V8.158.exe'
) | ForEach-Object {Join-Path $root $_}
foreach($target in $targets){
  if(!(Test-Path $target)){throw "MISSING_SIGN_TARGET: $target"}
  & $signtool sign /sha1 $Thumbprint /fd SHA256 /td SHA256 `
    /tr http://timestamp.digicert.com $target
  if($LASTEXITCODE -ne 0){throw "SIGN_FAILED: $target"}
  if((Get-AuthenticodeSignature $target).Status -ne 'Valid'){
    throw "SIGNATURE_VERIFY_FAILED: $target"
  }
}
$lines=foreach($target in $targets){
  "$((Get-FileHash $target -Algorithm SHA256).Hash.ToLowerInvariant())  $([IO.Path]::GetRelativePath($root,$target).Replace('\','/'))"
}
$manifest=Join-Path $root 'dist\RELEASE_ARTIFACTS_V8.158.sha256'
Set-Content -LiteralPath $manifest -Value $lines -Encoding utf8NoBOM
Write-Output "SIGNED_MANIFEST=$manifest"
Write-Output "SIGNED_MANIFEST_SHA256=$((Get-FileHash $manifest -Algorithm SHA256).Hash)"
