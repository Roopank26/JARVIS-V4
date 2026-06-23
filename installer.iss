; JARVIS Desktop Installer Script
; Inno Setup Script for Windows Installer
; Build with: iscc installer.iss

#define MyAppName "JARVIS Desktop"
#define MyAppVersion "3.0.0"
#define MyAppPublisher "JARVIS Project"
#define MyAppURL "https://github.com/jarvis"
#define MyAppExeName "JARVIS.exe"

[Setup]
AppId={{B8F3E9A2-5C4D-4E7F-8B1A-2C3D4E5F6A7B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=installer
OutputBaseFilename=JARVIS-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Start automatically with Windows"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\JARVIS\JARVIS.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\JARVIS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Auto-start with Windows
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "JARVIS"; ValueData: """{app}\{#MyAppExeName}"" --hidden"; Flags: uninsdeletevalue; Tasks: startupicon

; JARVIS data directory
Root: HKCU; Subkey: "Software\JARVIS"; ValueType: string; ValueName: "DataDir"; ValueData: "{userappdata}\JARVIS"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /F /IM JARVIS.exe"; Flags: runhidden; RunOnceId: "KillJARVIS"

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\JARVIS"

[Code]
function InitializeSetup(): Boolean;
begin
  // Kill existing JARVIS instance
  Exec('cmd.exe', '/C taskkill /F /IM JARVIS.exe', '', SW_HIDE, ewWaitUntilTerminated, Result);
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Create data directory
    ForceDirectories(ExpandConstant('{userappdata}\JARVIS'));
  end;
end;
