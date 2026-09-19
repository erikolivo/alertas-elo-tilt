import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

ZONA_ECUADOR = ZoneInfo("America/Guayaquil")
RUTA_ESTADO = "data/estado_ventanas.json"


def _cargar_json(ruta: str, default=None) -> dict:
    if not os.path.exists(ruta):
        return default if default is not None else {}
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def _guardar_json(ruta: str, contenido: dict):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(contenido, f, ensure_ascii=False, indent=2)


def cargar_estado() -> dict:
    return _cargar_json(RUTA_ESTADO, default={"ventanas": {}})


def guardar_estado(estado: dict):
    _guardar_json(RUTA_ESTADO, estado)


def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s)


def siguiente_hora(ahora: datetime) -> datetime:
    base = ahora.replace(minute=0, second=0, microsecond=0)
    return base + timedelta(hours=1)


def debe_anunciar(ahora: datetime, clave: str, estado: dict) -> bool:
    if clave in estado["ventanas"]:
        return False
    sig = parse_iso(clave)
    return (sig - ahora) <= timedelta(minutes=15)


def registrar_ventana(
    estado: dict,
    clave: str,
    ahora: datetime,
    fixture_ids: list[str],
    favoritos_alertados: list[str],
):
    estado["ventanas"][clave] = {
        "anunciada": True,
        "anunciada_en": ahora.isoformat(),
        "fixture_ids": fixture_ids,
        "favoritos_alertados": favoritos_alertados,
        "cerrada": False,
        "cerrada_en": None,
        "intentos_cierre": 0,
        "ultimo_intento_cierre": None,
    }


def ventana_listo_para_cerrar(ventana: dict, ahora: datetime) -> bool:
    if not ventana["anunciada"] or ventana["cerrada"]:
        return False
    anunciada_en = parse_iso(ventana["anunciada_en"])
    if (ahora - anunciada_en) < timedelta(hours=2.5):
        return False
    if ventana["ultimo_intento_cierre"]:
        ultimo = parse_iso(ventana["ultimo_intento_cierre"])
        if (ahora - ultimo) < timedelta(minutes=30):
            return False
    return True


def registrar_intento_cierre(ventana: dict, ahora: datetime):
    ventana["ultimo_intento_cierre"] = ahora.isoformat()
    ventana["intentos_cierre"] += 1


def cerrar_ventana(ventana: dict, ahora: datetime):
    ventana["cerrada"] = True
    ventana["cerrada_en"] = ahora.isoformat()


def podar_ventanas_viejas(estado: dict, ahora: datetime):
    claves_a_borrar = []
    for clave, v in estado["ventanas"].items():
        if v["cerrada"] and v["cerrada_en"]:
            cerrada_en = parse_iso(v["cerrada_en"])
            if (ahora - cerrada_en) > timedelta(days=3):
                claves_a_borrar.append(clave)
    for clave in claves_a_borrar:
        del estado["ventanas"][clave]


def liga_slug_de(partido: dict) -> str:
    return partido.get("liga_slug", "all")
