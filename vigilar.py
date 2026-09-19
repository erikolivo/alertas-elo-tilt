import os
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import obtener_favoritos
import obtener_resultado
import ventanas
import telegram_utils

ZONA_ECUADOR = ZoneInfo("America/Guayaquil")
RUTA_HISTORIAL = "data/historial"
RUTA_SORPRESAS = "data/sorpresas"


def _cargar_json_ruta(ruta: str, default=None) -> dict:
    if not os.path.exists(ruta):
        return default if default is not None else {}
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def _guardar_json_ruta(ruta: str, contenido: dict):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(contenido, f, ensure_ascii=False, indent=2)


def _ruta_historial(ahora: datetime) -> str:
    return f"{RUTA_HISTORIAL}/{ahora.strftime('%Y-%m')}.json"


def _ruta_sorpresas(ahora: datetime) -> str:
    return f"{RUTA_SORPRESAS}/{ahora.strftime('%Y-%m')}.json"


def _archivar_historial(entrada: dict, ruta: str):
    data = _cargar_json_ruta(ruta, default={"ventanas": []})
    data["ventanas"].append(entrada)
    _guardar_json_ruta(ruta, data)


def _archivar_sorpresa(entrada: dict, ruta: str):
    data = _cargar_json_ruta(ruta, default={"sorpresas": []})
    data["sorpresas"].append(entrada)
    _guardar_json_ruta(ruta, data)


def _construir_entrada_historial(
    partido: dict, resultado: dict, fue_enviado: bool
) -> dict:
    pred = partido["prediccion"]
    fav = obtener_favoritos.favorito(pred)
    m = obtener_favoritos.margen(pred)
    conf = partido.get("confianza", 0)
    cat = resultado.get("categoria", "pendiente")
    goles = resultado.get("goles") if cat == "finalizado" else None
    ganador = resultado.get("ganador") if cat == "finalizado" else None
    acierto = ganador == fav if ganador else None

    return {
        "fixture_id": partido["fixture_id"],
        "liga_slug": partido.get("liga_slug", ""),
        "equipo_local": partido["equipo_local"]["nombre"],
        "equipo_visitante": partido["equipo_visitante"]["nombre"],
        "favorito_predicho": fav,
        "margen": round(m, 1),
        "confianza_elo": conf,
        "enviada": fue_enviado,
        "resultado_categoria": cat,
        "resultado": ganador,
        "goles": goles,
        "acierto": acierto,
    }


def _construir_entrada_sorpresa(partido: dict, resultado: dict) -> dict:
    pred = partido["prediccion"]
    fav = obtener_favoritos.favorito(pred)
    m = obtener_favoritos.margen(pred)
    return {
        "fixture_id": partido["fixture_id"],
        "fecha": partido["fecha"],
        "liga_slug": partido.get("liga_slug", ""),
        "equipo_local": partido["equipo_local"]["nombre"],
        "equipo_visitante": partido["equipo_visitante"]["nombre"],
        "favorito_predicho": fav,
        "margen": round(m, 1),
        "resultado": resultado.get("ganador"),
        "goles": resultado.get("goles"),
    }


def _procesar_cierre_ventana(
    clave: str,
    ventana: dict,
    resultados: dict,
    ahora: datetime,
):
    ruta_hist = _ruta_historial(ahora)
    ruta_sorp = _ruta_sorpresas(ahora)

    for fixture_id in ventana["fixture_ids"]:
        partido = obtener_favoritos.partido_por_id(fixture_id)
        if partido is None:
            entrada_hist = {
                "fixture_id": fixture_id,
                "liga_slug": "",
                "equipo_local": "?",
                "equipo_visitante": "?",
                "favorito_predicho": "?",
                "margen": 0,
                "confianza_elo": 0,
                "enviada": fixture_id in ventana["favoritos_alertados"],
                "resultado_categoria": "pospuesto",
                "resultado": None,
                "goles": None,
                "acierto": None,
            }
            _archivar_historial(entrada_hist, ruta_hist)
            continue

        r = resultados.get(fixture_id, {})
        m = obtener_favoritos.margen(partido["prediccion"])
        fue_enviado = fixture_id in ventana["favoritos_alertados"]

        if obtener_favoritos.califica_para_historial(partido):
            entrada_hist = _construir_entrada_historial(partido, r, fue_enviado)
            _archivar_historial(entrada_hist, ruta_hist)

        if (
            r.get("categoria") == "finalizado"
            and obtener_favoritos.es_sorpresa(partido, r.get("ganador"))
        ):
            entrada_sorp = _construir_entrada_sorpresa(partido, r)
            _archivar_sorpresa(entrada_sorp, ruta_sorp)

    partidos_alertados = [
        fid for fid in ventana["fixture_ids"] if fid in ventana["favoritos_alertados"]
    ]
    if partidos_alertados:
        partidos_completos = {}
        for fid in partidos_alertados:
            p = obtener_favoritos.partido_por_id(fid)
            if p:
                partidos_completos[fid] = p
        mensajes = telegram_utils.formatear_resultados(
            partidos_alertados, resultados, partidos_completos
        )
        for m in mensajes:
            telegram_utils.enviar(m)


def ciclo():
    ahora = datetime.now(tz=ZONA_ECUADOR)
    estado = ventanas.cargar_estado()
    print(f"[CICLO] {ahora.isoformat()}")

    # PASO A — Anunciar ventana nueva
    sig = ventanas.siguiente_hora(ahora)
    clave = sig.isoformat()
    diff_min = (sig - ahora).total_seconds() / 60
    print(f"[PASO A] Siguiente ventana: {clave} ({diff_min:.1f} min)")
    if ventanas.debe_anunciar(ahora, clave, estado):
        print(f"[PASO A] Anunciando ventana {clave}")
        todos = obtener_favoritos.partidos_entre(sig, sig + timedelta(hours=1))
        print(f"[PASO A] {len(todos)} partidos en ventana")
        favoritos_claros = [p for p in todos if obtener_favoritos.es_favorito_claro_para_enviar(p)]
        print(f"[PASO A] {len(favoritos_claros)} favoritos claros")

        if favoritos_claros:
            mensajes = telegram_utils.formatear_anuncio(favoritos_claros)
            print(f"[TELEGRAM] Enviando {len(mensajes)} mensajes de anuncio")
            for msg in mensajes:
                print(f"[TELEGRAM] Longitud mensaje: {len(msg)}")
                telegram_utils.enviar(msg)
        else:
            print("[PASO A] Sin favoritos claros, no se envia nada")

        ventanas.registrar_ventana(
            estado,
            clave,
            ahora,
            [p["fixture_id"] for p in todos],
            [p["fixture_id"] for p in favoritos_claros],
        )
        print(f"[PASO A] Ventana registrada: {len(todos)} fixtures, {len(favoritos_claros)} alertados")
    else:
        print(f"[PASO A] No toca anunciar (faltan {diff_min:.1f} min o ya existe)")

    # PASO B — Cerrar ventanas abiertas
    for clave_ventana, ventana in list(estado["ventanas"].items()):
        if not ventanas.ventana_listo_para_cerrar(ventana, ahora):
            continue

        ventanas.registrar_intento_cierre(ventana, ahora)

        resultados = {}
        for fixture_id in ventana["fixture_ids"]:
            partido = obtener_favoritos.partido_por_id(fixture_id)
            liga = ventanas.liga_slug_de(partido) if partido else "all"
            fecha = partido["fecha"] if partido else None
            resultados[fixture_id] = obtener_resultado.consultar(fixture_id, liga, fecha)

        todos_resueltos = all(
            r["categoria"] == "finalizado" for r in resultados.values()
        )

        if todos_resueltos or ventana["intentos_cierre"] >= 4:
            _procesar_cierre_ventana(clave_ventana, ventana, resultados, ahora)
            ventanas.cerrar_ventana(ventana, ahora)

    # PASO C — Housekeeping
    ventanas.podar_ventanas_viejas(estado, ahora)
    ventanas.guardar_estado(estado)

    heartbeat_ruta = "data/.heartbeat"
    os.makedirs("data", exist_ok=True)
    with open(heartbeat_ruta, "a", encoding="utf-8") as f:
        pass


if __name__ == "__main__":
    ciclo()
