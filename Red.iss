[Setup]
AppName=Red
AppVersion=1.0
DefaultDirName={pf}\Red
DefaultGroupName=Red
OutputBaseFilename=RedSetup
Compression=lzma
SolidCompression=yes

[Files]
; Copie tout le contenu de dist\main dans le dossier d'installation
Source: "C:\Users\pc\Desktop\pyramide\dist\main\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Raccourci dans le menu Démarrer
Name: "{group}\Red"; Filename: "{app}\main.exe"

; Raccourci sur le bureau (optionnel)
Name: "{commondesktop}\Red"; Filename: "{app}\main.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le bureau"; \
    GroupDescription: "Options supplémentaires"; Flags: unchecked