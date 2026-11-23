#define MyAppName "RemiX Duo 8.180 R60 SUM Restore QA"
#define MyAppVersion "8.180"
#define MyAppPublisher "RemiX Audio"
#define MyAppExeName "RemiXDuo.exe"
[Setup]
AppId={{24A30618-3E9B-4FCB-9299-1A9425E6A60F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion=8.180.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=RemiX Duo V8.180 R60 Smaart8 SUM Phase and SUM Mag native QA
SetupIconFile=remixduo_app.ico
UninstallDisplayIcon={app}\RemiXDuo.exe
DefaultDirName={localappdata}\Programs\RemiX Duo V8.180 R60 SUM Restore QA
DefaultGroupName=RemiX Duo R60 SUM Restore QA
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist\installer_r60
OutputBaseFilename=RemiXDuo_QA_V8.180_R60_SUM_Restore_Setup
Compression=lzma2/fast
SolidCompression=no
WizardStyle=modern
UninstallDisplayName=RemiX Duo V8.180 R60 SUM Restore QA
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
Name: "{group}\RemiX Duo 8.180 R60 SUM Restore QA"; Filename: "{app}\RemiXDuo.exe"
; R60 isolated install: no AppId collision with R59, no postinstall run.
; QA never registers autostart, modifies the default application, or starts a generator.
