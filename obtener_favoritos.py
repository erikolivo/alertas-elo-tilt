import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

import requests

ELO_TILT_URL = (
    "https://raw.githubusercontent.com/erikolivo/elo-tilt/master/data/"
    "predicciones_cache.json"
)
ZONA_ECUADOR = ZoneInfo("America/Guayaquil")

_cache: Optional[dict] = None


def _fetch_predicciones() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    resp = requests.get(ELO_TILT_URL, timeout=30)
    resp.raise_for_status()
    _cache = resp.json()
    return _cache


def _parse_fecha(fecha_str: str) -> datetime:
    return datetime.fromisoformat(fecha_str)


def partidos_entre(inicio: datetime, fin: datetime) -> list[dict]:
    data = _fetch_predicciones()
    resultado = []
    for p in data.get("predicciones", []):
        fecha = _parse_fecha(p["fecha"])
        if inicio <= fecha < fin:
            resultado.append(p)
    return resultado


def partido_por_id(fixture_id: str) -> Optional[dict]:
    data = _fetch_predicciones()
    for p in data.get("predicciones", []):
        if p["fixture_id"] == fixture_id:
            return p
    return None


def margen(prediccion: dict) -> float:
    valores = sorted(
        [prediccion["prob_local"], prediccion["prob_empate"], prediccion["prob_visitante"]],
        reverse=True,
    )
    return valores[0] - valores[1]


def favorito(prediccion: dict) -> str:
    probs = {
        "local": prediccion["prob_local"],
        "empate": prediccion["prob_empate"],
        "visitante": prediccion["prob_visitante"],
    }
    return max(probs, key=probs.get)


def rating_confiable(equipo: dict) -> bool:
    return equipo["partidos_jugados"] >= 3


def es_favorito_claro_para_enviar(partido: dict) -> bool:
    return (
        margen(partido["prediccion"]) >= 45
        and rating_confiable(partido["equipo_local"])
        and rating_confiable(partido["equipo_visitante"])
    )


def califica_para_historial(partido: dict) -> bool:
    return (
        margen(partido["prediccion"]) >= 40
        and rating_confiable(partido["equipo_local"])
        and rating_confiable(partido["equipo_visitante"])
    )


def es_sorpresa(partido: dict, resultado_real: str) -> bool:
    m = margen(partido["prediccion"])
    favorito_predicho = favorito(partido["prediccion"])
    return (
        20 <= m < 30
        and rating_confiable(partido["equipo_local"])
        and rating_confiable(partido["equipo_visitante"])
        and resultado_real != favorito_predicho
    )
