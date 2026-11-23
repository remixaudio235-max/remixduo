#define MyAppName "RemiX Duo 8.181 R65 Full Release QA"
#define MyAppVersion "8.181"
#define MyAppPublisher "RemiX Audio"
#define MyAppExeName "RemiXDuo.exe"
[Setup]
AppId={{FF1108D7-4D58-4AE3-A1D7-87460CB68165}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion=8.181.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=RemiX Duo V8.181 R65 full release acceptance QA
SetupIconFile=remixduo_app.ico
UninstallDisplayIcon={app}\RemiXDuo.exe
DefaultDirName={localappdata}\Programs\RemiX Duo V8.181 R65 Full Release QA
DefaultGroupName=RemiX Duo R65 Full Release QA
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist\installer_r65
OutputBaseFilename=RemiXDuo_QA_V8.181_R65_Full_Release_Setup
Compression=lzma2/fast
SolidCompression=no
WizardStyle=modern
UninstallDisplayName=RemiX Duo V8.181 R65 Full Release QA
SetupLogging=yes
CloseApplications=no
RestartApplications=no
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
[Files]
Source: "dist\RemiXDuo\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dist\RemiXDuoSmaartWatcher.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\RemiXDuoSmaartSetup.exe"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\RemiX Duo 8.181 R65 Full Release QA"; Filename: "{app}\RemiXDuo.exe"
Name: "{autodesktop}\RemiX Duo"; Filename: "{app}\RemiXDuo.exe"; WorkingDir: "{app}"
; R65 isolated QA install: unique AppId, no postinstall run.
; QA never registers autostart, modifies the default application, or starts a generator.
