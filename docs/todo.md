
## TODO

1. Optimizar las estrategias forex para generar más ganancias y menos perdidas. [DOING]
2. Testear estrategia Market M1 [TODO]
3. Vista RSI ✅
4. Vista ATR ✅
5. VISTA MACD ✅
6. Vista ADMI

----------------------
quier que crees en body_macd lo siguiente:
1- crear vista MACD que se muestra igual en metatrader5 entre la grafica ATR (BodyATR) y logger (BodyLogger), para ello trendras que actualizar el gui_main.py y el body_builder.py

2- al hacer hover sobre la linea de MACD debe mostrar un toolip indicando:
MACD([EMA rapida, EMA lenta, MACD SMA])
fecha y hora
valor actual

3- se debera mostrar la informacion en la grafica cuando se pulse en Iniciar MT5 que es donde ya se ha seleccionado el timeframe y la moneda y se debe actualizar la grafica cuando se cree una nueva vela


----------------------


En las vistas RSI, ATR y MACD quiero poder hacer las siguientes acciones sobre la grafica:

- zoom in y zoom out: con la rueda del boton central del raton
- zoom a una zona haciendo drag con el click izquierdo y aparecera un cuadrado con lineas dash de color gris y cuando suelte se hara zoom ha esa zona.
- pan: mientras se mantiene el boton derecho y se mueve el raton
- volver al estado inicial: haciendo click con el boton central del raton 2 veces 

