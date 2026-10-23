# YAVIS – persönlicher, lokaler KI-Assistent für Windows 11

Kostenlos: lokales Modell (LM Studio), lokale Spracherkennung (faster-whisper), Stimmen über Edge-TTS (gratis, Internet)
oder Windows-Offline-Stimme. Keine API-Schlüssel, keine Abos.

## Windows-EXE über GitHub bauen

Das Repository enthält einen GitHub-Actions-Workflow unter `.github/workflows/build.yml`. GitHub baut daraus auf einem Windows-Runner einen Installer `YAVIS-Setup.exe`.

1. Lade **den Inhalt dieses Projektordners** in ein neues GitHub-Repository hoch. Wichtig: `.github/workflows/build.yml` muss genau an dieser Stelle im Repository liegen. Nicht nur die ZIP-Datei hochladen.
2. Öffne im Repository den Reiter **Actions** und wähle **Windows EXE bauen**. Bei einem Push auf `main` oder `master` startet der Build auch automatisch.
3. Warte, bis der Lauf grün ist. Öffne den abgeschlossenen Lauf und scrolle zu **Artifacts**.
4. Lade `YAVIS-Setup-Windows` herunter und entpacke das Archiv. Darin befindet sich `YAVIS-Setup.exe`. Starte diese Datei auf deinem Windows-PC.

Der Build läuft auf GitHubs Windows-Systemen; du brauchst dafür keinen Python-Compiler auf deinem PC. Der erste Build kann einige Minuten dauern. Der Workflow führt vor dem Verpacken Kern- und Mining-Tests sowie einen Start-Selbsttest der gebauten EXE aus. Nur wenn diese Schritte erfolgreich sind, werden Installer und portable ZIP als Artefakte veröffentlicht. Falls der Build fehlschlägt, öffne den Lauf in **Actions** und prüfe die rote Fehlermeldung im ersten fehlgeschlagenen Schritt. Eine Windows-EXE kann ich in dieser Linux-Umgebung nicht selbst ausführen oder verifizieren; GitHub übernimmt den Windows-Build und Selbsttest.

### Repository-Dateien hochladen

Am einfachsten: Entpacke die bereitgestellte ZIP auf deinem PC und lade die **Dateien und Ordner darin** ins Repository hoch, inklusive verstecktem Ordner `.github`. Alternativ kannst du Git lokal verwenden, wenn du damit vertraut bist.

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


## Bitcoin-Wallet (nur lesend)

Im Bereich „Crypto AI Trading“ kann eine **öffentliche Bitcoin-Adresse** abgefragt werden.
YAVIS zeigt bestätigtes/unbestätigtes Guthaben und die letzten Transaktionen über die
öffentliche Blockstream-Esplora-API an. Das Modul benötigt keine Seed-Phrase oder Private
Keys und kann keine Transaktionen signieren oder senden. Die Adresse wird an Blockstream
übermittelt, wenn die Abfrage gestartet wird. Keine Adresse eintragen, wenn du diese
Datenübermittlung nicht möchtest.

## Tests

GitHub Actions führt Kern-, Mining- und Wallet-Tests aus, baut die Windows-App mit
PyInstaller und prüft anschließend den Selbsttest der gebauten EXE. Der vollständige
Windows-Build muss in GitHub Actions tatsächlich durchlaufen, bevor ein Installer als
erfolgreich bestätigt werden kann.
