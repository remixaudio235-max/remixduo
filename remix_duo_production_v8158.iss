#define MyAppName "RemiX Duo"
#define MyAppVersion "8.158"
#define MyAppPublisher "RemiX Audio"
#define MyAppExeName "RemiXDuo.exe"
[Setup]
AppId={{4D1A276E-957B-4DE9-A1B0-66C1E5D2B877}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
SetupIconFile=remixduo_app.ico
UninstallDisplayIcon={app}\RemiXDuo.exe
VersionInfoVersion=8.158.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=RemiX Duo Smaart Companion
DefaultDirName={localappdata}\Programs\RemiX Duo
DefaultGroupName=RemiX Duo
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist\installer
OutputBaseFilename=RemiXDuo_Setup_V8.158
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=RemiX Duo V8.158
SetupLogging=yes
CloseApplications=no
RestartApplications=no
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
[Tasks]
Name: "autostart"; Description: "Tự mở RemiX Duo khi Smaart 8/9 bắt đầu"; GroupDescription: "Tích hợp Smaart"; Flags: checkedonce
Name: "desktopicon"; Description: "Tạo biểu tượng RemiX Duo trên Desktop"; GroupDescription: "Shortcut"
[Files]
Source: "dist\RemiXDuo\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dist\RemiXDuoSmaartWatcher.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\RemiXDuoSmaartSetup.exe"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\RemiX Duo"; Filename: "{app}\RemiXDuo.exe"
Name: "{autodesktop}\RemiX Duo"; Filename: "{app}\RemiXDuo.exe"; IconFilename: "{app}\RemiXDuo.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\RemiXDuoSmaartSetup.exe"; Parameters: "--enable --start-now"; Flags: runhidden waituntilterminated; Tasks: autostart
[UninstallRun]
Filename: "{app}\RemiXDuoSmaartSetup.exe"; Parameters: "--disable"; Flags: runhidden waituntilterminated; RunOnceId: "DisableSmaartCompanion"
