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
- Installiere **LM Studio**, lade dort ein lokales Modell und starte den lokalen Server (standardmäßig Port 1234). In YAVIS unter Einstellungen die passende Modell-ID eintragen.
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

## GPU-Mining-Modul (neu)

In der linken Navigation gibt es jetzt **Mining**. Das Modul enthält eine Stromkosten-/Nettogewinn-Rechnung, einen Vergleich GPU-Coin vs. direktes Bitcoin-GPU-Mining, NVIDIA-Telemetrie über `nvidia-smi`, Temperaturwarnung ab 83 °C und automatischen Prozess-Stopp ab 87 °C. Für den Start muss `nvidia-smi` verfügbar sein; sonst blockiert YAVIS den Start aus Sicherheitsgründen.

YAVIS lädt keine Miner herunter und führt keine Shell-Befehle aus. Zum Start ist eine vom Benutzer installierte, vertrauenswürdige `.exe` nötig. Pool- und Worker-Argumente hängen vom gewählten Miner und Pool ab. Niemals Seed-Phrasen oder private Schlüssel in Argumente eintragen. Der Ertrag ist eine editierbare Annahme und keine Live-Prognose. Die Berechnung berücksichtigt Strom, Poolgebühr und Nutzungszeit; PC-Grundverbrauch, Auszahlungsschwellen, Hardwareverschleiß, Steuern und Kursrisiko sind nicht automatisch enthalten.

**RTX 4070 SUPER / Strompreis 0,34 €/kWh:** bei angenommenen 190 W entstehen ca. 4,56 kWh bzw. 1,55 € Stromkosten pro Tag (nur GPU). Bei einem beispielhaften Bruttoertrag von 0,60 €/Tag und 1 % Poolgebühr läge der modellierte Nettowert bei ca. -0,96 €/Tag. Passe den Ertrag an aktuelle, überprüfbare Pool-/Benchmark-Daten an.

Tests: `python tests/test_core.py` und `python tests/test_mining.py`.
