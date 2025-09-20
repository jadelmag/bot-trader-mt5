
## TODO

<!-- 1. Crear estrategias customizadas de poca ganancia pero segura. -->


Añadir botón de configuración en opciones. Este botón abre una ventana modal (config_app_modal.py) con los siguientes campos:
   - Permite enviar emails a si mismo cada cierto intervalo de horas. (creia los ficheros necesarios en la carpeta email)
      - Campo correo electrónico.
      - Campo contraseña.
      - Campo texbox numerico intervalo en horas.
      - Checkbox para activar/desactivar notificaciones.
   - Límite de dinero. cuando llega a ese numero no permite abrir operaciones y mantiene las que tiene e intenta llegar lo más próximo a 0 para evitar pérdidas.
   - Checkbox para habilitar/deshabilitar audit log (JSONL). La idea es que cuando pulse Iniciar MT5 se vayan guardando las operaciones en un archivo JSONL. Estos archivos se guardan en la carpeta audit.
   - Dos botones:
      - Cancelar: Cierra el modal
      - Guardar: Guarda la configuracion en strategies con el nombre config.json

<!-- 1. Crear los funciones de:
   - Iniciar simulación
   - Abrir operación manual
   - Modificar estrategias
   - Cancelar simulación

2. Optimizar las estrategias forex y los patrones de velas para generar más ganancias y menos perdidas. -->
