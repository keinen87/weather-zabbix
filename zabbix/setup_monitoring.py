#!/usr/bin/env python3
import time
import requests
import json
import sys

ZABBIX_URL = "http://localhost:8080"
ZABBIX_USER = "Admin"
ZABBIX_PASSWORD = "zabbix"
WEATHER_APP_URL = "http://localhost:8000"


def wait_for_zabbix():
    print("Ожидание запуска Zabbix...")
    for i in range(30):
        try:
            response = requests.get(f"{ZABBIX_URL}/")
            if response.status_code == 200:
                print("Zabbix запущен!")
                return True
        except:
            pass
        print(f"Попытка {i+1}/30...")
        time.sleep(10)
    return False


def get_auth_token():
    payload = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {
            "username": ZABBIX_USER,
            "password": ZABBIX_PASSWORD
        },
        "id": 1,
        "auth": None
    }
    
    response = requests.post(
        f"{ZABBIX_URL}/api_jsonrpc.php",
        headers={"Content-Type": "application/json-rpc"},
        data=json.dumps(payload),
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        if "result" in result:
            return result["result"]
        else:
            print(f"Ошибка API: {result}")
    
    raise Exception(f"Ошибка аутентификации: {response.text}")

def get_host_group_id(auth_token):
    payload = {
        "jsonrpc": "2.0",
        "method": "hostgroup.get",
        "params": {
            "output": ["groupid", "name"],
            "filter": {"name": "Linux servers"}
        },
        "auth": auth_token,
        "id": 2
    }
    
    response = requests.post(
        f"{ZABBIX_URL}/api_jsonrpc.php",
        headers={"Content-Type": "application/json-rpc"},
        data=json.dumps(payload),
        timeout=30
    )
    
    result = response.json()
    
    if "result" in result and len(result["result"]) > 0:
        return result["result"][0]["groupid"]
    else:
        # Если группа не найдена, создаем новую
        return create_host_group(auth_token)

def create_host_group(auth_token):
    payload = {
        "jsonrpc": "2.0",
        "method": "hostgroup.create",
        "params": {
            "name": "Weather Services"
        },
        "auth": auth_token,
        "id": 3
    }
    
    response = requests.post(
        f"{ZABBIX_URL}/api_jsonrpc.php",
        headers={"Content-Type": "application/json-rpc"},
        data=json.dumps(payload),
        timeout=30
    )
    
    result = response.json()
    
    if "result" in result:
        return result["result"]["groupids"][0]
    else:
        print(f"Ошибка создания группы: {result}")
        return "2"  # Fallback to default Linux servers group

def create_http_check(auth_token):
    group_id = get_host_group_id(auth_token)
    host_payload = {
        "jsonrpc": "2.0",
        "method": "host.create",
        "params": {
            "host": "Weather Application",
            "name": "Weather Application",
            "interfaces": [
                {
                    "type": 1,
                    "main": 1,
                    "useip": 0,
                    "ip": "",
                    "dns": "weather-app",
                    "port": "8000"
                }
            ],
            "groups": [
                {
                    "groupid": group_id
                }
            ]
        },
        "auth": auth_token,
        "id": 4
    }
    
    response = requests.post(
        f"{ZABBIX_URL}/api_jsonrpc.php",
        headers={"Content-Type": "application/json-rpc"},
        data=json.dumps(host_payload),
        timeout=30
    )
    
    result = response.json()
    
    if "error" in result:
        print(f"Предупреждение при создании хоста: {result['error']}")
        print("Попытка найти существующий хост...")
        return find_and_update_existing_host(auth_token, group_id)
    
    host_id = result["result"]["hostids"][0]
    print(f"Хост создан с ID: {host_id}")
    
    http_payload = {
        "jsonrpc": "2.0",
        "method": "httptest.create",
        "params": {
            "name": "Weather App Availability",
            "hostid": host_id,
            "delay": "30s",
            "steps": [
                {
                    "name": "Check main page",
                    "url": WEATHER_APP_URL,
                    "status_codes": "200",
                    "no": 1,
                    "timeout": "10s"
                }
            ]
        },
        "auth": auth_token,
        "id": 5
    }
    
    response = requests.post(
        f"{ZABBIX_URL}/api_jsonrpc.php",
        headers={"Content-Type": "application/json-rpc"},
        data=json.dumps(http_payload),
        timeout=30
    )
    
    result = response.json()
    
    if "error" in result:
        print(f"Ошибка создания HTTP check: {result['error']}")
        return False
    
    print("HTTP check успешно создан!")
    return True


def find_and_update_existing_host(auth_token, group_id):
    payload = {
        "jsonrpc": "2.0",
        "method": "host.get",
        "params": {
            "output": ["hostid", "host", "name"],
            "filter": {"host": "Weather Application"}
        },
        "auth": auth_token,
        "id": 6
    }
    
    response = requests.post(
        f"{ZABBIX_URL}/api_jsonrpc.php",
        headers={"Content-Type": "application/json-rpc"},
        data=json.dumps(payload),
        timeout=30
    )
    
    result = response.json()
    
    if "result" in result and len(result["result"]) > 0:
        host_id = result["result"][0]["hostid"]
        print(f"Найден существующий хост с ID: {host_id}")
        
        update_payload = {
            "jsonrpc": "2.0",
            "method": "host.update",
            "params": {
                "hostid": host_id,
                "groups": [{"groupid": group_id}]
            },
            "auth": auth_token,
            "id": 7
        }
        
        response = requests.post(
            f"{ZABBIX_URL}/api_jsonrpc.php",
            headers={"Content-Type": "application/json-rpc"},
            data=json.dumps(update_payload),
            timeout=30
        )
        
        result = response.json()
        
        if "error" in result:
            print(f"Ошибка обновления хоста: {result['error']}")
        
        return create_web_scenario_for_existing_host(auth_token, host_id)
    
    return False

def create_web_scenario_for_existing_host(auth_token, host_id):
    """Создать веб-сценарий для существующего хоста"""
    payload = {
        "jsonrpc": "2.0",
        "method": "httptest.get",
        "params": {
            "output": ["httptestid", "name"],
            "hostids": [host_id],
            "filter": {"name": "Weather App Availability"}
        },
        "auth": auth_token,
        "id": 8
    }
    
    response = requests.post(
        f"{ZABBIX_URL}/api_jsonrpc.php",
        headers={"Content-Type": "application/json-rpc"},
        data=json.dumps(payload),
        timeout=30
    )
    
    result = response.json()
    
    if "result" in result and len(result["result"]) > 0:
        print("Веб-сценарий уже существует")
        return True
    
    http_payload = {
        "jsonrpc": "2.0",
        "method": "httptest.create",
        "params": {
            "name": "Weather App Availability",
            "hostid": host_id,
            "delay": "30s",
            "steps": [
                {
                    "name": "Check main page",
                    "url": WEATHER_APP_URL,
                    "status_codes": "200",
                    "no": 1,
                    "timeout": "10s"
                }
            ]
        },
        "auth": auth_token,
        "id": 9
    }
    
    response = requests.post(
        f"{ZABBIX_URL}/api_jsonrpc.php",
        headers={"Content-Type": "application/json-rpc"},
        data=json.dumps(http_payload),
        timeout=30
    )
    
    result = response.json()
    
    if "error" in result:
        print(f"Ошибка создания веб-сценария: {result['error']}")
        return False
    
    print("Веб-сценарий успешно создан для существующего хоста!")
    return True

def main():
    print("=" * 60)
    print("Настройка мониторинга веб-приложения погоды в Zabbix")
    print("=" * 60)
    
    if not wait_for_zabbix():
        print("❌ Не удалось дождаться запуска Zabbix")
        print("Проверьте, что Zabbix запущен: docker-compose ps")
        sys.exit(1)
    
    try:
        print("\n🔑 Аутентификация в Zabbix...")
        auth_token = get_auth_token()
        print("✅ Успешная аутентификация!")
        
        print("\n⚙️ Настройка мониторинга веб-приложения...")
        if create_http_check(auth_token):
            print("\n✅ Настройка завершена успешно!")
            print("\nДоступ к сервисам:")
            print(f"  • Веб-приложение погоды: http://localhost:8000")
            print(f"  • Zabbix веб-интерфейс: http://localhost:8080")
            print(f"    Логин: Admin | Пароль: zabbix")
            print("\nМониторинг настроен на проверку:")
            print(f"  • URL: {WEATHER_APP_URL}")
            print(f"  • Интервал: 30 секунд")
            print(f"  • Ожидаемый HTTP статус: 200")
        else:
            print("❌ Ошибка при настройке мониторинга")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()