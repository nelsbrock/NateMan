# NateMan

NateMan (**Na**chschreib**te**rmin-**Man**ager) ist eine Webanwendung zur Koordination von Klausuren gymnasialer Oberstufen. Klausurpläne können aus verschiedenen Formaten (z.B. Kurs42, bald auch UNTIS) importiert oder direkt im Webinterface erstellt werden und sind anschließend öffentlich einsehbar. Über eigene Lehrerkonten können Klausuraufsichten nach einer Klausur Versäumnisse eintragen. Beratungslehrer und Oberstufenkoordinatoren können diese Bearbeitungen einsehen, bei Bedarf ändern und Atteste für Versäumnisse eintragen.

![Klausurliste in NateMan](./screenshots/klausurliste.png)

## Funktionen
* Import und Bearbeitung von Klausurlisten (aus Kurs42, bald auch UNTIS)
* administrierbares Anmeldesystem für Lehrkräfte
* Eintragung von Klausurversäumnissen und Attesten
* Einsicht und Export (Excel) von Versäumnislisten
* Klausurerinnerungen per E-Mail
* öffentlich einsehbare Klausurpläne

## Installation
NateMan kann wie jede andere Flask-App installiert werden.

Nach dem ersten Start wird automatisch eine ausführlich kommentierte Konfigurationsdatei `config.yml` angelegt. Hier müssen die Einträge `server-name` sowie `uses-ssl` entsprechend angepasst werden. Für die Nutzung des E-Mail-Versands müssen auch die Einträge unter `mail` geändert werden.

Die erste Einrichtung erfolgt über den CLI-Befehl `nateman`. Um ein neues Lehrerkonto mit Administratorrechten anzulegen, führen Sie `nateman add-lehrer --admin <KÜRZEL>` aus. Mit diesem Konto können Sie sich anschließend im Webinterface anmelden.
