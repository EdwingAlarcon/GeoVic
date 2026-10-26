# Scripts de GeoVic (Windows)

Doble clic en el `.bat` que necesites. Todos usan el Python del entorno virtual (`.venv`) si existe.

## Uso diario

| Script | Para qué sirve |
|---|---|
| `iniciar_programador.bat` | Inicia el programador en una ventana "Programador GeoVictoria" (déjala abierta; puedes minimizarla) |
| `reiniciar_programador.bat` | Lo detiene y lo vuelve a iniciar. Úsalo tras editar `config\employees.json` o `config\festivos_adicionales.json`: el programador solo lee esos archivos al arrancar |
| `detener_programador.bat` | Lo detiene matando solo los procesos de `programador.py` (no toca otros Python) |
| `detener_monitor.bat` | Detiene solo el monitor (procesos de `monitor.py`); no toca el programador |
| `inicio_con_windows.bat` | **Interruptor** del arranque con Windows: crea o borra un acceso directo en la carpeta Inicio que lanza `iniciar_al_inicio.bat` al iniciar sesión. Sin Tareas Programadas ni Administrador. Solo arranca si ese usuario inicia sesión tras el reinicio |
| `ver_estado.bat` | Muestra qué marcajes se registraron hoy |
| `ver_log_en_vivo.bat` | Sigue el log del programador en tiempo real. Opcional: el monitor ya trae el panel **Log en vivo** (con usuarios y claves ocultos) |
| `monitor.bat` | **Monitor web en vivo**: por empleado, hora programada, estado (pendiente / marcada / **confirmada por el portal** / **NO confirmada** / **vencida**), último login y actividad; latido del programador, instancias y alertas, más un panel **Log en vivo** y los botones **Reiniciar / Detener / Iniciar** del programador (solo desde el propio servidor; avisan antes de reiniciar en mitad de un marcaje) y **Marcar pendientes (N)**, que aparece cuando alguien está VENCIDA o NO confirmada: marca solo si el portal ofrece ese botón, así que no duplica. Abre `http://127.0.0.1:8765`. Deja la ventana abierta mientras lo uses |
| `diagnostico_sistema.bat` | Instancias del programador, lock, registro, logs recientes y **alertas de hoy por usuario** |
| `probar_login.bat` | Prueba el login de **un** empleado (también desactivado), **sin marcar**, y explica por qué falla: credenciales mal copiadas, contraseña rechazada, cuenta bloqueada, cambio de clave, segundo factor… Guarda una captura. Uso: `probar_login.bat emp15`. Con `probar_login.bat --todos` revisa a **todos los activos, uno por uno**, y dice si el portal ofrece "Marcar Salida" (entrada ya registrada) o "Marcar Entrada" (aún no); es la comprobación de verdad contra el portal. Nunca hace clic en un botón de marcaje |

## Marcaje manual y recuperación

| Script | Para qué sirve |
|---|---|
| `ejecutar_manual.bat` | Un marcaje manual |
| `marcar_salida_ahora.bat` | Marca la salida de todos los empleados (recupera una salida perdida) |
| `limpiar_registro_hoy.bat` | Borra el registro de hoy. ⚠️ Permite volver a marcar: úsalo solo si el registro quedó con datos incorrectos |

## Instalación y utilidades

| Script | Para qué sirve |
|---|---|
| `verificar_instalacion.bat` | Comprueba Python, dependencias y estructura tras instalar |
| `ver_festivos.bat` | Festivos de Colombia del año |
| `eliminar_tarea_programada.bat` | Quita la Tarea Programada "GeoVictoria Programador" si quedó de una versión anterior |

En la raíz del proyecto: `setup.bat` (primera instalación), `actualizar_servidor.bat` (actualizar desde el zip: primero cierra el programador y el monitor **con sus ventanas**, incluidas las vacías que se hayan acumulado, y luego deja una consola de cada uno y abre la página del monitor) y `exportar_proyecto.bat` (generar el zip).

## Una sola instancia

El programador impide por sí mismo que corran dos a la vez (exclusión del sistema operativo): un segundo arranque sale con "Programador ya en ejecución". Un `programador.lock` viejo no estorba.

## Si Windows no deja ejecutar un `.bat`

Clic derecho → Propiedades → Desbloquear → Aceptar.
