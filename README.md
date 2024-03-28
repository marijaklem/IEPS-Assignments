# IEPS-Assignments

## Startup

Install python 3.12.0 <br>
Install venv `pip install virtualenv`

First start:
`py -m venv .venv`

Activate cmd or PS to virtual env:
- In cmd.exe
`.venv\Scripts\activate.bat`
- In PowerShell
`.venv\Scripts\Activate.ps1`

Check if version in .venv is 3.12 with `py --version`

Install requirements: `pip install -r requirements.txt`

## Running

`py Programming_assignment_1/main.py`

In PyCharm (IntelliJ):
- Bottom right select interpreter `Add new interpreter` -> `Add local interpreter`
- Select new, select location venv python.
- Run top right with green arrow in main.py

## Adding packages

Add to `requirements.txt` -> numpy==1.26.0 (version) <br>
Run `pip install -r requirements.txt`

## DB

- Download postegreSQL 16.2
    https://www.postgresql.org/download/

- Download Docker
    https://www.docker.com/products/docker-desktop/
