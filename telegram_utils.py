import os
import requests

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
TANDA_MAXIMA = 8


def _token() -> str:
    return os.environ.get("TELEGRAM_BOT_TOKEN", "")


def _chat_id() -> str:
    return os.environ.get("TELEGRAM_CHAT_ID", "")


def enviar(mensaje: str):
    import sys
    token = _token()
    chat_id = _chat_id()
    if not token or not chat_id:
        print(f"[TELEGRAM] Token o chat_id no configurado.", flush=True)
        return
    url = TELEGRAM_API.format(token=token)
    payload = {"chat_id": chat_id, "text": mensaje}
    try:
        print(f"[TELEGRAM] Enviando a chat {chat_id}... ({len(mensaje)} chars)", flush=True)
        resp = requests.post(url, json=payload, timeout=30)
        print(f"[TELEGRAM] Status: {resp.status_code}", flush=True)
        if resp.status_code != 200:
            print(f"[TELEGRAM] Respuesta: {resp.text[:300]}", flush=True)
    except Exception as e:
        print(f"[TELEGRAM] Error: {type(e).__name__}: {e}", flush=True)
        sys.stdout.flush()


def formatear_anuncio(partidos: list[dict]) -> list[str]:
    if not partidos:
        return []

    def abs_diff_elo(p):
        return abs(p.get("diff_elo", 0))

    partidos_ordenados = sorted(partidos, key=abs_diff_elo, reverse=True)

    mensajes = []
    for i in range(0, len(partidos_ordenados), TANDA_MAXIMA):
        tanda = partidos_ordenados[i : i + TANDA_MAXIMA]
        hora = tanda[0]["hora"]
        lineas = [f"\U0001f550 Favoritos claros \u2014 partidos de {hora} a {hora}"]
        for j, p in enumerate(tanda):
            if j > 0:
                lineas.append("")
            lineas.append(_formatear_partido_anuncio(p))
        mensajes.append("\n".join(lineas))
    return mensajes


def _formatear_partido_anuncio(p: dict) -> str:
    local = p["equipo_local"]
    visitante = p["equipo_visitante"]
    pred = p["prediccion"]
    diff = abs(p.get("diff_elo", 0))
    conf = p.get("confianza", 0)

    fav = _favorito(pred)
    fav_pct = pred[f"prob_{fav}"]
    emp_pct = pred["prob_empate"]
    loc_pct = pred["prob_local"]
    visit_pct = pred["prob_visitante"]

    form_l = local.get("form_score", 0)
    form_v = visitante.get("form_score", 0)
    mom_l = local.get("momentum", "?")
    mom_v = visitante.get("momentum", "?")

    u5_l = local.get("ultimos5", {}).get("texto", "?")
    u5_v = visitante.get("ultimos5", {}).get("texto", "?")
    streak_l = local.get("streak", {})
    streak_v = visitante.get("streak", {})
    racha_l = f"{streak_l.get('tipo', '?')}{streak_l.get('cantidad', 0)}"
    racha_v = f"{streak_v.get('tipo', '?')}{streak_v.get('cantidad', 0)}"

    gt_l = local.get("goal_trend", {})
    gt_v = visitante.get("goal_trend", {})
    goles_l = f"{gt_l.get('goles_favor', 0):.1f}-{gt_l.get('goles_contra', 0):.1f}"
    goles_v = f"{gt_v.get('goles_favor', 0):.1f}-{gt_v.get('goles_contra', 0):.1f}"

    return (
        f"\u26bd {p['hora']} \u00b7 {p.get('liga', '?')}\n"
        f"{local['nombre']} ({local['rating']:.0f}) vs {visitante['nombre']} ({visitante['rating']:.0f})\n"
        f"\U0001f4ca ELO \u0394{diff:.0f}\n"
        f"\U0001f3af Fav: {fav.upper()} {fav_pct}% (E {emp_pct}% / V {visit_pct}%) \u00b7 Conf {conf:.0f}\n"
        f"\U0001f4c8 Form: {form_l:.0f} vs {form_v:.0f} \u00b7 Mom: {mom_l} vs {mom_v}\n"
        f"\U0001f501 U5: {u5_l} vs {u5_v} \u00b7 Racha: {racha_l} vs {racha_v}\n"
        f"\u26bd Prom goles: {goles_l} vs {goles_v}"
    )


def _favorito(pred: dict) -> str:
    probs = {
        "local": pred["prob_local"],
        "empate": pred["prob_empate"],
        "visitante": pred["prob_visitante"],
    }
    return max(probs, key=probs.get)


def formatear_resultados(
    fixture_ids: list[str],
    resultados: dict,
    partidos_completos: dict,
) -> list[str]:
    if not fixture_ids:
        return []

    mensajes = []
    for i in range(0, len(fixture_ids), TANDA_MAXIMA):
        tanda = fixture_ids[i : i + TANDA_MAXIMA]
        lineas = []
        for j, fid in enumerate(tanda):
            r = resultados.get(fid, {})
            p = partidos_completos.get(fid)
            if j > 0:
                lineas.append("")
            lineas.append(_formatear_resultado(fid, r, p))
        header = "📋 Resultados — favoritos de la ventana"
        mensajes.append(header + "\n" + "\n".join(lineas))
    return mensajes


def _formatear_resultado(fixture_id: str, resultado: dict, partido: dict) -> str:
    if not partido:
        return f"⚽ {fixture_id} — datos no disponibles"

    local = partido["equipo_local"]["nombre"]
    visitante = partido["equipo_visitante"]["nombre"]
    pred = partido["prediccion"]
    fav = _favorito(pred)
    fav_pct = pred[f"prob_{fav}"]

    cat = resultado.get("categoria", "pendiente")
    goles = resultado.get("goles")
    ganador = resultado.get("ganador")

    if cat == "finalizado" and ganador:
        acerto = ganador == fav
        icono = "\u2705 ACERTÓ" if acerto else "\u274c FALLÓ"
        return (
            f"\u26bd {local} {goles} {visitante}\n"
            f"\U0001f3af Favorito: {fav.upper()} ({fav_pct}%) \u2192 {icono}"
        )
    else:
        desc = resultado.get("descripcion", "sin resultado aún")
        return (
            f"\u26bd {local} vs {visitante}\n"
            f"\U0001f3af Favorito: {fav.upper()} ({fav_pct}%) \u2192 \u23f3 {desc}"
        )
