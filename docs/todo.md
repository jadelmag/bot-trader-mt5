
## TODO


1. Crear estrategias customizadas de poca ganancia pero segura. [TODO]
2. Optimizar las estrategias forex para generar más ganancias y menos perdidas. [DOING]


como es posible que si sigo este flujo:

Herramientas > Detectar Estrategias forex (modal DetectAllForexModal) > Selecciono todas y me dice:

=============== RESUMEN DE ANÁLISIS DE ESTRATEGIAS ===============
[14:10:20] ESTRATEGIA                          | APLICACIONES |      BENEFICIOS |        PÉRDIDAS
[14:10:20] --------------------------------------------------------------------------------------
[14:10:20] Bollinger Bands Breakout            |            0 |          0.00 $ |          0.00 $
[14:10:20] Bollinger Bands Reversion           |            0 |          0.00 $ |          0.00 $
[14:10:20] Candle Pattern Reversal             |            3 |          0.00 $ |         44.00 $
[14:10:20] Chart Pattern Breakout              |            0 |          0.00 $ |          0.00 $
[14:10:20] Fibonacci Reversal                  |            3 |          0.00 $ |         44.00 $
[14:10:20] Ichimoku Kinko Hyo                  |            0 |          0.00 $ |          0.00 $
[14:10:20] Ma Crossover                        |            3 |         47.00 $ |          0.00 $
[14:10:20] Momentum Rsi Macd                   |            3 |         62.00 $ |          0.00 $
[14:10:20] Price Action Sr                     |            3 |          0.00 $ |         44.00 $
[14:10:20] Scalping Stochrsi Ema               |            0 |          0.00 $ |          0.00 $
[14:10:20] Swing Trading Multi Indicator       |           48 |        426.00 $ |        577.00 $
[14:10:20] --------------------------------------------------------------------------------------
[14:10:20] BENEFICIO TOTAL (TODAS LAS ESTRATEGIAS): 535.00 $
[14:10:20] PÉRDIDA TOTAL (TODAS LAS ESTRATEGIAS): 709.00 $
[14:10:20] ===========================================================================

Sin embargo, sigo este otro flujo:

Herramientas > Aplicar Estrategias (abre el modal StrategySimulatorModal) > Selecciono Bollinger Bands Breakout con la siguiente configuración:
    - % Ratio: 1
    - RR Ratio: 2
    - Stop Loss (pips): 20

Y me devuelve esto:

--- Iniciando Simulación de Estrategia ---
[14:12:25] Preparando datos y calculando indicadores técnicos manualmente...
[14:12:25] Indicadores calculados. Velas disponibles para simulación: 223
[14:12:25] Señal de FOREX 'strategy_bollinger_bands_breakout' (long) en la vela 29 al precio 1.17537
[14:12:25]     -> Trade ABIERTO: long a 1.17537 | Lote: 0.05 | Riesgo: $10.00
[14:12:25] --- Simulación Finalizada ---
[14:12:25] 
========================= Resumen de la Simulación =========================
[14:12:25] No se realizaron operaciones.
[14:12:25] Configuración de simulación guardada y simulación ejecutada.

Como es posible que:
- ¿abra una operacion y no la cierre?
- finalice la simulacion sin un resumen?