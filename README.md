# Bot Trader MT5 - Sistema Avanzado de Trading Automatizado

Un sofisticado bot de trading para MetaTrader 5 con interfaz gráfica profesional, diseñado para análisis técnico avanzado, ejecución automatizada de estrategias y gestión inteligente de riesgos en los mercados de divisas.

---

## 🎯 Características Principales

### 🖥️ Interfaz Gráfica Profesional
- **Dashboard en Tiempo Real**: Visualización completa del estado de la cuenta (balance, equity, margen, P/L)
- **Actualización Automática de UI**: Los labels de información se actualizan automáticamente al cerrar operaciones manualmente
- **Gráficos Dinámicos**: Velas japonesas actualizadas en tiempo real con mplfinance
- **Panel de Control Intuitivo**: Selectores para símbolos (EURUSD, XAUUSD, etc.) y marcos temporales (M1 a D1)
- **Sistema de Logging Avanzado**: Registro detallado de operaciones, señales y eventos del sistema
- **Ventanas Modales No Bloqueantes**: Gestión de operaciones abiertas sin interrumpir el flujo principal
- **Modo Debug Dinámico**: Activar/desactivar logs de debug en tiempo real durante la simulación

### 🤖 Motor de Trading Inteligente
- **Ejecución Automatizada**: Análisis y ejecución de operaciones en cada nueva vela
- **Sistema de Señales Duales**: Combinación de indicadores técnicos y patrones de velas
- **Gestión Dinámica de Volumen**: Cálculo automático corregido usando `trade_contract_size` (soluciona error de fondos insuficientes)
- **Protección Multicapa**: 
  - Límite de equity mínimo
  - **Límite de ganancia diaria con cierre inteligente**
  - Stop Loss y Take Profit automáticos
- **Sistema de Cierre Robusto**: Múltiples modos de filling (FOK, IOC, RETURN) con hasta 15 intentos automáticos

### 💰 Sistema de Límite de Ganancia Diaria
- **Control de Beneficios**: Establece un límite máximo de ganancia por día
- **Cierre Inteligente**: Al alcanzar el límite:
  - ✅ Cierra automáticamente operaciones con beneficio positivo (asegura ganancias)
  - ⏳ Mantiene abiertas operaciones con pérdidas (oportunidad de recuperación)
- **Reseteo Automático**: Detección de nuevo día y reinicio del contador
- **Configuración Flexible**: Valor 0 = sin límite, acepta decimales
- **Integración Completa**: Implementado en [risk_manager.py] y [signal_analyzer.py]

### 📊 Análisis Técnico Avanzado
- **Detección de Patrones**: Más de 15 patrones de velas japonesas (Martillo, Envolvente, Doji, etc.)
- **Indicadores Técnicos**: RSI, MACD, Medias Móviles, Bandas de Bollinger, ATR
- **Estrategias Forex**: Sistema modular de estrategias basadas en indicadores
- **Estrategias Personalizadas**: Implementación de algoritmos propietarios como "Pico y Pala"
- **Sistema de Identificación**: Comentarios extendidos a 63 caracteres para nombres completos de estrategias

### 🔬 Módulo de Backtesting Profesional
- **Backtesting Perfecto**: Evaluación histórica con conocimiento futuro para identificar potencial máximo
- **Informes Detallados**: Análisis de rentabilidad por estrategia con métricas clave
- **Auditoría Completa**: Registro JSONL de todas las operaciones para análisis post-mortem
- **Métricas Avanzadas**: Win rate, profit factor, drawdown máximo

### ⚙️ Configuración y Personalización
- **Panel de Configuración Centralizado**: Modal para ajustar todos los parámetros del sistema
- **Notificaciones Email**: Resúmenes periódicos automáticos del estado de la cuenta
- **Gestión de Riesgo**: Control de capital mínimo y porcentaje de riesgo por operación
- **Persistencia de Datos**: Guardado automático de preferencias y configuraciones

### 📈 Gestión de Operaciones Avanzada
- **Ventana de Operaciones en Tiempo Real**: 
  - Visualización no bloqueante con actualización automática de precios cada segundo
  - Muestra: Ticket, Volumen, P/L, Tipo (Long/Short), Precio apertura, Precio actual, Estrategia completa
  - Sistema de colores dinámico (verde para ganancias, rojo para pérdidas)
  - Scrollbar para manejar múltiples operaciones
- **Cierre Individual Robusto**: Botón dedicado para cerrar operaciones específicas con sistema de reintentos
- **Threading Optimizado**: Actualizaciones sin bloquear la interfaz principal
- **Manejo de Errores Robusto**: Prevención completa de errores "bad window path name"
- **Actualización Automática de UI**: Balance, equity y métricas se actualizan inmediatamente tras cerrar operaciones

### 🔒 Sistema de Cierre Robusto de Operaciones
- **Múltiples Modos de Filling**: Intenta FOK, IOC y RETURN automáticamente
- **Reintentos Inteligentes**: Hasta 5 intentos por modo (15 intentos totales)
- **Verificación de Cierre**: Confirma que la operación se cerró completamente
- **Diagnóstico Detallado**: Información completa de MT5 y símbolo para troubleshooting
- **Threading No Bloqueante**: Cierre de operaciones en hilo separado al salir de la aplicación
- **Manejo de Spread**: Ajuste dinámico de desviación según spread del mercado

---

## 🆕 Últimas Actualizaciones

### v2.3.0 - Mejoras Críticas en Estabilidad y UX
**Fecha**: Enero 2025

#### 🐛 Correcciones Críticas
- **Cálculo de Volumen Corregido**: 
  - Solucionado error crítico que causaba "Fondos insuficientes"
  - Cambio de `trade_tick_value` a `trade_contract_size` en `_calculate_volume()`
  - Previene volúmenes gigantescos (antes: 1,846,150 lotes → ahora: volúmenes correctos)
  
- **Cierre de Operaciones Robusto**:
  - Implementado sistema con 3 filling modes y 15 intentos totales
  - Soluciona error "Unsupported filling mode (código: 10030)"
  - Archivos modificados: [close_operations.py], `manage_operations.py`, [trade_manager.py]

- **Ventanas de Operaciones Estabilizadas**:
  - Eliminado completamente error "bad window path name"
  - Verificaciones `winfo_exists()` antes de cada actualización
  - Manejo robusto de `tk.TclError` en ambas ventanas
  - Limpieza automática de eventos al cerrar ventanas

#### ✨ Nuevas Funcionalidades
- **Límite de Ganancia Diaria**:
  - Campo dedicado en modal de configuración
  - Validación: no acepta valores negativos, permite decimales
  - Cierre selectivo: preserva operaciones con pérdidas
  - Reseteo automático al cambiar de día
  - Archivos: [config_app_modal.py], [risk_manager.py], [signal_analyzer.py]

- **Actualización Automática de UI**:
  - Labels de cuenta se actualizan al cerrar operaciones manualmente
  - Método `_update_ui_account_info()` en [action_handler.py]
  - Integrado en [window_operations.py] y `window_close_operations.py`

- **Modo Debug Dinámico**:
  - Activar/desactivar logs de debug durante la simulación
  - Opción en menú "Simulación" → "Modo Debug"
  - No requiere reiniciar la aplicación

- **Nombres Completos de Estrategias**:
  - Comentarios extendidos de 20 a 63 caracteres
  - Parsing mejorado en [window_operations.py]
  - Muestra nombres completos como "strategy_scalping_stochrsi_ema"

#### 🔧 Mejoras Técnicas
- **Threading No Bloqueante**: 
  - Cierre de operaciones en hilo separado al salir
  - Feedback visual durante el proceso
  - Prevención de cierre si quedan operaciones abiertas

- **Diagnóstico Mejorado**:
  - Información detallada de MT5 y símbolo en errores
  - Logs estructurados con niveles (info, success, error, warn)
  - Sistema de auditoría JSONL completo

---

## 📥 Instalación y Configuración

### Requisitos del Sistema
- **Python 3.13+** [Descargar](https://www.python.org/downloads/)
- **MetaTrader 5** (Terminal activo)
- **Git** [Descargar](https://git-scm.com/downloads)
- **Conexión a Internet** (para datos de mercado)

### Instalación Paso a Paso

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
├── actions/                              # Sistema de acciones y tooltips
│   ├── actions.py
│   ├── tooltip.py
│   └── trade_manager.py
│
├── analysis/ 
│   └── analysis_[day-month-year].md
|
├── audit/                                # Logs de auditoría en formato JSONL
│   └── audit_log_*.jsonl
| 
├── backtesting/                          # Motor de backtesting
│   ├── __init__.py
│   ├── apply_strategies.py
│   ├── backtesting.py
│   ├── detect_candles.py
│   ├── indicators.py
│   ├── report_generator.py
│   └── strategy_simulator.py
│
├── candles/                              # Patrones de velas japonesas
│   └── candle_list.py
│
├── custom/                               # Estrategias personalizadas
│   └── custom_strategies.py
│
├── docs/                                 # Documentación técnica
│   ├── backtesting.md
│   ├── candles.md
│   ├── forex.md
│   └── log.txt
│
├── email/                                # Sistema de notificaciones
│   └── email_sender.py
│
├── forex/                                # Estrategias de divisas
│   └── forex_list.py
│
├── gui/                                  # Interfaz gráfica
│   ├── __init__.py
│   ├── body_atr.py
│   ├── body_graphic.py
│   ├── body_logger.py
│   ├── body_macd.py
│   ├── body_momentum.py
│   └── body_rsi.py
│
├── loggin/                              # Sistema de logging
│   ├── __init__.py
│   ├── audit_log.py
│   └── loggin.py
│
├── main/                                # Núcleo de la aplicación
│   ├── __init__.py
│   ├── action_handler.py
│   ├── analysis_handler.py
│   ├── body_builder.py
│   ├── header_builder.py
│   ├── login_handler.py
│   └── preferences_manager.py
│
├── metatrader/                           # Conexión MT5
│   └── metatrader.py
│
├── modals/                               # Ventanas modales
│   ├── __init__.py
│   ├── candle_config_modal.py            # Modal de configuración de velas
│   ├── config_app_modal.py               # Modal de configuración de la aplicación
│   ├── detect_all_candles_modal.py       # Modal de detección de velas
│   ├── detect_all_forex_modal.py         # Modal de detección de forex
│   ├── loggin_modal.py                   # Modal de logging
│   ├── simulation_strategies_modal.py    # Modal de simulación de estrategias
│   └── strategy_simulator_modal.py       # Modal de simulador de estrategias
│
├── operations/                           # Gestión de operaciones
│   ├── close_operations.py      
│   ├── manage_operations.py
│   ├── window_operations.py     
│   └── window_close_operations.py
│
├── resumes/  
│   └── resume_[day-month-year_hh:mm:ss].txt
│
├── simulation/                           # Motor de simulación
│   ├── __init__.py            
│   ├── config_loader.py            
│   ├── indicators.py            
│   ├── key_list.py            
│   ├── position_monitor.py            
│   ├── risk_manager.py            
│   ├── signal_analyzer.py            
│   └── trade_manager.py                       
│
├── simulation_logs/ 
│   └── simulacion_day_month_year_hour_minute_seconds.log
│
├── strategies/                           
│   ├── config.json                       # Configuración de la aplicacion para el backtesting
│   ├── strategies.json                   # Configuración de la aplicacion para la simulación con metatrader
│   └── *.json                            # Patrones individuales
│
├── test/                                 # Herramientas de testing
│   └── close_operations.py
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

## 💻 Stack Tecnológico

| Tecnología | Propósito | Versión |
|------------|-----------|---------|
| **Python** | Lenguaje principal | 3.13+ |
| **MetaTrader5** | API de trading | 5.0.5260 |
| **Tkinter** | Interfaz gráfica | Built-in |
| **Pandas** | Análisis de datos | 2.3.2+ |
| **NumPy** | Computación numérica | 2.2.6+ |
| **Pandas-TA** | Indicadores técnicos | 0.4.71b0 |
| **mplfinance** | Gráficos financieros | 0.12.10b0 |
| **Matplotlib** | Visualización | 3.9.2+ |
| **python-dotenv** | Variables de entorno | 1.0.0+ |
| **threading** | Concurrencia | Built-in |

### Dependencias Adicionales
- **stable-baselines3**: Reinforcement Learning (2.7.0+)
- **gymnasium**: Entornos RL (0.30.0+)
- **torch**: Deep Learning (2.0.0+)
- **scikit-learn**: Machine Learning (1.5.0+)
- **telethon**: Notificaciones Telegram (1.28.5)
- **pyarrow**: Serialización eficiente (14.0.0+)
- **websocket-client**: Conexiones WebSocket (1.7.0+)
- **requests**: Llamadas HTTP (2.31.0+)

---

## ⚙️ Configuraciones Avanzadas

### Parámetros Principales

#### Límite de Ganancia Diaria
- **Descripción**: Control de beneficios máximos por día
- **Configuración**: `config.json` → `daily_profit_limit`
- **Valor por defecto**: `0.0` (sin límite)
- **Ejemplo**: `100.0` = detener al ganar 100€ en el día
- **Comportamiento**: 
  - Cierra operaciones rentables automáticamente
  - Mantiene operaciones con pérdidas abiertas
  - Se resetea automáticamente a las 00:00

#### Capital Mínimo
- **Descripción**: Protección de cuenta con límite inferior
- **Configuración**: `config.json` → `money_limit`
- **Comportamiento**: Detiene nuevas operaciones si el balance cae por debajo del límite

#### Riesgo por Operación
- **Descripción**: Porcentaje del equity a arriesgar por trade
- **Configuración**: `config.json` → `risk_per_trade_percent`
- **Valor por defecto**: `1.0` (1% del equity)
- **Formato**: String con 8 decimales para evitar notación científica
- **Ejemplo**: `"0.50000000"` = 0.5% de riesgo

#### Notificaciones Email
- **Activación**: `config.json` → `email_notifications`
- **Parámetros**:
  - `email_address`: Correo del remitente
  - `email_password`: Contraseña de aplicación
  - `email_interval_hours`: Frecuencia de resúmenes (ej: 24 horas)

#### Audit Log
- **Activación**: `config.json` → `audit_log_enabled`
- **Formato**: JSONL (JSON Lines)
- **Ubicación**: `audit/audit_log_*.jsonl`
- **Contenido**: Registro completo de todas las operaciones con timestamps

### Gestión de Riesgos

#### Stop Loss Dinámico
- **Basado en ATR**: Usa volatilidad del mercado
- **Configuración por patrón**: `use_atr_for_sl_tp: true`
- **Multiplicador ATR**: Configurable en cada estrategia
- **Pips fijos**: Alternativa cuando ATR está desactivado

#### Take Profit Inteligente
- **Ratios configurables**: Risk/Reward por estrategia
- **Ejemplo**: SL de 20 pips → TP de 40 pips (ratio 1:2)
- **Desactivable**: `use_take_profit: false` en configuración

#### Límites de Operaciones
- **Por vela**: Control de número máximo de trades por vela
- **Variable**: `trades_in_current_candle` en [simulation.py](cci:7://file:///c:/Users/Xu/Documents/repositories/bot-trader-mt5/simulation/simulation.py:0:0-0:0)
- **Reseteo**: Automático al cambiar de vela

#### Protección de Drawdown
- **Límite de equity**: Detiene operaciones si equity < capital mínimo
- **Cierre automático**: Al alcanzar límite de ganancia diaria
- **Monitoreo continuo**: Verificación en cada análisis de mercado

---

## 📊 Métricas y Rendimiento

### KPIs Monitoreados

#### Win Rate
- **Descripción**: Porcentaje de operaciones ganadoras
- **Cálculo**: `(Trades ganadores / Total trades) × 100`
- **Ubicación**: Logs de simulación y reportes de backtesting

#### Profit Factor
- **Descripción**: Ratio beneficios/pérdidas
- **Cálculo**: `Total ganancias / Total pérdidas`
- **Interpretación**: 
  - > 1.0 = Sistema rentable
  - > 2.0 = Sistema muy rentable
  - < 1.0 = Sistema no rentable

#### Drawdown Máximo
- **Descripción**: Mayor pérdida consecutiva desde un pico
- **Monitoreo**: Continuo durante simulación
- **Registro**: En audit logs y reportes

#### Sharpe Ratio
- **Descripción**: Rendimiento ajustado por riesgo
- **Uso**: Evaluación de estrategias en backtesting
- **Interpretación**: Mayor valor = mejor relación riesgo/retorno

#### Ganancia Diaria
- **Descripción**: Control de objetivos de beneficio
- **Tracking**: `daily_start_balance` en [risk_manager.py](cci:7://file:///c:/Users/Xu/Documents/repositories/bot-trader-mt5/simulation/risk_manager.py:0:0-0:0)
- **Reseteo**: Automático al detectar nuevo día

### Reportes Disponibles

#### Backtesting Detallado
- **Ubicación**: `analysis/analysis_[fecha].md`
- **Contenido**:
  - Rendimiento por estrategia
  - Métricas de rentabilidad
  - Análisis de patrones más efectivos
  - Recomendaciones de optimización

#### Auditoría de Operaciones
- **Formato**: JSONL (una operación por línea)
- **Ubicación**: `audit/audit_log_*.jsonl`
- **Campos**:
  - Timestamp
  - Tipo de evento (open/close/system)
  - Símbolo, volumen, precio
  - P/L, comentario, estrategia

#### Resúmenes Diarios
- **Ubicación**: `resumes/resume_[fecha_hora].txt`
- **Contenido**:
  - Balance inicial y final
  - Total de operaciones
  - Ganancias y pérdidas
  - Rendimiento por estrategia

#### Análisis por Estrategia
- **Generación**: Automática en backtesting
- **Métricas individuales**:
  - Win rate por estrategia
  - Profit factor
  - Número de señales generadas
  - Rentabilidad promedio

---

## 🔧 Modo Debug

### Activación
- **Durante ejecución**: Menú "Simulación" → "Modo Debug"
- **Al inicio**: Checkbox en menú "Opciones"
- **Dinámico**: No requiere reiniciar la aplicación

### Información Adicional en Debug
- Requests de órdenes completos
- Cálculos de volumen detallados
- Evaluación de indicadores técnicos
- Decisiones de estrategias paso a paso
- Verificaciones de riesgo

### Archivos de Log
- **Ubicación**: `simulation_logs/simulacion_[fecha_hora].log`
- **Niveles**: INFO, SUCCESS, ERROR, WARN, DEBUG
- **Formato**: Timestamp + Nivel + Mensaje

---

## 🛠️ Herramientas de Diagnóstico

### Script de Cierre de Emergencia
- **Ubicación**: `test/close_operations.py`
- **Uso**: Cerrar todas las operaciones manualmente
- **Ejecución**: 
  ```bash
  python test/close_operations.py
  ```

### Logs Detallados
- **Sistema multicapa**:
  - GUI logger (interfaz)
  - Simulation logger (archivo)
  - Audit logger (JSONL)
- **Rotación**: Automática por fecha

### Validación de Conexión
- **Automática**: Al iniciar simulación
- **Verificaciones**:
  - Terminal MT5 activo
  - Conexión al servidor
  - Símbolo disponible
  - Permisos de trading

---

## 🐛 Troubleshooting

### Problemas Comunes

#### 1. Error de Conexión MT5
**Síntomas**: "MT5 no está conectado" o "Terminal no responde"

**Soluciones**:
- Verificar que MT5 esté abierto y activo
- Comprobar credenciales en [.env](cci:7://file:///c:/Users/Xu/Documents/repositories/bot-trader-mt5/.env:0:0-0:0)
- Verificar conexión a internet
- Reiniciar terminal MT5
- Verificar que el servidor esté operativo

#### 2. Fondos Insuficientes
**Síntomas**: "Insufficient funds" o volúmenes incorrectos

**Solución**: ✅ **CORREGIDO en v2.3.0**
- Ahora usa `trade_contract_size` en lugar de `trade_tick_value`
- Cálculo de volumen correcto para Forex (100,000 unidades)
- Si persiste, reducir `risk_per_trade_percent`

#### 3. Unsupported Filling Mode
**Síntomas**: Error código 10030

**Solución**: ✅ **CORREGIDO en v2.3.0**
- Sistema robusto con 3 filling modes (FOK, IOC, RETURN)
- 15 intentos automáticos (5 por modo)
- Ajuste dinámico de desviación según spread

#### 4. Operaciones No Ejecutadas
**Causas posibles**:
- Capital por debajo del mínimo configurado
- Límite de ganancia diaria alcanzado
- Riesgo por operación muy bajo
- No hay señales válidas de estrategias

**Verificar**:
- `config.json` → `money_limit`
- `config.json` → `daily_profit_limit`
- `config.json` → `risk_per_trade_percent`
- Logs de debug para ver evaluación de señales

#### 5. Límite Diario No Funciona
**Verificar**:
- Formato numérico correcto en `config.json`
- Valor mayor que 0 (0 = sin límite)
- Balance inicial del día registrado correctamente
- Logs: buscar "[RISK-LIMIT]" para ver activación

#### 6. Bad Window Path Name
**Síntomas**: Error al cerrar ventanas de operaciones

**Solución**: ✅ **CORREGIDO en v2.3.0**
- Verificaciones `winfo_exists()` implementadas
- Manejo robusto de `tk.TclError`
- Limpieza automática de eventos
- Si persiste, actualizar a última versión

#### 7. Estrategias No Aparecen Completas
**Síntomas**: Nombres truncados en ventana de operaciones

**Solución**: ✅ **CORREGIDO en v2.3.0**
- Comentarios extendidos a 63 caracteres
- Parsing mejorado en [window_operations.py](cci:7://file:///c:/Users/Xu/Documents/repositories/bot-trader-mt5/operations/window_operations.py:0:0-0:0)
- Muestra nombres completos de estrategias

#### 8. UI No Se Actualiza
**Síntomas**: Labels de balance/equity no cambian al cerrar operaciones

**Solución**: ✅ **CORREGIDO en v2.3.0**
- Actualización automática implementada
- Método `_update_ui_account_info()` en [action_handler.py](cci:7://file:///c:/Users/Xu/Documents/repositories/bot-trader-mt5/main/action_handler.py:0:0-0:0)
- Ejecuta en hilo principal con `after(0, ...)`

---

## 📚 Documentación Adicional

### Archivos de Documentación
- **`docs/backtesting.md`**: Guía completa de backtesting
- **`docs/candles.md`**: Patrones de velas soportados
- **`docs/forex.md`**: Estrategias Forex disponibles
- **`docs/log.txt`**: Registro de cambios y desarrollo

### Recursos Externos
- [Documentación MT5 Python](https://www.mql5.com/en/docs/python_metatrader5)
- [Pandas-TA Indicators](https://github.com/twopirllc/pandas-ta)
- [mplfinance Charts](https://github.com/matplotlib/mplfinance)

---

## 🤝 Contribuciones

Este proyecto está en desarrollo activo. Las mejoras implementadas incluyen:

### Últimas Contribuciones
- ✅ Sistema de límite de ganancia diaria
- ✅ Cierre robusto con múltiples filling modes
- ✅ Corrección crítica de cálculo de volumen
- ✅ Ventanas de operaciones estabilizadas
- ✅ Actualización automática de UI
- ✅ Modo debug dinámico
- ✅ Nombres completos de estrategias
- ✅ Threading no bloqueante

---

## 📄 Licencia

**Commons Clause + Apache/MIT**

Este software está disponible bajo una licencia que permite uso personal y educativo, pero restringe el uso comercial sin autorización explícita.

---

## ⚠️ Disclaimer

**ADVERTENCIA**: Este software es una herramienta educativa y de investigación. El trading en mercados financieros conlleva riesgos significativos de pérdida de capital.

- ❌ No garantizamos rentabilidad
- ❌ No somos asesores financieros
- ✅ Úsalo bajo tu propia responsabilidad
- ✅ Prueba en cuenta demo primero
- ✅ Nunca arriesgues más de lo que puedes perder

---

## 📞 Soporte

Para reportar bugs o solicitar funcionalidades:
1. Revisar la sección de **Troubleshooting**
2. Verificar logs en [simulation_logs/]
3. Consultar audit logs en [audit/]
4. Activar modo debug para diagnóstico detallado

---

## 🎯 Roadmap

### Próximas Funcionalidades
- [ ] Machine Learning para optimización de estrategias
- [ ] Backtesting con datos tick-by-tick
- [ ] Dashboard web en tiempo real
- [ ] Notificaciones push móviles
- [ ] Multi-símbolo simultáneo
- [ ] Gestión de múltiples cuentas
- [ ] API REST para control remoto

---

**Desarrollado para traders que buscan automatización profesional y gestión inteligente de riesgos en los mercados financieros.**

**¡Happy Trading! 📈💰**

