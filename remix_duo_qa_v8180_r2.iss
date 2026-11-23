#define MyAppName "RemiX Duo QA R2"
#define MyAppVersion "8.180"
#define MyAppPublisher "RemiX Audio"
#define MyAppExeName "RemiXDuo.exe"
[Setup]
AppId={{915E45BF-A4AF-48E2-9F23-ED3C0D23F180}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
SetupIconFile=remixduo_app.ico
UninstallDisplayIcon={app}\RemiXDuo.exe
VersionInfoVersion=8.180.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=RemiX Duo 8.180 QA R2 static-capture
DefaultDirName={localappdata}\Programs\RemiX Duo QA V8.180 R2
DefaultGroupName=RemiX Duo QA R2
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist\installer_qa
OutputBaseFilename=RemiXDuo_QA_Setup_V8.180_R2
Compression=lzma2/fast
SolidCompression=no
WizardStyle=modern
UninstallDisplayName=RemiX Duo QA V8.180 R2
SetupLogging=yes
CloseApplications=no
RestartApplications=no
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
[Tasks]
Name: "desktopicon"; Description: "Create QA Desktop shortcut"; GroupDescription: "QA Shortcuts"; Flags: unchecked
[Files]
Source: "dist\RemiXDuo\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dist\RemiXDuoSmaartWatcher.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\RemiXDuoSmaartSetup.exe"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\RemiX Duo"; Filename: "{app}\RemiXDuo.exe"
Name: "{autodesktop}\RemiX Duo"; Filename: "{app}\RemiXDuo.exe"; IconFilename: "{app}\RemiXDuo.exe"; Tasks: desktopicon
[Run]
; QA has no postinstall launches, no watcher or startup registration.

