# Mini Subway Surfer (Windows Forms)

Ein kleines C#-Windows-Forms-Spiel als einfache Subway-Surfer-Variante. Die Spielfigur läuft auf drei Spuren, sammelt Münzen, weicht Hindernissen aus und kann springen.

## Features

- Drei Spuren mit Links-/Rechts-Bewegung
- Sprungmechanik zum Überwinden von Hindernissen
- Zufällig spawnende Hindernisse und Münzen
- Score, Münzzähler und steigende Geschwindigkeit
- Game-Over-Zustand mit Neustart per Taste `R`

## Steuerung

| Taste | Aktion |
| --- | --- |
| `←` / `A` | Nach links wechseln |
| `→` / `D` | Nach rechts wechseln |
| `Space` / `W` / `↑` | Springen |
| `R` | Nach Game Over neu starten |

## Voraussetzungen

- Windows
- .NET 8 SDK oder neuer

## Starten

```powershell
dotnet run --project .\SubwaySurferWinForms.csproj
```

Alternativ kann das Projekt in Visual Studio geöffnet und direkt gestartet werden.
