
## TODO

1. Crear los funciones de:
   - Iniciar simulación
   - Abrir operación manual
   - Modificar estrategias
   - Cancelar simulación

2. Crear estrategias customizadas de poca ganancia pero segura.
3. Optimizar las estrategias forex y los patrones de velas para generar más ganancias y menos perdidas.


creo que hay un error en config_app_modal.py.
Me has puesto Limite de dinero (stop loss global) en el modal de configuración.

Yo lo que quiero es que si tengo 500$ en mi cuenta, que no se me permita abrir operaciones cuando llegue a 100$. A eso me refiero con Limite de dinero.

Por ejemplo de esos 500$ me han generado 500$ de beneficios, por lo que tengo 1000$ de dinero para invertir, entonces yo pongo 500$ en el limite de dinero. Entonces el bot no abre operaciones cuando llegue a 500$ y las que hay abiertas espera para intenta cerrarlas lo mas proximo a 0 posible para evitar pérdidas que puedan cubrir los 500€ que quedan.