
## TODO

1. Optimizar las estrategias forex para generar más ganancias y menos perdidas. [DOING]
2. Testear estrategia Market M1 [TODO]
3. Vista RSI ✅
4. Vista ATR ✅
5. VISTA MACD ✅
6. Vista Momentum
6. Vista ADMI

----------------------
quiero que crees en body_momentum.py lo siguiente:
1- crear vista Momentum que se muestra igual en metatrader5 entre la grafica MACD (BodyMACD) y logger (BodyLogger), para ello trendras que actualizar el gui_main.py y el body_builder.py

2- al hacer hover sobre la linea de MACD debe mostrar un toolip indicando:
Momentum([Periodo])
fecha y hora
valor

3- se debera mostrar la informacion en la grafica cuando se pulse en Iniciar MT5 que es donde ya se ha seleccionado el timeframe y la moneda y se debe actualizar la grafica cuando se cree una nueva vela

4- la grafica momentum tendra las siguientes acciones:

- zoom in y zoom out: con la rueda del boton central del raton
- zoom a una zona haciendo drag con el click izquierdo y aparecera un cuadrado con lineas dash de color gris y cuando suelte se hara zoom ha esa zona.
- pan: mientras se mantiene el boton derecho y se mueve el raton
- volver al estado inicial: haciendo click con el boton central del raton 2 veces 

----------------------


En las vistas RSI, ATR y MACD quiero poder hacer las siguientes acciones sobre la grafica:

- zoom in y zoom out: con la rueda del boton central del raton
- zoom a una zona haciendo drag con el click izquierdo y aparecera un cuadrado con lineas dash de color gris y cuando suelte se hara zoom ha esa zona.
- pan: mientras se mantiene el boton derecho y se mueve el raton
- volver al estado inicial: haciendo click con el boton central del raton 2 veces 

---------------------------


He añadido las siguientes graficas: 
- body_atr.py
- body_macd.py
- body_rsi.py
- body_momentum.py

Quiero que actualices el fichero simulation.py para que no trabaje con datos creados dinamicamente, sino que obtengas los valores en tiempo real de ATR, MACD, RSI y Momentum para:

1. Mejorar las estrategias forex
2. Mejorar los patrones de velas
3. Mejorar la predicción de velas y de estrategias forex

Es decir quiero que trabajes con datos reales de atr, macd, rsi y momentum y elimines los datos creados dinamicamente para obtener esos valores.






