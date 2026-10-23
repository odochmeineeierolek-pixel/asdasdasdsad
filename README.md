# YAVIS – persönlicher, lokaler KI-Assistent für Windows 11

Kostenlos: lokales Modell (LM Studio), lokale Spracherkennung (faster-whisper), Stimmen über Edge-TTS (gratis, Internet)
oder Windows-Offline-Stimme. Keine API-Schlüssel, keine Abos.

## EXE erzeugen (nur GitHub, kein Test von dir nötig)
1. Neues GitHub-Repository anlegen, den **Inhalt** dieses Ordners hochladen (inkl. `.github`).
2. Reiter **Actions → Build YAVIS-Setup.exe → Run workflow**.
3. Nach ca. 15–25 Minuten: Lauf öffnen → **Artifacts → YAVIS-Setup** herunterladen, entpacken, `YAVIS-Setup.exe` starten.
   Der Lauf schlägt absichtlich fehl, wenn Tests oder der Selbsttest der EXE nicht bestehen.

## Erster Start
- Windows SmartScreen warnt bei unsignierten Programmen: „Weitere Informationen → Trotzdem ausführen“.
- Beim ersten Start versucht YAVIS auf Windows, **LM Studio automatisch über WinGet** im Hintergrund zu installieren, falls es noch fehlt. Dafür sind Internetzugang und `winget` erforderlich. Falls WinGet fehlt, öffnet YAVIS die offizielle Downloadseite.
- Nach der Installation öffnet YAVIS LM Studio. Lade dort einmalig ein lokales Modell herunter und starte den lokalen Server (standardmäßig Port 1234). In YAVIS unter Einstellungen die passende Modell-ID eintragen. Der Modell-Download erfolgt nicht automatisch, da Modellgröße und Hardwarebedarf stark variieren.
- Beim ersten Hören lädt Whisper sein Modell (~460 MB, einmalig, Internet nötig).
- Danach: „**YAVIS**, öffne YouTube“, „YAVIS, spiel Musik“, „YAVIS, was ist 12 mal 7“ …

## Funktionen
44 freigebbare Programme (+ eigene, + Startmenü-Import), 56 Stimmen-Voreinstellungen, eigene Aktivierungsnamen,
Gefühle (automatisch / immer neutral / nett / böse / traurig), animierter Kreis, Musikplayer, Webrecherche mit
Quellen, Gedächtnis (einsehbar/löschbar), Feedback-Lernen (👍/👎), Verkaufshilfe, Timer, Erinnerungen, Notizen,
Aufgaben, Rechner, Wetter, Witze, Münze/Würfel/Zufall, Screenshot, Lautstärke, PC sperren, Herunterfahren
(mit Bestätigung), Dateisuche, Ordner öffnen, Zwischenablage, Übersetzen, Tagesplan u. v. m.

## Ehrliche Grenzen
- Crypto AI Trading enthält Live-Kursabfrage und Paper-Trading; echte Orders sind nicht aktiviert.
- Kein „automatisches Geldverdienen“: YAVIS bereitet Texte/Preisrecherche vor; Veröffentlichen, Kaufen, Bezahlen, Senden machst du selbst.
- „Lernen“ = gemerkte Fakten + Feedback-Lektionen im Prompt; kein Selbstumprogrammieren.
- Stimmen sind 16 Grundstimmen × Stile (Tempo/Tonhöhe), keine 56 völlig verschiedenen Sprecher. Edge-TTS ist ein inoffizieller Gratisdienst und kann sich ändern.
- Während YAVIS spricht, hört er nicht zu (Echo-Schutz); dafür gibt es den STOPP-Knopf.
- Spracherkennung „perfekt“ gibt es nicht: Größeres Whisper-Modell (Einstellungen) = genauer, aber langsamer.
- Antwortgeschwindigkeit hängt von deinem PC ab (Modell `llama3.2:3b` ist ein guter Kompromiss).
