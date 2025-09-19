quiero que en detect_candle_modal.py añadas todas las estrategias forex que hay en forex_list.py.

quiero que el modal tenga un titulo que diga 'Simulador de Estrategias'.

el modal tendra diseño tabular de dos pestañas: Forex y Candle.

En la seccion forex tendra:
    1. dos botones: seleccionar todos y deseleccionar todos
    2. todas las estrategias de forex en lista.
        - Cada fila tendra un checkbox para seleccionarlo, el nombre de la estrategia un texbox para el % Ratio que por defecto sera 1 y un textbox RR Ratio que por defecto sera 2. Y no se si hace falta algun otro textbox para otro parametro como el stop loss. (igual depende de la estrategia)

En la seccion candle tendra:
    1. dos botones: seleccionar todos, deseleccionar todos y cargar todas las estrategias
    2. todas las estrategias de candle en lista.
        - Cada fila tendra un checkbox para seleccionarlo, el nombre de la candle el dropdown con dos estados: Default y Custom, boton configurar y boton cargar.

Y abajo del todo, independientemente del tab estaran los botones: 
    1. Cancelar - El cual cerrara el modal
    2. Aplicar - El cual aplicara todas las estrategias seleccionadas con sus respectivos parametros

