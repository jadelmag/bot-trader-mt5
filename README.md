# Bot Trader MT5

Un sofisticado bot de trading para MetaTrader 5, con una interfaz gráfica de usuario (GUI) construida con Tkinter. El bot está diseñado para analizar los mercados de divisas, detectar señales de trading basadas en una completa biblioteca de estrategias técnicas y gestionar las conexiones de forma segura.

---

## 🚀 Características Principales

### Interfaz Gráfica Intuitiva (GUI)
-   **Visualización Profesional**: Gráficos de velas en tiempo real con `mplfinance`, que se actualizan dinámicamente.
-   **Panel de Control Centralizado**: Selectores para cambiar fácilmente entre símbolos (`EURUSD`, `XAUUSD`, etc.) y marcos de tiempo (`M1` a `D1`).
-   **Menús de Acceso Rápido**: Accede a todas las herramientas de análisis, backtesting, simulación y configuración desde menús desplegables.
-   **Logger Integrado**: Un panel de registro detallado que muestra el estado de la conexión, señales de trading, operaciones ejecutadas, errores y resúmenes de análisis.
-   **Dashboard de Cuenta**: Visualiza en tiempo real el balance, equity, margen, beneficios y pérdidas de tu cuenta de trading.

### Motor de Trading y Simulación en Tiempo Real
-   **Ejecución de Estrategias en Vivo**: El bot analiza el mercado en cada nueva vela y puede ejecutar operaciones automáticamente.
-   **Lógica de Doble Señal**: Combina señales de indicadores de tendencia (como cruces de medias móviles) con señales de patrones de velas para confirmar entradas al mercado.
-   **Gestión de Riesgo Dinámica**: Calcula automáticamente el volumen de la operación (`lotaje`) basándose en un porcentaje de riesgo sobre el equity y un stop-loss en pips definidos.
-   **Manejo de Operaciones**: Abre y cierra operaciones directamente en MetaTrader 5, incluyendo la configuración de Stop Loss y Take Profit.
-   **Protección de Capital**: Incluye un límite de equity configurable para detener la apertura de nuevas operaciones si el capital cae por debajo de un umbral.

### Potente Módulo de Backtesting
-   **Backtesting "Perfecto"**: Evalúa la rentabilidad histórica de todas las estrategias y patrones de velas, asumiendo conocimiento futuro para identificar el potencial máximo de cada señal.
-   **Informes Detallados**: Genera resúmenes claros que muestran el número de operaciones rentables y el beneficio total para cada estrategia, ayudándote a decidir cuáles son las más efectivas.
-   **Auditoría de Trades**: Registra cada operación de backtesting en un fichero de auditoría (`JSONL`), permitiendo un análisis post-mortem exhaustivo.

### Análisis Técnico Avanzado
-   **Detección de Patrones de Velas**: Identifica más de 10 patrones de velas (Martillo, Envolvente, Doji, etc.) y analiza su rendimiento histórico.
-   **Análisis de Estrategias Forex**: Evalúa el rendimiento de múltiples estrategias de trading basadas en indicadores como Medias Móviles, RSI, MACD y Bandas de Bollinger.
-   **Configuración de Estrategias**: Permite seleccionar y configurar qué estrategias de velas y forex se utilizarán en la simulación en tiempo real.

### Configuración y Personalización
-   **Gestión Centralizada**: Un modal de configuración permite ajustar parámetros clave de la aplicación.
-   **Notificaciones por Email**: Configura el envío de resúmenes periódicos del estado de la cuenta a tu correo electrónico, con control sobre el intervalo de envío.
-   **Parámetros de Riesgo**: Define el capital mínimo para operar y el porcentaje de riesgo por operación.
-   **Persistencia de Preferencias**: La aplicación guarda tus últimas selecciones de símbolo y timeframe para mayor comodidad.

### Gestión Segura y Conexión
-   **Conexión Segura a MT5**: Utiliza un modal de inicio de sesión para conectar de forma segura a tu cuenta de MetaTrader 5.
-   **Manejo de Credenciales**: Carga las credenciales desde un archivo `.env` para mantenerlas separadas del código fuente.

---

## Requisitos

* Python 3.13 [Download: https://www.python.org/downloads/]
* Conexión a internet (para descargar datos de Yahoo Finance y FinRL)
* Git (para clonar el repositorio) [Download: https://git-scm.com/downloads]
* MetaTrader 5

---

## 🛠️ Instalación y Configuración

Sigue estos pasos para poner en marcha el proyecto.

1.  **Clona el repositorio**:
    ```bash
    git clone <your-repository-url>
    cd bot-trader-mt5
    ```

2.  **Crea un entorno virtual** (recomendado):
    ```bash
    python -m venv venv
    # En Windows:
    venv\Scripts\activate
    # En macOS/Linux:
    # source venv/bin/activate
    ```

3.  **Instala las dependencias**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configura tus credenciales**:
    -   Crea un archivo llamado `.env` en el directorio raíz del proyecto.
    -   Añade los detalles de tu cuenta de MetaTrader 5 a este archivo con el siguiente formato:
        ```env
        MT5_ACCOUNT=12345678
        MT5_PASSWORD="tu_contraseña"
        MT5_SERVER="nombre_de_tu_servidor"
        ```

---

## Esquema de Directorios y Archivos (Resumen)

```
app/
|
├── actions/                              # Módulos para acciones
│   ├── actions.py                        # Acciones
│   ├── tooltip.py                        # Tooltips
│   └── trade_manager.py                  # Gestión de operaciones
|
├── audit/                                # Directorio para logs de operaciones en JSONL
|
├── backtesting/                         
│   ├── __init__.py                       # Inicialización de módulos
│   ├── apply_strategies.py               # Aplicación de estrategias
│   ├── backtesting.py                    # Backtesting
│   ├── detect_candles.py                 # Detección de velas
│   ├── report_generator.py               # Generador de informes
│   └── strategy_simulator.py             # Simulador de estrategias
|
├── candles/                              
|   └── candle_list.py                    # Patrones de velas
|
├── custom/
|   └── custom_strategies.py              # Estrategias personalizadas
|
├── docs/                                 # Documentación
|   ├── candles.md                        # Documentación de patrones de velas
|   ├── forex.md                          # Documentación de estrategias de forex
|   ├── log.txt                           # Log de la aplicación
|   └── todo.md                           # Tareas pendientes
|
├── email/                                # Módulo para envío de notificaciones por email
|   └── email_sender.py                   # Envío de notificaciones por email
|
├── forex/
│   └── forex_list.py                     # Lista de estrategias de forex
|
├── gui/
│   ├── __init__.py                       # Inicialización de módulos
│   ├── body_graphic.py                   # Gráfico principal de la aplicación
│   └── body_logger.py                    # Logger de la aplicación
|
├── loggin/                               # Módulos para logging
│   ├── __init__.py                       # Inicialización de módulos
│   ├── audit_log.py                      # Logger de auditoría
│   └── loggin.py                         # Logger de la aplicación
|
├── modals/                               # Módulos para modales de la aplicación
│   ├── __init__.py                       # Inicialización de módulos
│   ├── backtesting_modal.py              # Modal de backtesting
│   ├── candle_config_modal.py            # Modal de configuración de velas
│   ├── config_app_modal.py               # Modal de configuración de la aplicación
│   ├── detect_all_candles_modal.py       # Modal de detección de velas
│   ├── detect_all_forex_modal.py         # Modal de detección de forex
│   ├── loggin_modal.py                   # Modal de logging
│   └── strategy_simulator_modal.py       # Modal de simulador de estrategias
|
├── resumes/                            # Directorio para informes de backtesting
│   └── backtesting_2025-09-20_12-51-52.txt
|
├── simultation/   
│   └── simulation.py                     # Simulación de trading
|
├── simultation_logs/   
│   └── simulation_2025-09-20_12-51-52.txt # Log de la simulación
|
├── strategies/                         # Patrones de velas y estrategias de trading
|   ├── config.json                       # Fichero de configuración de la app
|   └── ... (Múltiples ficheros .json con estrategias)
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

## ▶️ Cómo Usar la Aplicación

1. Crea un archivo `.env` en el directorio raíz del proyecto.
2. Añade los detalles de tu cuenta de MetaTrader 5 a este archivo con el siguiente formato:
    ```env
    MT5_ACCOUNT=12345678
    MT5_PASSWORD="tu_contraseña"
    MT5_SERVER="nombre_de_tu_servidor"
    ```
3. Asegúrate de que tu terminal de MetaTrader 5 esté en funcionamiento.
4. Ejecuta la aplicación desde tu terminal:
    ```bash
    python main.py
    ```
5. Usa el botón **"Conectar"** en la GUI. El modal de inicio de sesión aparecerá pre-rellenado con tus credenciales del archivo `.env`. Haz clic en "Conectar".
6. Una vez conectado, selecciona un símbolo y un marco de tiempo, y haz clic en **"Iniciar MT5"** para cargar el gráfico.
7. Usa el menú **"Herramientas"** para analizar el gráfico en busca de patrones de velas o señales de estrategia.

---

## 💻 Tecnologías Clave

-   **Python 3**
-   **MetaTrader5**: Para la conexión al terminal de MT5 y la obtención de datos de mercado.
-   **Tkinter**: Para la interfaz gráfica de usuario.
-   **Pandas**: Para la manipulación y el análisis de datos.
-   **Pandas-TA**: Para el cálculo de indicadores técnicos.
-   **python-dotenv**: Para la gestión de variables de entorno y credenciales.
-   **SciPy**: Para operaciones numéricas (utilizado en la detección de patrones).


## Licencia

Commons Clause + Apache/MIT