# Bot Trader MT5 - Sistema Avanzado de Trading Automatizado

Un sofisticado bot de trading para MetaTrader 5 con interfaz gráfica profesional, diseñado para análisis técnico avanzado, ejecución automatizada de estrategias y gestión inteligente de riesgos en los mercados de divisas.

---

## Características Principales

### Interfaz Gráfica Profesional
- **Dashboard en Tiempo Real**: Visualización completa del estado de la cuenta (balance, equity, margen, P/L)
- **Gráficos Dinámicos**: Velas japonesas actualizadas en tiempo real con mplfinance
- **Panel de Control Intuitivo**: Selectores para símbolos (EURUSD, XAUUSD, etc.) y marcos temporales (M1 a D1)
- **Sistema de Logging Avanzado**: Registro detallado de operaciones, señales y eventos del sistema
- **Ventanas Modales No Bloqueantes**: Gestión de operaciones abiertas sin interrumpir el flujo principal

### Motor de Trading Inteligente
- **Ejecución Automatizada**: Análisis y ejecución de operaciones en cada nueva vela
- **Sistema de Señales Duales**: Combinación de indicadores técnicos y patrones de velas
- **Gestión Dinámica de Volumen**: Cálculo automático basado en porcentaje de riesgo y ATR
- **Protección Multicapa**: 
  - Límite de equity mínimo
  - **NUEVO: Límite de ganancia diaria con cierre inteligente**
  - Stop Loss y Take Profit automáticos
- **Cierre Robusto**: Sistema de cierre con múltiples modos de filling (FOK, IOC, RETURN)

### Sistema de Límite de Ganancia Diaria (NUEVO)
- **Control de Beneficios**: Establece un límite máximo de ganancia por día
- **Cierre Inteligente**: Al alcanzar el límite:
  - Cierra automáticamente operaciones con beneficio positivo (asegura ganancias)
  - Mantiene abiertas operaciones con pérdidas (oportunidad de recuperación)
- **Reseteo Automático**: Detección de nuevo día y reinicio del contador
- **Configuración Flexible**: Valor 0 = sin límite, acepta decimales

### Análisis Técnico Avanzado
- **Detección de Patrones**: Más de 15 patrones de velas japonesas (Martillo, Envolvente, Doji, etc.)
- **Indicadores Técnicos**: RSI, MACD, Medias Móviles, Bandas de Bollinger, ATR
- **Estrategias Forex**: Sistema modular de estrategias basadas en indicadores
- **Estrategias Personalizadas**: Implementación de algoritmos propietarios como "Pico y Pala"

### Módulo de Backtesting Profesional
- **Backtesting Perfecto**: Evaluación histórica con conocimiento futuro para identificar potencial máximo
- **Informes Detallados**: Análisis de rentabilidad por estrategia con métricas clave
- **Auditoría Completa**: Registro JSONL de todas las operaciones para análisis post-mortem
- **Métricas Avanzadas**: Win rate, profit factor, drawdown máximo

### Configuración y Personalización
- **Panel de Configuración Centralizado**: Modal para ajustar todos los parámetros del sistema
- **Notificaciones Email**: Resúmenes periódicos automáticos del estado de la cuenta
- **Gestión de Riesgo**: Control de capital mínimo y porcentaje de riesgo por operación
- **Persistencia de Datos**: Guardado automático de preferencias y configuraciones

### Gestión de Operaciones Avanzada
- **Ventana de Operaciones en Tiempo Real**: Visualización no bloqueante con actualización de precios
- **Cierre Individual**: Botón dedicado para cerrar operaciones específicas
- **Sistema de Colores**: Verde para ganancias, rojo para pérdidas
- **Threading Optimizado**: Actualizaciones sin bloquear la interfaz principal

---

## Últimas Actualizaciones

### Límite de Ganancia Diaria (v2.1.0)
- **Configuración Visual**: Campo dedicado en el modal de configuración
- **Validación Inteligente**: No acepta valores negativos, permite decimales
- **Lógica de Negocio**: `Ganancia_Objetivo = Balance_Inicial + Límite_Configurado`
- **Cierre Selectivo**: Preserva operaciones con potencial de recuperación
- **Reseteo Automático**: Detección de cambio de día y reinicio del sistema

### Mejoras en Gestión de Operaciones
- **Ventana de Operaciones Abiertas**: Visualización en tiempo real con actualización de precios
- **Cierre Individual**: Botón dedicado para cerrar operaciones específicas
- **Sistema de Colores**: Verde para ganancias, rojo para pérdidas
- **Threading Optimizado**: Actualizaciones sin bloquear la interfaz

---

## Instalación y Configuración

### Requisitos del Sistema
- **Python 3.13+** [Descargar](https://www.python.org/downloads/)
- **MetaTrader 5** (Terminal activo)
- **Git** [Descargar](https://git-scm.com/downloads)
- **Conexión a Internet** (para datos de mercado)

### Instalación Paso a Paso

1. **Clonar el repositorio**:
   ```bash
   git clone <repository-url>
   cd bot-trader-mt5
   ```

2. **Crear entorno virtual**:
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```

3. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar credenciales**:
   Crear archivo `.env` en la raíz:
   ```env
   MT5_ACCOUNT=12345678
   MT5_PASSWORD="tu_contraseña"
   MT5_SERVER="nombre_servidor"
   ```

---

## Guía de Uso

### Inicio Rápido
1. **Ejecutar la aplicación**:
   ```bash
   python gui_main.py
   ```

2. **Conectar a MT5**: Usar el modal de login con credenciales del `.env`

3. **Configurar parámetros**: 
   - Acceder a "Configuración" → "Configuración de la Aplicación"
   - Establecer límite de ganancia diaria (ej: 100.0 para 100€)
   - Configurar riesgo por operación y capital mínimo

4. **Seleccionar estrategias**: Elegir patrones de velas y estrategias forex

5. **Iniciar simulación**: El bot comenzará a analizar y operar automáticamente

### Configuración del Límite Diario
```
Ejemplo práctico:
- Balance inicial: 1000€
- Límite diario: 200€
- Objetivo: 1000€ + 200€ = 1200€

Al alcanzar 1200€:
✅ Operaciones con +50€ → Se cierran (ganancia asegurada)
⏳ Operaciones con -30€ → Se mantienen (oportunidad de recuperación)
```

### Monitoreo de Operaciones
- **Ver Operaciones Abiertas**: Ventana no bloqueante con actualización en tiempo real
- **Cierre Individual**: Botón para cerrar operaciones específicas
- **Logging Detallado**: Seguimiento completo de todas las acciones

---

## Arquitectura del Proyecto

```
bot-trader-mt5/
│
├── actions/                    # Sistema de acciones y tooltips
│   ├── actions.py
│   ├── tooltip.py
│   └── trade_manager.py
│
├── audit/                      # Logs de auditoría en formato JSONL
│   └── audit_log_*.jsonl
| 
├── backtesting/               # Motor de backtesting
│   ├── backtesting.py
│   ├── detect_candles.py
│   ├── apply_strategies.py
│   ├── indicators.py
│   ├── │strategy_simulator.py
│   └── report_generator.py
│
├── candles/                   # Patrones de velas japonesas
│   └── candle_list.py
│
├── custom/                    # Estrategias personalizadas
│   └── custom_strategies.py
│
├── docs/                      # Documentación técnica
│   ├── backtesting.md
│   ├── candles.md
│   ├── forex.md
│   └── log.txt
│
├── email/                     # Sistema de notificaciones
│   └── email_sender.py
│
├── forex/                     # Estrategias de divisas
│   └── forex_list.py
│
├── gui/                       # Interfaz gráfica
│   ├── body_graphic.py
│   └── body_logger.py
│
├── loggin/                    # Sistema de logging
│   ├── audit_log.py
│   └── loggin.py
│
├── main/                      # Núcleo de la aplicación
│   ├── action_handler.py
│   ├── analysis_handler.py
│   ├── body_builder.py
│   ├── header_builder.py
│   ├── login_handler.py
│   └── preferences_manager.py
│
├── metatrader/               # Conexión MT5
│   └── metatrader.py
│
├── modals/                    # Ventanas modales
│   ├── candle_config_modal.py            # Modal de configuración de velas
│   ├── config_app_modal.py               # Modal de configuración de la aplicación
│   ├── detect_all_candles_modal.py       # Modal de detección de velas
│   ├── detect_all_forex_modal.py         # Modal de detección de forex
│   ├── loggin_modal.py                   # Modal de logging
│   ├── simulation_strategies_modal.py    # Modal de simulación de estrategias
│   └── strategy_simulator_modal.py       # Modal de simulador de estrategias
│
├── operations/               # Gestión de operaciones
│   ├── close_operations.py      # ⭐ Cierre robusto
│   ├── manage_operations.py
│   ├── window_operations.py     # ⭐ Ventana de operaciones
│   └── window_close_operations.py
│
├── simulation/               # Motor de simulación
│   └── simulation.py            # ⭐ Con límite de ganancia diaria
│
├── strategies/               # Configuraciones de estrategias
│   ├── config.json             # ⭐ Incluye daily_profit_limit
│   └── *.json                  # Patrones individuales
│
├── test/                     # Herramientas de testing
│   └── close_operations.py     # Script de emergencia
|
├── .env                                  # Archivo de variables de entorno
├── .gitignore                            # Archivo de configuración de Git
├── gui_main.py                           # Punto de entrada de la aplicación con GUI
├── LICENSE                               # Licencia de la aplicación
├── main.py                               # Punto de entrada de la aplicación
├── README.md                             # Documentación de la aplicación
├── requirements.txt                      # Requisitos de la aplicación
└── user_prefs.json                       # Preferencias del usuario
```

---

## Stack Tecnológico

| Tecnología | Propósito | Versión |
|------------|-----------|---------|
| **Python** | Lenguaje principal | 3.13+ |
| **MetaTrader5** | API de trading | Latest |
| **Tkinter** | Interfaz gráfica | Built-in |
| **Pandas** | Análisis de datos | Latest |
| **Pandas-TA** | Indicadores técnicos | Latest |
| **mplfinance** | Gráficos financieros | Latest |
| **python-dotenv** | Variables de entorno | Latest |
| **threading** | Concurrencia | Built-in |

---

## Configuraciones Avanzadas

### Parámetros Principales
- **Límite de Ganancia Diaria**: Control de beneficios máximos por día
- **Capital Mínimo**: Protección de cuenta con límite inferior
- **Riesgo por Operación**: Porcentaje del equity a arriesgar
- **Notificaciones Email**: Resúmenes automáticos periódicos

### Gestión de Riesgos
- **Stop Loss Dinámico**: Basado en ATR o pips fijos
- **Take Profit Inteligente**: Ratios riesgo/beneficio configurables
- **Límites de Operaciones**: Control de número máximo por vela
- **Protección de Drawdown**: Cierre automático en pérdidas excesivas

---

## Métricas y Rendimiento

### KPIs Monitoreados
- **Win Rate**: Porcentaje de operaciones ganadoras
- **Profit Factor**: Ratio beneficios/pérdidas
- **Drawdown Máximo**: Mayor pérdida consecutiva
- **Sharpe Ratio**: Rendimiento ajustado por riesgo
- **Ganancia Diaria**: Control de objetivos de beneficio

### Reportes Disponibles
- **Backtesting Detallado**: Análisis histórico completo
- **Auditoría de Operaciones**: Log JSONL de todas las transacciones
- **Resúmenes Diarios**: Balance, operaciones y rendimiento
- **Análisis por Estrategia**: Rendimiento individual de cada patrón

---

## Soporte y Troubleshooting

### Herramientas de Diagnóstico
- **Script de Cierre de Emergencia**: `test/close_operations.py`
- **Logs Detallados**: Sistema de logging multicapa
- **Validación de Conexión**: Verificación automática de MT5

### Problemas Comunes
1. **Error de Conexión MT5**: Verificar terminal activo y credenciales
2. **Operaciones No Ejecutadas**: Revisar configuración de riesgo y capital
3. **Límite Diario No Funciona**: Verificar formato numérico en configuración

---

## Licencia

Commons Clause + Apache/MIT

---

**Desarrollado para traders que buscan automatización profesional y gestión inteligente de riesgos en los mercados financieros.**

**¡Happy Trading! 📈💰**
