
## TODO

1. Crear los funciones de:
   - Iniciar simulación [DOING]
   - Abrir operación manual
   - Modificar estrategias
   - Cancelar simulación

2. Crear estrategias customizadas de poca ganancia pero segura.
3. Optimizar las estrategias forex y los patrones de velas para generar más ganancias y menos perdidas.


creo que hay un error en config_app_modal.py.
Me has puesto Limite de dinero (stop loss global) en el modal de configuración.

Yo lo que quiero es que si tengo 500$ en mi cuenta, que no se me permita abrir operaciones cuando llegue a 100$. A eso me refiero con Limite de dinero.

Por ejemplo de esos 500$ me han generado 500$ de beneficios, por lo que tengo 1000$ de dinero para invertir, entonces yo pongo 500$ en el limite de dinero. Entonces el bot no abre operaciones cuando llegue a 500$ y las que hay abiertas espera para intenta cerrarlas lo mas proximo a 0 posible para evitar pérdidas que puedan cubrir los 500€ que quedan.



1. Quiero que cuando se pulse en iniciar simulación, se abra un modal identico que cuando se pulsa en Aplicar Estrategias (Herramientas). El modal se llama simulation_strategies_modal.py

2. Quiero que elimines del modal simulation_strategies_modal.py capital inicial.


El fichero simulation.py se encargara de la siguiente logica:
1. Analizara la grafica que se ha cargado para ver como es el precio y la tendencia del mercado, analizara la media movil y toda la informacion que pueda sacar.
2. Trigger con media móvil

   - Usar la línea de media móvil como “señal maestra” para detectar momentos de entrada/salida es una buena simplificación.

   - El problema: una sola media móvil suele dar señales atrasadas. Lo habitual es usar cruces de medias (rápida vs lenta) o combinar con otros indicadores para más precisión.

3. Aplicación de estrategias Forex y patrones de velas

   - Bien que lo pongas como siguiente paso: no abrir operación solo por la media móvil, sino validarlo con patrones de velas o estrategias adicionales (ej. RSI, MACD, soportes/resistencias).

   - Esto reduce señales falsas.

4. Apertura de operaciones (long/short)

   - Correcto que contemples ambos escenarios (alcista y bajista).

   - Lo ideal es definir criterios claros:

   - ¿Abrirás un long si el precio cruza hacia arriba la media?

   - ¿Abrirás un short si cruza hacia abajo?

   - ¿O necesitas confirmación de otro patrón primero?

5. Cierre de operaciones (take profit / stop loss)

   - Aquí está lo más crítico: no puedes depender solo de la media móvil.

   - Necesitas reglas de salida claras:

   - Take profit: cerrar al alcanzar X% de beneficio o cierto soporte/resistencia.

   - Stop loss: salir si el precio se gira y baja X% para evitar pérdidas grandes.

   - También puedes usar Trailing Stop (ajustar stop a medida que el precio avanza a favor).

6. ⚙️ Recomendaciones de mejora

   - Usar 2 medias móviles (rápida y lenta) para señales más confiables.

   - Combinar con otro indicador (ej. RSI o MACD) como confirmación.

   - Definir reglas claras de salida → take profit y stop loss automáticos.

   - Simulación realista → incluir spread, slippage y gestión de capital (riesgo por operación).





<!-- 3. Cuando se pulse en iniciar simulación, se debe iniciar la simulación con las estrategias seleccionadas en el modal simulation_strategies_modal.py.
El fichero simulation.py se encargara de la logica para iniciar la simulación con la siguiente logica:
   - La línea de media móvil (moving average) se encargara de detectar cuando es el mejor momento para aplicar estrategias forex y patrones de velas.
   - Primero intentara detectar cuando es el mejor momento para aplicar estrategias forex y patrones de velas. 
   - Cuando lo detecte abrira operaciones short y long y siguiendo las estrategias forex y patrones de velas.
   - Finalmente cerrara las operaciones cuando detecte que es el mejor momento para obtener el maximo beneficio y evitar en todo lo posible pérdidas. -->






4. 


- 

