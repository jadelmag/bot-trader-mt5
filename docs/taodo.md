
quiero que cuando se pulse en el boton Detectar patrones de velas se abra el modal detect_candle_modal.py y ahi pueda seleccionar todas los patrones de velas que hay en candle_list.py.

El modal contendra los siguiente:

1. un titulo.
2. dos botones en una misma fila alineados a la derecha, seleccionar todos,  deseleccionar todos y cargar todas las estrategias.
    - seleccionar todos: selecciona todos los patrones de velas.
    - deseleccionar todos: deselecciona todos los patrones de velas.
    - cargar todas las estrategias: carga todas las estrategias que hay en la carpeta strategies.
3. todos los patrones de velas en esta estructura:
    - una fila con un checkbox, un label del nombre del patron, substituyendo la _ por espacio y quitando el is. un dropdown y dos botones.
    - un boton de configurar estrategia, que abrira el modal candle_config_mdal.py. El cual mostrara los campos de la estrategia en modo de tabs y se podra modificar las siguientes configuraciones y dos botones: cancelar el cual cierra el modal actual (de configuracion) y guardar el cual guardara la configuracion en un json en la carpeta strategies.
        {
            "use_signal_change": true,
            "use_stop_loss": true,
            "use_take_profit": true,
            "use_trailing_stop": false,
            "use_pattern_reversal": false,
            "atr_sl_multiplier": 1.5,
            "atr_tp_multiplier": 3.0,
            "atr_trailing_multiplier": 1.5
        }
    - un boton de cargar estrategia, cargara la estrategia del patron de la fila y lo obtendra de la carpeta strategies.   

4. El dropdown tendra dos opciones default: en el que no se le pasara ninguna configuracion a los patrones de velas y custom en el que tendra una configuracion y se le pasara a los patrones de velas.

5. Finalmente tendra dos botones en una misma fila, alineados en el centro. 
    - un boton de guardar, que aplicara todas las configuraciones seleccionadas a los patrones de vela.
    - un boton de cancelar, que cerrara el modal.




Ahora vamos a pasar a cuando se pulsa en detectar estrategias forex.

Cuando se pulsa en detectar estrategias forex se muestra el modal detect_all_forex_modal.py.

Este modal tendra:
1. un titulo
2. dos botones en una misma fila alineados a la derecha, seleccionar todos,  deseleccionar todos y cargar todas las estrategias.
3. una lista con todas las estrategias forex que hay en forex_list.py
4. cada fila tendra un checkbox, un label del nombre de la estrategia forex.

5. Finalmente tendra dos botones en una misma fila, alineados en el centro. 
    - un boton de cancelar, que cerrara el modal. (a la izquierda)
    - un boton de iniciar, que detectara todas las estrategias seleccionadas y las aplicara en la grafica. (a la derecha)
6. Se mostrara un resumen de las estrategias seleccionadas. apply_strategies.py
    - Tendra la siguiente estructura:
        - nombre de la estrategia forex | numero de veces que se ha podido aplicar | beneficios: dinero que hubiese generado si se hubiese aplicado | perdidas: dinero que hubiese perdido si se hubiese aplicado mal o en el peor de los casos.
        - Dinero general de todas las estrategias
        - Dinero perdido de todas las estrategias


