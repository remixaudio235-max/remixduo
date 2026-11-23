#define MyAppName "RemiX Duo 8.180 R4 QA"
#define MyAppVersion "8.180"
#define MyAppPublisher "RemiX Audio"
#define MyAppExeName "RemiXDuo.exe"
[Setup]
AppId={{B8A7C4FB-A048-466A-B48E-B1E052E19413}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion=8.180.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=RemiX Duo V8.180 R4 EQ Export independent QA
SetupIconFile=remixduo_app.ico
UninstallDisplayIcon={app}\RemiXDuo.exe
DefaultDirName={localappdata}\Programs\RemiX Duo V8.180 R4 QA
DefaultGroupName=RemiX Duo R4 QA
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist\installer_r4
OutputBaseFilename=RemiXDuo_QA_V8.180_R4_Setup
Compression=lzma2/fast
SolidCompression=no
WizardStyle=modern
UninstallDisplayName=RemiX Duo V8.180 R4 QA
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
Name: "{group}\RemiX Duo 8.180 R4 QA"; Filename: "{app}\RemiXDuo.exe"
; QA never registers autostart, modifies the default application, or starts a generator.
