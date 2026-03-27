# Arte Forecast for Home Assistant

Eine Custom-Integration, die beim Hinzufuegen nach kompatiblen Pflanzen-Entities sucht und daraus pro Pflanze einen eigenen Forecast-Eintrag erzeugt.

## Idee

Die Integration betrachtet:

- historische Bodenfeuchtewerte
- Spruenge nach oben als moegliche Giessereignisse
- die mittlere Austrocknungsrate zwischen zwei Giessereignissen
- optional Luftfeuchtigkeit, Temperatur und Beleuchtungsstaerke als Korrekturfaktoren
- definierte Schwellwerte fuer minimale und maximale Bodenfeuchte

Das Ergebnis ist:

- ein Timestamp-Sensor fuer den voraussichtlichen naechsten Zeitpunkt, an dem die Bodenfeuchte den Minimalwert erreicht
- ein Binary Sensor, der anzeigt, ob jetzt gegossen werden sollte

## Einrichtung

Die Integration ist jetzt fuer einen Config Flow vorbereitet. Lege den Ordner `custom_components/arte_forecast` in deine Home-Assistant-Installation und starte Home Assistant neu. Danach kannst du die Integration ueber `Einstellungen -> Geraete & Dienste -> Integration hinzufuegen` anlegen.

Beim Start des Flows sucht die Integration nach kompatiblen `plant.*`-Entities, die bereits genug Informationen fuer einen Forecast mitbringen. Fuer jede gefundene Pflanze kannst du einen separaten Eintrag anlegen. Bereits konfigurierte Pflanzen werden im Auswahl-Schritt nicht noch einmal angeboten.

## Config-Entry-Felder

- `plant_entity`: optionale Pflanzen-Entity; aus ihren Attributen koennen Sensor-Referenzen und `min/max`-Werte gelesen werden
- `soil_moisture_entity`: Bodenfeuchtesensor der Pflanze
- `min_moisture` und `max_moisture`: persoenliche Zielspanne fuer die Pflanze
- `humidity_entity`: optionaler Luftfeuchtigkeitssensor
- `temperature_entity`: optionaler Temperatursensor
- `illuminance_entity`: optionaler Lichtsensor
- `lookback_hours`: wie weit in die Vergangenheit analysiert wird
- `reset_threshold`: ab welchem Sprung ein neues Giessereignis angenommen wird
- `humidity_impact`, `temperature_impact`, `illuminance_impact`: Gewichtung der Umgebungsfaktoren

Explizit konfigurierte Entities und Schwellenwerte haben Vorrang. Wenn `plant_entity` gesetzt ist, versucht die Integration ansonsten uebliche Attributnamen wie `moisture_entity`, `temperature_entity`, `humidity_entity`, `illuminance_entity`, `min_moisture` und `max_moisture` zu verwenden.

Als kompatibel gilt aktuell eine Pflanzen-Entity, wenn sie mindestens einen Bodenfeuchtesensor sowie `min_moisture` und `max_moisture` bereitstellt.

## YAML-Beispiel

YAML bleibt als einfache Fallback-Variante nutzbar:

```yaml
sensor:
  - platform: arte_forecast
    name: Monstera watering forecast
    plant_entity: plant.monstera
    soil_moisture_entity: sensor.monstera_soil_moisture
    humidity_entity: sensor.living_room_humidity
    temperature_entity: sensor.living_room_temperature
    illuminance_entity: sensor.monstera_light_level
    min_moisture: 22
    max_moisture: 55
    lookback_hours: 168
    update_interval_minutes: 30
    reset_threshold: 4
    humidity_impact: 0.35
    temperature_impact: 0.30
    illuminance_impact: 0.20
```

## Bedeutende Attribute

- `status`: `ok`, `watering_due`, `insufficient_history` oder `missing_current_moisture`
- `hours_until_min_moisture`: Restzeit bis zum Minimalwert
- `depletion_rate_per_hour`: verwendete Austrocknungsrate nach Korrektur
- `average_segment_rate_per_hour`: reine historische Austrocknungsrate
- `ambient_temperature` und `ambient_illuminance`: verwendete Umgebungswerte
- `samples_used` und `segments_used`: hilfreich fuer das Tuning

## Naechste sinnvolle Ausbaustufen

1. Saisonale Korrektur oder Fenster fuer Sommer/Winter
2. Robusteres Modell fuer stark verrauschte Sensoren
3. Migration von YAML auf Config Entries auch fuer bestehende Installationen
4. Tests direkt gegen eine Home-Assistant-Testumgebung
