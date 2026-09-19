# Alertas Favoritos elo-tilt → Telegram

Sistema de alertas automáticas de favoritos claros en partidos de fútbol, usando el modelo de predicción Glicko-2 del repo [elo-tilt](https://github.com/erikolivo/elo-tilt) y resultados de ESPN.

## Qué hace

1. **Cada hora, 15 min antes de arrancar**, anuncia por Telegram los partidos con **favorito claro** (margen ≥ 45%, ambos equipos con ≥ 3 partidos jugados).
2. **~2.5 horas después**, manda el resultado de esos mismos partidos.
3. **Guarda historial mensual** con más partidos de los que alerta (margen ≥ 40%), para medir aciertos después.
4. **Registra sorpresas** (margen 20-30%, el favorito perdió) en archivo aparte.

## Arquitectura

```
elo-tilt (predicciones_cache.json) ─┐
                                     ├──> vigilar.py (1 ciclo) ──> Telegram
ESPN (boxscore/scoreboard)      ────┘         │
                                               ▼
                              data/estado_ventanas.json (operativo)
                              data/historial/YYYY-MM.json (archivo)
                              data/sorpresas/YYYY-MM.json (archivo)
```

## Setup

1. Crear un repo en GitHub con este código.
2. Configurar secrets:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
3. Los workflows se ejecutan automáticamente según el cronograma (ver `.github/workflows/`).

## Estructura

```
├── .github/workflows/
│   ├── vigilancia.yml       # workflow principal
│   └── watchdog.yml         # heartbeat cada 30 min
├── data/
│   ├── estado_ventanas.json
│   ├── historial/YYYY-MM.json
│   └── sorpresas/YYYY-MM.json
├── obtener_favoritos.py     # lee predicciones de elo-tilt
├── obtener_resultado.py     # consulta ESPN
├── ventanas.py              # lógica de ventanas horarias
├── telegram_utils.py        # envío de mensajes
├── vigilar.py               # orquestador principal
└── requirements.txt
```

## Requisitos

- Python 3.11+
- Secrets de Telegram configurados en GitHub
