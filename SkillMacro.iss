; onedir 빌드 결과를 단일 설치 파일로 패키징하는 Inno Setup 스크립트
; 버전은 워크플로우에서 /DMyAppVersion 으로 전달

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

#define MyAppName "ProDays SkillMacro"
#define MyAppExeName "SkillMacro.exe"
#define MyAppPublisher "ProDays"
#define SourceDir "dist\onedir\SkillMacro"

[Setup]
AppId={{8B6A2D31-7F4E-4C9A-9E2B-3D5F1A0C7E64}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\ProDays\SkillMacro
DefaultGroupName=ProDays SkillMacro
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=dist\installer
OutputBaseFilename=SkillMacro-Setup
SetupIconFile=app\resources\image\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
