# Programming_assignment_1

## Startup

Install python 3.12.0 <br>
Install venv `pip install virtualenv` <br>
Install Selenium: `pip install selenium` <br>
Install psycopg2: `pip install psycopg2` <br>
Install requests: `pip install requests`

First start:
`py -m venv .venv`

Activate cmd or PS to virtual env:
- In cmd.exe
`.venv\Scripts\activate.bat`
- In PowerShell
`.venv\Scripts\Activate.ps1`

Check if version in .venv is 3.12 with `py --version`

Install requirements: `pip install -r requirements.txt`

## Instalacija lokalne baze

1. Install PostgreSQL 16.2: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
    1. Izberi naj installa vse komponenteq
    2. Nastavi geslo na: "SMRPO_skG"
    3. Ko te vpraša, "Launch Stack Builder at exit?", daš klukico stran
2. Odpreš pgAdmin 4
    1. Levo odpreš "Servers" in naj bi se pojavu "PostgreSQL 16"
    2. Odpreš PostgreSQL 16 -> Databases -> postgres
    3. Klikneš na Schemas da jo izbereš. Odpreš Tools -> Query Tool. V polje, ki se odpre kopiraš kodo iz [crawldb.sql](https://github.com/kristofzupan/IEPS-Assignments/tree/main/Programming_assignment_1/crawldb.sql). Klikneš Execute Script (F5)
    4. Desni klik na Schemas in nato Refresh. Opreš Schemas in naj bi se pojavu "crawldb"
    5. Baza je narejena

3. Ta korak ni nujen, samo je lažje gledat podatke v bazi
    1. Install DbVisualizer (with Java): https://www.dbvis.com/download/ 
    2. Odpreš DbVisualizer, izbereš "Create a Database Connection" in "Create a Connection". Na seznamu izbereš PostgreSQL.
    3. Polja Authentication:\
    Database Userid: postgres\
    Password Source: From Database Password field\
    Database Password: SMRPO_skG
    4. Klikneš Connect in povežeš se z bazo.
    5. Na levi se pod Databases pojavi "postgres". V Schemas -> crawldb dvojni klik na Tables (izbereš levo opcijo, mislim da piše da ti odpre object). Lahko vidiš vsa polja. Na "References" se ti izriše še povezava med tabelami.
    6. Podatke v posamezni tabeli lahk vidiš, če izbereš tabelo (npr. Tables -> site) in na vrhu izbereš "Data"

4. Testiranje povezave
    Zaženeš datoteko [testBaze.py](https://github.com/kristofzupan/IEPS-Assignments/tree/main/Programming_assignment_1/testBaze.py). V tabelo site, se naj bi dodala ena vrstica.

## Firefox

Crawler narejen za Firefox.
Če pri instalaciji Firefoxa ni bila izbrana privzeta lokacija instalacije, jo je potrebno ročno nastaviti:
V 25. vrstici datoteke [crawler.py](https://github.com/kristofzupan/IEPS-Assignments/tree/main/Programming_assignment_1/crawler.py) je
potrebno spremeniti pot do "Firefox.exe" datoteke. Ta se mora ujemati absolutni poti do lokacije datoteke "Firefox.exe" na vašem računalniku.
Primer: `firefox_options.binary_location = r'C:\Program Files\Mozilla Firefox\firefox.exe'`

## Running

`py Programming_assignment_1/crawler.py`

## Dostop do podatkovne baze s shranjenimi podatki

Zaradi velikosti podatkovne baze smo jo shranili v dveh različicah.
    Do celotne podatkovne baze lahko dostopate na povezavi v db.txt.
    Obstaja tudi zmanjšana verzija podatkovne baze, ki ima v tabeli 'page' vsebino 'html_content' omejeno na 1000 znakov. Za dostop do nje po kloniranju repozitorija v ukaznem pozivu poženite ukaz: git lfs pull
