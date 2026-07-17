; Installateur Windows Linkora (Inno Setup 6+)
; Build via tools/build_windows.ps1 ou :
;   ISCC.exe /DMyAppVersion=1.1.0 tools\linkora.iss

#ifndef MyAppVersion
  #define MyAppVersion "1.1.0"
#endif

#define MyAppName "Linkora"
#define MyAppPublisher "Linkora"
#define MyAppURL "https://github.com/tallyhome/Linkora"
#define MyAppExeName "Linkora.exe"

[Setup]
AppId={{A7C3E9B1-4F2D-4A8E-9C1B-6D5E8F0A2B3C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=..\dist
OutputBaseFilename=Linkora-Setup-v{#MyAppVersion}
SetupIconFile=..\static\img\logo.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
; Ne pas écraser data/ utilisateur à la MAJ
UsePreviousAppDir=yes

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"

[Files]
; Appli complète — exclure data/ pour préserver historique & clés API
Source: "..\dist\Linkora\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "data\*"

[Dirs]
; Dossier data créé vide si absent (l'app le remplit au 1er lancement)
Name: "{app}\data"; Flags: uninsneveruninstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "Récupérateur de liens"
Name: "{group}\Désinstaller {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "Récupérateur de liens"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeUninstall(): Boolean;
begin
  Result := True;
  if DirExists(ExpandConstant('{app}\data')) then
  begin
    if MsgBox('Conserver l''historique et les réglages (dossier data) ?' + #13#10 +
              'Oui = garder data' + #13#10 +
              'Non = tout supprimer',
              mbConfirmation, MB_YESNO or MB_DEFBUTTON1) = IDNO then
    begin
      DelTree(ExpandConstant('{app}\data'), True, True, True);
    end;
  end;
end;
