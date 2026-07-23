; Installateur Windows Linkora (Inno Setup 6+)
; Build via tools/build_windows.ps1 ou :
;   ISCC.exe /DMyAppVersion=1.3.0 tools\linkora.iss
;
; Si une install existe déjà → page : Mettre à jour / Réparer / Désinstaller

#ifndef MyAppVersion
  #define MyAppVersion "1.3.0"
#endif

#define MyAppName "Linkora"
#define MyAppPublisher "Tallyhome"
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
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Linkora — récupérateur de liens
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoCopyright=Copyright © 2026 Tallyhome
VersionInfoOriginalFileName=Linkora-Setup.exe
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableDirPage=auto
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
UsePreviousAppDir=yes
UsePreviousTasks=yes
; Autorise la réinstall par-dessus la même version (Réparer)
AllowNoIcons=yes

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"


[Files]
; Appli complète — exclure data/ et updates/ pour préserver historique & staging MAJ
Source: "..\dist\Linkora\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "data\*,updates\*"

[Dirs]
Name: "{app}\data"; Flags: uninsneveruninstall
Name: "{app}\updates"; Flags: uninsneveruninstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "Récupérateur de liens"
Name: "{group}\Désinstaller {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "Récupérateur de liens"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
function ExitProcess(uExitCode: Integer): Boolean;
  external 'ExitProcess@kernel32.dll stdcall';

var
  ExistingPage: TWizardPage;
  RadioUpdate: TNewRadioButton;
  RadioRepair: TNewRadioButton;
  RadioUninstall: TNewRadioButton;
  ExistingInfoLabel: TNewStaticText;
  PrevVersion: String;
  PrevDir: String;
  UninstallCmd: String;
  ModeUninstallOnly: Boolean;

function UninstallRegKey: String;
begin
  Result := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\' +
    '{' + 'A7C3E9B1-4F2D-4A8E-9C1B-6D5E8F0A2B3C' + '}_is1';
end;

function ReadInstallInfo: Boolean;
var
  RootKey: Integer;
begin
  Result := False;
  PrevVersion := '';
  PrevDir := '';
  UninstallCmd := '';

  { PrivilegesRequired=lowest → HKCU en priorité }
  if RegQueryStringValue(HKCU, UninstallRegKey, 'UninstallString', UninstallCmd) then
    RootKey := HKCU
  else if RegQueryStringValue(HKLM, UninstallRegKey, 'UninstallString', UninstallCmd) then
    RootKey := HKLM
  else
    Exit;

  RegQueryStringValue(RootKey, UninstallRegKey, 'DisplayVersion', PrevVersion);
  RegQueryStringValue(RootKey, UninstallRegKey, 'InstallLocation', PrevDir);
  if (PrevDir = '') and (UninstallCmd <> '') then
  begin
    { Déduire le dossier depuis unins000.exe }
    PrevDir := ExtractFileDir(RemoveQuotes(UninstallCmd));
  end;
  Result := (UninstallCmd <> '');
end;

function IsUpgradeMode: Boolean;
begin
  Result := (ExistingPage <> nil) and RadioUpdate.Checked and not ModeUninstallOnly;
end;

function IsRepairMode: Boolean;
begin
  Result := (ExistingPage <> nil) and RadioRepair.Checked and not ModeUninstallOnly;
end;

procedure CreateExistingInstallPage;
var
  Info: String;
begin
  ExistingPage := CreateCustomPage(
    wpWelcome,
    'Installation existante détectée',
    'Linkora est déjà présent sur cet ordinateur. Que souhaitez-vous faire ?'
  );

  ExistingInfoLabel := TNewStaticText.Create(ExistingPage);
  ExistingInfoLabel.Parent := ExistingPage.Surface;
  ExistingInfoLabel.Left := ScaleX(0);
  ExistingInfoLabel.Top := ScaleY(0);
  ExistingInfoLabel.Width := ExistingPage.SurfaceWidth;
  ExistingInfoLabel.AutoSize := False;
  ExistingInfoLabel.WordWrap := True;
  ExistingInfoLabel.Height := ScaleY(48);

  Info := 'Version installée : ';
  if PrevVersion <> '' then
    Info := Info + PrevVersion
  else
    Info := Info + '(inconnue)';
  Info := Info + #13#10 + 'Nouvelle version : {#MyAppVersion}';
  if PrevDir <> '' then
    Info := Info + #13#10 + 'Dossier : ' + PrevDir;
  ExistingInfoLabel.Caption := Info;

  RadioUpdate := TNewRadioButton.Create(ExistingPage);
  RadioUpdate.Parent := ExistingPage.Surface;
  RadioUpdate.Left := ScaleX(0);
  RadioUpdate.Top := ExistingInfoLabel.Top + ExistingInfoLabel.Height + ScaleY(12);
  RadioUpdate.Width := ExistingPage.SurfaceWidth;
  RadioUpdate.Height := ScaleY(22);
  RadioUpdate.Caption := 'Mettre à jour vers {#MyAppVersion} (conserve historique & réglages)';
  RadioUpdate.Checked := True;

  RadioRepair := TNewRadioButton.Create(ExistingPage);
  RadioRepair.Parent := ExistingPage.Surface;
  RadioRepair.Left := ScaleX(0);
  RadioRepair.Top := RadioUpdate.Top + ScaleY(28);
  RadioRepair.Width := ExistingPage.SurfaceWidth;
  RadioRepair.Height := ScaleY(22);
  RadioRepair.Caption := 'Réparer / réinstaller les fichiers (conserve data/)';

  RadioUninstall := TNewRadioButton.Create(ExistingPage);
  RadioUninstall.Parent := ExistingPage.Surface;
  RadioUninstall.Left := ScaleX(0);
  RadioUninstall.Top := RadioRepair.Top + ScaleY(28);
  RadioUninstall.Width := ExistingPage.SurfaceWidth;
  RadioUninstall.Height := ScaleY(22);
  RadioUninstall.Caption := 'Désinstaller Linkora';
end;

procedure InitializeWizard;
begin
  ModeUninstallOnly := False;
  if ReadInstallInfo then
    CreateExistingInstallPage;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ResultCode: Integer;
  Cmd, Params: String;
begin
  Result := True;
  if (ExistingPage = nil) or (CurPageID <> ExistingPage.ID) then
    Exit;

  if RadioUninstall.Checked then
  begin
    if MsgBox(
      'Lancer la désinstallation de Linkora ?' + #13#10 +
      'Vous pourrez choisir de conserver ou non le dossier data/.',
      mbConfirmation, MB_YESNO or MB_DEFBUTTON2) <> IDYES then
    begin
      Result := False;
      Exit;
    end;

    Cmd := RemoveQuotes(UninstallCmd);
    Params := '';
    { L’uninstall Inno accepte /SILENT ; on laisse l’UI pour la question data/ }
    if not FileExists(Cmd) then
    begin
      MsgBox('Désinstalleur introuvable :' + #13#10 + Cmd, mbError, MB_OK);
      Result := False;
      Exit;
    end;

    if Exec(Cmd, Params, '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
    begin
      MsgBox('Désinstallation terminée.', mbInformation, MB_OK);
      ExitProcess(0);
    end
    else
    begin
      MsgBox('Impossible de lancer le désinstalleur.', mbError, MB_OK);
      Result := False;
    end;
  end
  else if RadioUpdate.Checked or RadioRepair.Checked then
  begin
    if (PrevDir <> '') and DirExists(PrevDir) then
      WizardForm.DirEdit.Text := PrevDir;
  end;
end;

function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo, MemoTypeInfo,
  MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
var
  S: String;
begin
  S := '';
  if ExistingPage <> nil then
  begin
    if RadioUpdate.Checked then
      S := S + 'Action : Mise à jour vers {#MyAppVersion}' + NewLine
    else if RadioRepair.Checked then
      S := S + 'Action : Réparation / réinstallation' + NewLine;
    if PrevVersion <> '' then
      S := S + 'Version précédente : ' + PrevVersion + NewLine;
  end
  else
    S := S + 'Action : Nouvelle installation' + NewLine;

  S := S + NewLine + MemoDirInfo;
  if MemoGroupInfo <> '' then
    S := S + NewLine + MemoGroupInfo;
  if MemoTasksInfo <> '' then
    S := S + NewLine + MemoTasksInfo;
  Result := S;
end;

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

function InstallLocaleCode: String;
begin
  if ActiveLanguage = 'english' then
    Result := 'en'
  else
    Result := 'fr';
end;

procedure WriteUiLocaleSetting;
var
  SettingsPath, Content, Locale: String;
begin
  Locale := InstallLocaleCode;
  ForceDirectories(ExpandConstant('{app}\data'));
  SettingsPath := ExpandConstant('{app}\data\settings.json');
  if FileExists(SettingsPath) then
  begin
    { Mise à jour / réparation : ne pas écraser les réglages existants }
    Exit;
  end;
  Content :=
    '{' + #13#10 +
    '  "active_provider": "alldebrid",' + #13#10 +
    '  "theme": "linkora",' + #13#10 +
    '  "ui_locale": "' + Locale + '"' + #13#10 +
    '}';
  SaveStringToFile(SettingsPath, Content, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    WriteUiLocaleSetting;
end;
