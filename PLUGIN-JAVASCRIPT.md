# LeTTo-Plugins: JavaScript im Browser

Diese Beschreibung richtet sich an Entwickler von LeTTo-Plugins. Sie beschreibt, wie das JavaScript eines Plugins
in der LeTTo-App aufgerufen wird, wie es die Eingabe an LeTTo zurückgibt und wie es auf die Einstellungen der App
(Design, Prüfen-Buttons) zugreifen kann.

Als Vorlage dient das Demo-Plugin „Uhr“ (`src/main/resources/plugins/uhr/uhrScript.js` in diesem Repository).

---

## 1. Einbinden der JavaScript-Dateien

Das Plugin gibt in seiner Java-Klasse an, welche JavaScript-Dateien LeTTo laden soll:

```java
protected String[] javascriptLibs = {"plugins/uhr/uhrScript.js", "plugins/plugintools.js"};
```

Die Dateien liefert das Plugin-Service selbst aus. `plugins/plugintools.js` mit allgemeinen Hilfsfunktionen
(Zeichnen, Skalieren, Umgebung der App, siehe Abschnitt 4) gehört zu den LeTTo-eigenen Plugin-Services
(Repository `letto-plugins`). Ein eigenes Plugin-Service (wie das Demo-Plugin „Uhr“) hat diese Datei nicht
automatisch: entweder eine Kopie unter `plugins/plugintools.js` mitliefern und in `javascriptLibs` eintragen,
oder direkt auf `window.LeTTo` zugreifen (siehe Abschnitt 4, „Ohne plugintools.js“).

## 2. Aufruf des Plugins

Nach dem Rendern der Frage ruft LeTTo eine globale Funktion mit dem Namen `initPlugin<Typ>` auf, z. B.
`initPluginUhr` für den Plugin-Typ `Uhr`:

```js
function initPluginUhr(dtoString, active) { ... }
```

| Parameter | Bedeutung |
|---|---|
| `dtoString` | Plugin-DTO als JSON-String (`JSON.parse(dtoString)`) |
| `active` | `true`: der Schüler darf eingeben. `false`: nur anzeigen (z. B. Lösungsansicht, abgegebener Test) |

Wichtige Felder des DTO:

| Feld | Bedeutung |
|---|---|
| `tagName` | eindeutiger Name des Plugins in der Frage – Grundlage für die Element-Namen (siehe unten) |
| `jsonData` | plugin-spezifische Daten als JSON-String (`JSON.parse(dto.jsonData)`) |
| `imageUrl` | URL eines vom Plugin-Service erzeugten Bildes |
| `width`, `height` | Größe der Darstellung in Pixel |

**Regel:** Alle Hilfsfunktionen des Plugins als innere Funktionen von `initPlugin<Typ>` anlegen. Die Funktion kann
für mehrere Plugins einer Seite und mehrfach für dieselbe Frage aufgerufen werden (z. B. nach einem Neuladen).

## 3. Darstellung und Rückgabe der Eingabe

LeTTo gibt zwei Elemente vor:

| Element | Selektor | Verwendung |
|---|---|---|
| Container | `"#" + dto.tagName + "_div"` | hier rendert das Plugin seine Darstellung (z. B. ein Canvas) |
| Eingabe | `"." + dto.tagName + "_inp"` | verstecktes Textfeld: hier steht die bisherige Antwort, hier schreibt das Plugin die neue Antwort hinein |

Das Plugin liest beim Start die bisherige Antwort aus dem Textfeld und schreibt jede Änderung als Text (oder JSON)
in dessen `value`. LeTTo übernimmt den Inhalt automatisch (Abfrage etwa alle 500 ms) und übergibt ihn zum Beurteilen
an den Plugin-Service. Ist `active` `false`, darf das Plugin keine Eingaben annehmen.

```js
const plugin_div = "#" + dto.tagName + "_div";
const plugin_inp = "." + dto.tagName + "_inp";
let eingabe = $(plugin_inp)[0];
let bisher = eingabe.value;          // bisherige Antwort
eingabe.value = neueAntwort;         // neue Antwort an LeTTo übergeben
```

## 4. Umgebung der App: Design und Prüfen-Buttons (`window.LeTTo`)

Die LeTTo-App stellt das Objekt `window.LeTTo` bereit. Darüber kann das Plugin z. B. seine Farben an das gewählte
Design anpassen oder erkennen, ob der Schüler die Frage während des Tests prüfen lassen kann.

| Feld | Bedeutung |
|---|---|
| `theme` | gewähltes Design: `default`, `theme-soft-light`, `theme-soft-dark`, `theme-dark`, `theme-high-contrast` |
| `dunkel` | `true` bei dunklem Design (`theme-dark`, `theme-soft-dark`) |
| `kontrast` | `true` bei hohem Kontrast (`theme-high-contrast`) |
| `farben` | aktuelle Farben des Designs: `text`, `hintergrund`, `primary`, `rahmen` (CSS-Farbwerte, z. B. `#ffffff`) |
| `pruefen` | `true`, wenn zur Frage ein Prüfen-Button angezeigt wird |
| `pruefenButtons` | angezeigte Prüfen-Buttons: `check` (Prüfen), `check_next` (Prüfen und weiter), `check_penalty` (Prüfen mit Abzug), in der Beispielsammlung `bp_score` |
| `modus` | Modus der Frage: `test` (Test/Übung), `bp` (Beispielsammlung, Vorschau), `result` (Ergebnisansicht) u. a. |

Wann ist `pruefen` wahr?

- in der Beispielsammlung und der Fragenvorschau (`modus` = `bp`): immer,
- im Test (`modus` = `test`): wenn die Frage einen der Prüfen-Buttons hat (abhängig von den Einstellungen der
  Aktivität, z. B. Übung mit Prüfen) und sie nicht bereits vom Lehrer manuell beurteilt wurde,
- sonst (Ergebnisansicht usw.): nie.

Die Werte sind gesetzt, **bevor** `initPlugin<Typ>` aufgerufen wird. Das Objekt bleibt während der ganzen Sitzung
dasselbe; seine Werte werden aktualisiert. Bei jeder Änderung (z. B. Wechsel des Designs) löst die App das Ereignis
`letto-umgebung` auf `window` aus, `event.detail` enthält eine Kopie der Werte.

### Hilfsfunktionen in `plugintools.js`

Statt direkt auf `window.LeTTo` zuzugreifen, sollten die Hilfsfunktionen verwendet werden. Sie funktionieren auch
dort, wo es `window.LeTTo` nicht gibt (ältere LeTTo-Oberflächen, Plugin-Tester), und liefern dann Standardwerte –
`lettoPruefen()` liefert in diesem Fall `null` (unbekannt).

| Funktion | Ergebnis |
|---|---|
| `lettoUmgebung()` | alle Werte als Objekt (Felder wie oben) |
| `lettoTheme()` | Name des Designs |
| `lettoDunkel()` | `true` bei dunklem Design |
| `lettoPruefen()` | `true`/`false`, `null` wenn unbekannt |
| `lettoOnUmgebung(callback)` | ruft `callback(umgebung)` bei jeder Änderung auf, liefert eine Funktion zum Abmelden |

### Ohne plugintools.js

`window.LeTTo` fehlt in älteren LeTTo-Oberflächen und im Plugin-Tester. Deshalb immer mit Rückfallwerten lesen:

```js
function umgebung() {
    const standard = {theme: 'default', dunkel: false, kontrast: false,
        farben: {text: '', hintergrund: '', primary: '', rahmen: ''},
        pruefen: null, pruefenButtons: [], modus: ''};
    return (window.LeTTo && typeof window.LeTTo === 'object') ? Object.assign({}, standard, window.LeTTo) : standard;
}
window.addEventListener('letto-umgebung', e => zeichne(e.detail));   // Änderungen
```

### Beispiel (mit plugintools.js)

```js
function initPluginBeispiel(dtoString, active) {
    const dto = JSON.parse(dtoString);
    const plugin_div = "#" + dto.tagName + "_div";

    function zeichne(u) {
        const farbe = u.dunkel ? (u.farben.text || '#ffffff') : '#000000';
        // ... Darstellung mit farbe in plugin_div zeichnen
    }

    zeichne(lettoUmgebung());

    // Bei Designwechsel neu zeichnen
    const abmelden = lettoOnUmgebung(u => zeichne(u));

    // Eigene Rückmeldung nur anbieten, wenn LeTTo keinen Prüfen-Button zeigt
    if (lettoPruefen() === false) {
        // ...
    }
}
```

## 5. Hinweise

- jQuery steht zur Verfügung (`$`). Das Demo-Plugin sichert das mit `try { $ = jQuery; } catch (e) {}` ab.
- Element-IDs und CSS-Klassen immer mit `dto.tagName` bilden, damit mehrere Plugins auf einer Seite nicht kollidieren.
- Breite an den verfügbaren Platz anpassen (kleine Bildschirme): `imagescale(plugin, dto, prozent)` aus
  `plugintools.js` berechnet die Skalierung aus der Breite des Containers.
- Fehler im Plugin-JavaScript fängt LeTTo ab, sie verhindern aber die Darstellung des Plugins – zum Testen die
  Browser-Konsole verwenden. Für eigene Tests gibt es den LeTTo Plugin-Tester (siehe `README.md`).
- Die REST-Schnittstelle zwischen LeTTo und dem Plugin-Service (Beurteilen, Bild erzeugen, Konfiguration) ist in
  der Swagger-Doku des Demo-Plugins beschrieben (siehe `README.md`).
