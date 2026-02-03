# Docker Web Scraper

Tento projekt ukazuje jednoduchou webovou aplikaci vytvořenou pomocí **Dockeru**, **Flasku** a **Redis**.  
Cílem projektu je demonstrovat, jak lze aplikaci zabalit do kontejnerů a spouštět ji konzistentně na různých počítačích bez ohledu na lokální prostředí (v rámci předmětu *Moderní algoritmy*).

## Struktura projektu
```text
docker-web-scraper/
├── app/
│   ├── app.py              
│   └── requirements.txt   
├── Dockerfile              
├── docker-compose.yml      
└── README.md
```

## Funkcionalita

- Flask aplikace běží v samostatném Docker kontejneru.
- Redis běží v samostatném kontejneru.
- Docker Compose zajišťuje spuštění a propojení obou služeb.
- Aplikace může ukládat a číst data z databáze Redis.

[Dokumentace projektu](moderni_alg_stetinova.pdf)

```mermaid
sequenceDiagram

    title Web Scraper – Docker aplikace s Redis cache
    participant Dev
    participant Docker
    participant Flask 
    participant Redis 
    participant User 
    participant Target 


    Dev->>Dev: Vytvoření app.py
    Dev->>Dev: Vytvoření Dockerfile
    note over Dev: FROM python:3.10-slim<br>RUN pip install flask redis<br>CMD ["python", "app.py"]

    Dev->>Docker: docker-compose up
    activate Docker

    Docker->>Docker: Build image aplikace (Flask)
    Docker->>Redis: Spustí Redis container
    Docker->>Flask: Spustí Flask container
    Docker-->>Dev: Aplikace běží (port 5000)

    deactivate Docker


    User->>Flask: Zadá URL a klikne na „Diagnostikovat“
    activate Flask

    Flask->>Redis: Dotaz na cache (URL)
    alt Data nalezena v cache
        Redis-->>Flask: Vrací uložený výsledek
        Flask-->>User: Vrací výsledek (rychlá odpověď)
    else Cache miss
        Redis-->>Flask: Cache prázdná
        Flask->>Target: HTTP GET / HEAD requesty
        Target-->>Flask: HTML a HTTP hlavičky
        Flask->>Flask: Analýza HTML (BeautifulSoup)\n→ obrázky a jejich velikosti
        Flask->>Redis: Uloží výsledek do cache
        Flask-->>User: Vrací výsledky\n(čas načtení, hlavičky, počet obrázků)
    end

    deactivate Flask


    Dev->>Docker: Sleduje docker ps, docker logs, docker stop
    Docker-->>Dev: Umožní opakovatelné nasazení na jiném PC
```
