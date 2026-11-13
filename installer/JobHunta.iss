; Instalador do JobHunta (Inno Setup 6). Compilar com:
;   ISCC /DAppVersion=0.1.0 installer\JobHunta.iss
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
; Não troque este AppId: é ele que faz a atualização substituir a instalação anterior.
AppId={{6F1D3A52-8C47-4B8E-9A3B-4A0C7E2D91B5}
AppName=JobHunta
AppVersion={#AppVersion}
AppPublisher=Douglas Couto
DefaultDirName={autopf}\JobHunta
DefaultGroupName=JobHunta
; Instalação por usuário: não pede administrador, então a atualização silenciosa funciona.
PrivilegesRequired=lowest
OutputDir=..\Output
OutputBaseFilename=JobHunta-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UninstallDisplayName=JobHunta
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; Flags: unchecked

[Files]
Source: "..\dist\JobHunta\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\JobHunta"; Filename: "{app}\JobHunta.exe"
Name: "{autodesktop}\JobHunta"; Filename: "{app}\JobHunta.exe"; Tasks: desktopicon

[Run]
; Sem "skipifsilent": depois de uma atualização silenciosa o programa reabre sozinho.
Filename: "{app}\JobHunta.exe"; Description: "Abrir o JobHunta"; Flags: nowait postinstall
