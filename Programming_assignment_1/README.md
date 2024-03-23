## Startup

Install Selenium: `pip install selenium`

## Firefox

Crawler narejen za Firefox.
Če pri instalaciji Firefoxa ni bila izbrana privzeta lokacija instalacije, jo je potrebno ročno nastaviti:
V 25. vrstici datoteke [crawler.py](https://github.com/kristofzupan/IEPS-Assignments/tree/main/Programming_assignment_1/crawler.py) je
potrebno spremeniti pot do "Firefox.exe" datoteke. Ta se mora ujemati absolutni poti do lokacije datoteke "Firefox.exe" na vašem računalniku.
Primer: `firefox_options.binary_location = r'C:\Program Files\Mozilla Firefox\firefox.exe'`