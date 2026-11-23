#define MyAppName "RemiX Duo QA"
#define MyAppVersion "8.87"
#define MyAppPublisher "RemiX Audio"
#define MyAppExeName "RemiXDuo_QA.exe"
[Setup]
AppId={{4D1A276E-957B-4DE9-A1B0-66C1E5D2B877}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion=8.87.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=RemiX Duo QA Smaart Companion Test Installer
DefaultDirName={localappdata}\Programs\RemiX Duo QA
DefaultGroupName=RemiX Duo QA
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist\installer
OutputBaseFilename=RemiXDuo_QA_Setup_V8.87
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=RemiX Duo QA V8.87
SetupLogging=yes
CloseApplications=no
RestartApplications=no
DisableReadyPage=no
DisableFinishedPage=no
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
[Tasks]
Name: "autostart"; Description: "Tu mo RemiX Duo khi Smaart 8/9 bat dau"; GroupDescription: "Tich hop Smaart"; Flags: checkedonce
Name: "desktopicon"; Description: "Tao bieu tuong RemiX Duo QA tren Desktop"; GroupDescription: "Shortcut"
[Files]
Source: "dist\RemiXDuo_QA\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dist\RemiXDuoSmaartWatcher.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\RemiXDuoSmaartSetup.exe"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\RemiX Duo QA"; Filename: "{app}\RemiXDuo_QA.exe"
Name: "{autodesktop}\RemiX Duo QA"; Filename: "{app}\RemiXDuo_QA.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\RemiXDuoSmaartSetup.exe"; Parameters: "--enable --start-now"; Flags: runhidden waituntilterminated; Tasks: autostart
[UninstallRun]
Filename: "{app}\RemiXDuoSmaartSetup.exe"; Parameters: "--disable"; Flags: runhidden waituntilterminated; RunOnceId: "DisableSmaartCompanion"
