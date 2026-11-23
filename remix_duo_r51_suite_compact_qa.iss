#define MyAppName "RemiX Duo 8.180 R5.1 Suite Compact QA"
#define MyAppVersion "8.180"
#define MyAppPublisher "RemiX Audio"
#define MyAppExeName "RemiXDuo.exe"
[Setup]
AppId={{A95E72B8-B89F-4AA7-9F32-8AD684FF41D7}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion=8.180.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=RemiX Duo V8.180 R5.1 Suite Compact Mag 888x238 Native QA
SetupIconFile=remixduo_app.ico
UninstallDisplayIcon={app}\RemiXDuo.exe
DefaultDirName={localappdata}\Programs\RemiX Duo V8.180 R5.1 Suite Compact QA
DefaultGroupName=RemiX Duo R5.1 Suite Compact QA
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist\installer_r51
OutputBaseFilename=RemiXDuo_QA_V8.180_R51_SuiteCompact_Setup
Compression=lzma2/fast
SolidCompression=no
WizardStyle=modern
UninstallDisplayName=RemiX Duo V8.180 R5.1 Suite Compact QA
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
Name: "{group}\RemiX Duo 8.180 R5.1 Suite Compact QA"; Filename: "{app}\RemiXDuo.exe"
; QA never registers autostart, modifies the default application, or starts a generator.
