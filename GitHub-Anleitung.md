# GitHub-Anleitung: Resource-Pack automatisch veröffentlichen

Ziel: Du lädst **nur noch deine ZIP hoch**. GitHub erhöht die Version, berechnet den SHA-256-Hash, erstellt die Release und aktualisiert `latest.json` – alles automatisch.

Das Skript und der Workflow wurden lokal getestet (Skript) bzw. auf gültiges YAML geprüft (Workflow), **aber noch nicht auf GitHub ausgeführt**. Prüfe deshalb Schritt 12 gründlich und melde mir Fehlermeldungen aus dem Actions-Protokoll.

## 1. GitHub-Account erstellen
1. https://github.com öffnen → **Sign up**.
2. E-Mail, Passwort und **Benutzernamen** wählen (z. B. `maxmuster`). Dieser Name ist später dein `DEINNAME`.
3. E-Mail-Adresse über den Bestätigungscode bestätigen.

## 2. Repository erstellen
1. Oben rechts **+ → New repository**.
2. *Repository name:* `CustomPackUpdater`
3. **Public** auswählen (wichtig: Die Mod lädt ohne Anmeldung, das geht nur bei öffentlichen Repos).
4. Haken bei **Add a README file** setzen (damit der Zweig `main` existiert).
5. **Create repository**.

## 3. Projektdateien hochladen
Entpacke `GitHub-Repo-Dateien.zip`. Darin liegen: `.github/`, `scripts/`, `resourcepack/`, `latest.json`, `version.txt`, `README.md`.

1. Im Repository **Add file → Upload files**.
2. Ziehe den **Inhalt** des entpackten Ordners ins Browserfenster (nicht den Ordner selbst).
3. Unten **Commit changes**.

Wichtig: `.github` ist ein versteckter Ordner. Windows: Im Explorer *Ansicht → Anzeigen → Ausgeblendete Elemente*. Mac: `Cmd + Shift + .`.
**Falls der Ordner `.github` nicht hochgeladen wurde:** *Add file → Create new file*, als Name `.github/workflows/update-resourcepack.yml` eintippen (die Schrägstriche erzeugen die Ordner), den Inhalt der Datei `update-resourcepack.yml` einfügen, **Commit changes**.

Danach in `latest.json` (Stift-Symbol) **DEINNAME** durch deinen Benutzernamen ersetzen und speichern. (Nach der ersten Veröffentlichung überschreibt der Workflow die Datei ohnehin korrekt.)

## 4. GitHub Actions aktivieren
1. Oben auf den Tab **Actions** klicken.
2. Erscheint ein Hinweis wie *„Workflows aren't being run on this repository“*, auf **I understand my workflows, go ahead and enable them** klicken.
3. Links sollte **Resource-Pack veröffentlichen** auftauchen.

## 5. Berechtigungen einstellen
Der Workflow verlangt selbst nur `contents: write` (Releases + Commit). Zur Sicherheit auch im Repository:
1. **Settings → Actions → General**.
2. Ganz unten **Workflow permissions → Read and write permissions** → **Save**.
3. **Settings → Branches:** Es darf keine Schutzregel für `main` geben, die Pushes verbietet.

Keine Passwörter oder Tokens eintragen – der Workflow nutzt den automatischen `GITHUB_TOKEN`.

## 6. Resource-Pack als ZIP vorbereiten
1. Öffne deinen Pack-Ordner. **Direkt darin** muss `pack.mcmeta` liegen, daneben der Ordner `assets`.
2. Markiere **alles im Ordner** (nicht den Ordner selbst) → Rechtsklick → *Senden an → ZIP-komprimierter Ordner* (Mac: *Komprimieren*).
3. Benenne die ZIP um in `CustomPack.zip` (keine Leerzeichen, nur Buchstaben/Zahlen/`.`/`_`/`-`).
4. Test: Öffne die ZIP – du siehst sofort `pack.mcmeta`, **nicht** erst einen Unterordner.

## 7. ZIP hochladen
1. Im Repository den Ordner **resourcepack** öffnen.
2. **Add file → Upload files** → `CustomPack.zip` hineinziehen → **Commit changes** (direkt auf `main`).

Im Ordner darf immer nur **eine** ZIP liegen. Browser-Upload geht bis 25 MB; größere Dateien (bis maximal 100 MB) lädst du mit GitHub Desktop hoch.

## 8. Workflow startet automatisch
Tab **Actions**: Ein Lauf „Resource-Pack veröffentlichen“ erscheint (gelber Punkt = läuft, grüner Haken = fertig, rotes X = Fehler). Dauer: etwa 1 Minute.
Manuell starten: Actions → Workflow wählen → **Run workflow**.

## 9. Wie GitHub die Versionsnummer erhöht
`version.txt` enthält die letzte Version (zu Beginn `1.0.0`). Bei jedem Upload zählt das Skript die letzte Zahl hoch: `1.0.0 → 1.0.1 → 1.0.2 …` (nach `1.0.9` kommt `1.0.10`). Du änderst nie eine Versionsnummer selbst. Die erste veröffentlichte Version ist also `1.0.1`.

## 10. Wie die Release erstellt wird
Der Workflow prüft die ZIP (gültig, `pack.mcmeta`, keine unsicheren Pfade), berechnet den SHA-256, erstellt die Release `v1.0.1`, lädt die ZIP als Release-Datei hoch und lädt sie zur Kontrolle wieder herunter (Hash-Vergleich). Existiert die Release schon, bricht er ab. Ist die ZIP identisch zur letzten, passiert bewusst nichts.
Ansehen: Startseite des Repos → rechts **Releases**.

## 11. Wie `latest.json` aktualisiert wird
Erst **nach** erfolgreicher Release und Gegenprüfung schreibt der Workflow `latest.json` und `version.txt` neu und committet sie (Commit „Resource-Pack 1.0.1 veröffentlicht“). Schlägt vorher etwas fehl, wird eine halb fertige Release wieder gelöscht und `latest.json` bleibt unverändert.

## 12. Prüfen, ob alles funktioniert
1. Actions-Lauf ist grün. Bei rotem X: Lauf anklicken → roten Schritt öffnen → die Meldung (deutsch) lesen.
2. Unter **Releases** gibt es `v1.0.1` mit `CustomPack.zip`.
3. `latest.json` im Repo enthält `"version": "1.0.1"` und einen 64-stelligen `sha256` statt des Platzhalters.
4. Öffne im Browser `https://raw.githubusercontent.com/DEINNAME/CustomPackUpdater/main/latest.json` (mit deinem Namen) – das ist die Adresse, die die Mod liest (Änderungen können bis ca. 5 Minuten dauern).
5. Starte Minecraft mit der Mod: Im Chat (nach Weltbeitritt) erscheint „Neue Version gefunden: 1.0.1“, „Download erfolgreich!“ … Im Ordner `resourcepacks` liegt `CustomPack-1.0.1.zip`. Zweiter Start: „Du hast bereits die neueste Version.“

## 13. Später ein neues Resource-Pack veröffentlichen
1. Neue ZIP bauen (Schritt 6), **gleicher Name** `CustomPack.zip`.
2. Im Ordner `resourcepack` **Add file → Upload files** → neue ZIP hochladen (ersetzt die alte).
3. **Commit changes** – fertig. Nach ~1 Minute ist `1.0.2` veröffentlicht; Spieler bekommen es beim nächsten Start/Serverbeitritt.

## Häufige Fehlermeldungen
| Meldung | Lösung |
|---|---|
| „Im Ordner 'resourcepack' liegt keine ZIP-Datei“ | ZIP direkt in `resourcepack` hochladen |
| „…liegen 2 ZIP-Dateien“ | Alte/zusätzliche ZIP löschen |
| „In der ZIP fehlt die Datei pack.mcmeta …“ | ZIP aus dem **Inhalt** des Ordners neu erstellen |
| „Der Dateiname … ist nicht erlaubt“ | Umbenennen, z. B. `CustomPack.zip` |
| „Die Release v… existiert bereits“ | Alte Release unter *Releases* löschen oder `version.txt` prüfen |
| Push-Fehler im letzten Schritt | Branch-Schutz für `main` entfernen (Schritt 5) |
