[Setup]
AppName=YAVIS
AppVersion=1.0.0
AppPublisher=YAVIS
DefaultDirName={autopf}\YAVIS
DefaultGroupName=YAVIS
OutputDir=Output
OutputBaseFilename=YAVIS-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=..\assets\yavis.ico
UninstallDisplayIcon={app}\YAVIS.exe
DisableProgramGroupPage=yes

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Symbole:"
Name: "autostart"; Description: "YAVIS mit Windows starten (optional)"; GroupDescription: "Start:"; Flags: unchecked

[Files]
Source: "..\dist\YAVIS\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\YAVIS"; Filename: "{app}\YAVIS.exe"
Name: "{autodesktop}\YAVIS"; Filename: "{app}\YAVIS.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "YAVIS"; ValueData: """{app}\YAVIS.exe"" --minimized"; Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\YAVIS.exe"; Description: "YAVIS jetzt starten"; Flags: nowait postinstall skipifsilent
