# Weather app

## Create .env

```txt
POSTGRES_USER=zabbix
POSTGRES_PASSWORD=zabbix
POSTGRES_DB=zabbix

TIMEZONE=Europe/Astrakhan

ZBX_SERVER_HOST=zabbix-server
```

## Run

```bash
docker-compose up -d
python3 setup_monitoring.py
```

## Links

Weather app web-interface: [http://localhost:8000](http://localhost:8000)

Zabbix -interface: [http://localhost:8080](http://localhost:8080)

