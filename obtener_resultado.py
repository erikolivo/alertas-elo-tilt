from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional

import requests

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
ZONA_ECUADOR = ZoneInfo("America/Guayaquil")


def _mapear_estado(state: str, description: str) -> str:
    desc_lower = description.lower() if description else ""
    if state == "post":
        if "suspended" in desc_lower:
            return "suspendido"
        return "finalizado"
    if state == "in":
        if "suspended" in desc_lower:
            return "suspendido"
        return "en_curso"
    if state == "pre":
        if "postponed" in desc_lower:
            return "pospuesto"
        return "pendiente"
    return "pendiente"


def _extraer_competidores(competitors: list) -> dict:
    resultado = {"goles": None, "local": None, "visitante": None}
    for c in competitors:
        ha = c.get("homeAway")
        score = c.get("score")
        if ha == "home":
            resultado["local"] = score
        elif ha == "away":
            resultado["visitante"] = score
    if resultado["local"] is not None and resultado["visitante"] is not None:
        resultado["goles"] = f"{resultado['local']}-{resultado['visitante']}"
    return resultado


def _desde_summary(fixture_id: str, liga_slug: str) -> Optional[dict]:
    url = f"{ESPN_BASE}/{liga_slug}/summary?event={fixture_id}"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        comp = data.get("competitions", [{}])[0]
        status = comp.get("state", {})
        state = status.get("type", {}).get("state", "")
        description = status.get("type", {}).get("description", "")
        categoria = _mapear_estado(state, description)
        comps = comp.get("competitors", [])
        info = _extraer_competidores(comps)
        return {
            "categoria": categoria,
            "descripcion": description,
            "goles": info["goles"],
            "ganador": _determinar_ganador(comps),
        }
    except Exception:
        return None


def _desde_scoreboard(fixture_id: str, fecha_str: str) -> Optional[dict]:
    try:
        fecha_dt = datetime.fromisoformat(fecha_str)
        fecha_fmt = fecha_dt.strftime("%Y%m%d")
    except Exception:
        return None

    url = f"{ESPN_BASE}/all/scoreboard?dates={fecha_fmt}"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        for event in data.get("events", []):
            if str(event.get("id")) == str(fixture_id):
                comp = event.get("competitions", [{}])[0]
                status = comp.get("status", {}).get("type", {})
                state = status.get("state", "")
                description = status.get("description", "")
                categoria = _mapear_estado(state, description)
                comps = comp.get("competitors", [])
                info = _extraer_competidores(comps)
                return {
                    "categoria": categoria,
                    "descripcion": description,
                    "goles": info["goles"],
                    "ganador": _determinar_ganador(comps),
                }
    except Exception:
        pass
    return None


def _determinar_ganador(competitors: list) -> Optional[str]:
    local_score = None
    visitante_score = None
    for c in competitors:
        ha = c.get("homeAway")
        try:
            score = int(c.get("score", 0))
        except (ValueError, TypeError):
            score = 0
        if ha == "home":
            local_score = score
        elif ha == "away":
            visitante_score = score

    if local_score is None or visitante_score is None:
        return None
    if local_score > visitante_score:
        return "local"
    if visitante_score > local_score:
        return "visitante"
    return "empate"


def consultar(fixture_id: str, liga_slug: str, fecha: Optional[str] = None) -> dict:
    resultado = _desde_summary(fixture_id, liga_slug)
    if resultado is not None:
        return resultado

    if liga_slug == "all" and fecha:
        resultado = _desde_scoreboard(fixture_id, fecha)
        if resultado is not None:
            return resultado

    if fecha:
        resultado = _desde_scoreboard(fixture_id, fecha)
        if resultado is not None:
            return resultado

    return {
        "categoria": "pendiente",
        "descripcion": "No encontrado",
        "goles": None,
        "ganador": None,
    }
