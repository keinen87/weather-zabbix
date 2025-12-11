import uvicorn
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
import requests

CITY = "Ахтубинск"

app = FastAPI()


def request_weather(city: str) -> str:
    payload = {"nMTq": "", "lang": "ru"}
    url = f"https://wttr.in/{city}"
    
    try:
        response = requests.get(url, params=payload, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"Произошла ошибка: {str(e)}"


@app.get("/", response_class=PlainTextResponse)
async def get_weather_default():
    weather = request_weather(CITY)
    return f"Погода в Ахтубинске:\n\n{weather}"


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)