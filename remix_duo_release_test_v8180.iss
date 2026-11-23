#define MyAppName "RemiX Duo V8.180 Release Test"
#define MyAppVersion "8.180"
#define MyAppPublisher "RemiX Audio"
[Setup]
AppId={{11E0CEFC-5581-41A0-980F-5221A8521870}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion=8.180.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=RemiX Duo 8.180 release binary validation
SetupIconFile=remixduo_app.ico
UninstallDisplayIcon={app}\RemiXDuo.exe
DefaultDirName={localappdata}\Programs\RemiX Duo V8.180 Release Test
DefaultGroupName=RemiX Duo V8.180 Release Test
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist\installer_release_test
OutputBaseFilename=RemiXDuo_V8.180_Release_Test_Setup
Compression=lzma2/fast
SolidCompression=no
WizardStyle=modern
UninstallDisplayName=RemiX Duo V8.180 Release Test
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
Name: "{group}\RemiX Duo 8.180 Release Test"; Filename: "{app}\RemiXDuo.exe"
; Deliberately do not register autostart/watcher or launch any generator.
; Production licensing, Cython core and complete frozen payload are unchanged.
