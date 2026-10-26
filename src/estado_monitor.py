"""Lógica pura del monitor: convierte registros, eventos y latido en el estado que se muestra.

Sin I/O: recibe todo por parámetro para poder probarla con casos controlados. Nunca copia usuarios
ni contraseñas de los empleados.

Estados de un marcaje (entrada o salida) de un empleado:
  pendiente      aún no llega su hora
  vencida        pasó su hora (+ gracia) y no hay marcaje registrado        -> CRÍTICO
  marcada        registrada por el programador, todavía sin confirmar por el portal
  confirmada     el portal lo confirma (segundo login, o el propio portal lo mostró)
  no_confirmada  el segundo login vio que el portal SIGUE ofreciendo el botón  -> CRÍTICO
  desactivado / no_aplica (domingo, festivo, no trabaja ese día)
"""
import re
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple

from src.empleados import _HORARIO_DEFAULT, obtener_horario_dia

GRACIA_SEG = 180        # tras la hora programada, tolerancia antes de dar el marcaje por vencido
CONFIRMANDO_SEG = 300   # tras marcar, ventana en que "esperando confirmación" es normal
LATIDO_MAX_SEG = 90     # sin latido en este tiempo = programador caído

_DIAS_AP = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_TIPOS = {
    "semana": ("ENTRADA SEMANA (L-V)", "SALIDA SEMANA (L-V)"),
    "sabado": ("ENTRADA SÁBADO", "SALIDA SÁBADO"),
}
_ORDEN_NIVEL = {"ok": 0, "aviso": 1, "critico": 2}


def confirmacion_de(accion: str, boton: Optional[str]) -> Optional[bool]:
    """¿Confirma el portal que el marcaje de `accion` ("Entrada"/"Salida") se registró?

    True  si el portal ya no ofrece el botón de esa acción (ofrece el otro: la marca quedó).
    False si lo sigue ofreciendo (la marca NO quedó).
    None  si no es concluyente (el portal no ofrece ningún botón, o no se pudo consultar).
    """
    if boton == accion:
        return False
    if boton in ("Entrada", "Salida"):
        return True
    return None


def _hms(texto: Optional[str]) -> Optional[time]:
    try:
        partes = [int(p) for p in str(texto).split(":")]
        return time(partes[0], partes[1], partes[2] if len(partes) > 2 else 0)
    except (ValueError, IndexError, TypeError):
        return None


def _iso(texto: Optional[str]) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(texto))
    except (ValueError, TypeError):
        return None


def _horario(emp: Dict) -> Dict:
    return {**_HORARIO_DEFAULT, **(emp.get("horario") or {})}


def _tipo_dia(emp: Dict, ahora: datetime, festivo: bool) -> str:
    if ahora.weekday() == 6:
        return "domingo"
    if festivo:
        return "festivo"
    if ahora.weekday() == 5:
        return "sabado" if _horario(emp).get("trabaja_sabados", True) else "no_trabaja"
    return "semana"


def _programada(emp: Dict, plan: Optional[Dict], ahora: datetime, accion: str) -> Optional[str]:
    """Hora programada de hoy: la del plan real del programador (con su escalonado) o, sin él, la base."""
    del_plan = ((plan or {}).get(emp.get("id")) or {}).get(_DIAS_AP[ahora.weekday()]) or {}
    if del_plan.get(accion):
        return del_plan[accion]
    try:
        h = obtener_horario_dia(_horario(emp), ahora.weekday())
    except Exception:
        return None
    hh, mm = (h["entrada_hora"], h["entrada_minuto"]) if accion == "entrada" else (h["salida_hora"], h["salida_minuto"])
    return f"{hh:02d}:{mm:02d}:00"


def _estado_accion(emp, accion, tipo_dia, ahora, registro, eventos_emp, plan) -> Dict:
    accion_portal = "Entrada" if accion == "entrada" else "Salida"
    clave_tipo = _TIPOS[tipo_dia][0 if accion == "entrada" else 1]
    hoy = ahora.strftime("%Y-%m-%d")
    marca = ((registro or {}).get(hoy) or {}).get(clave_tipo)
    if marca and marca.get("ejecutado") is False:  # anulada: el portal la contradijo, no cuenta como marca
        marca = None

    exitos = sum(1 for e in eventos_emp
                 if e.get("tipo") == "marcaje" and e.get("accion") == accion_portal and e.get("resultado") == "ok")
    intentos = sum(1 for e in eventos_emp
                   if e.get("tipo") == "marcaje" and e.get("esperada") == accion_portal)
    confirmaciones = [e for e in eventos_emp if e.get("tipo") == "confirmacion" and e.get("accion") == accion_portal]
    confirmada = confirmaciones[-1].get("confirmada") if confirmaciones else None
    if confirmada is None and marca:
        # Sin confirmación propia, cualquier login posterior a la marca que vea el portal ofreciendo
        # ese mismo botón demuestra que la marca no quedó (el registro local la daba por hecha).
        vistos = [e for e in eventos_emp if e.get("tipo") == "estado_portal"
                  and str(e.get("ts", "")) > str(marca.get("hora") or "")]
        if vistos and vistos[-1].get("boton") == accion_portal:
            confirmada = False

    programada = _programada(emp, plan, ahora, accion)
    resultado = {"programada": programada, "estado": "pendiente", "hora": None, "origen": None,
                 "intentos": intentos, "exitos": exitos, "duplicada": exitos > 1,
                 "confirmada": confirmada, "detalle": ""}

    if marca:
        resultado["hora"] = (marca.get("hora") or "")[11:19] or None
        resultado["origen"] = marca.get("origen") or "desconocido"
        if confirmada is True or resultado["origen"] == "portal":
            resultado["estado"] = "confirmada"
            resultado["detalle"] = "confirmada por el portal"
        elif confirmada is False:
            resultado["estado"] = "no_confirmada"
            resultado["detalle"] = "el portal SIGUE ofreciendo este botón: la marca puede no haber quedado"
        else:
            resultado["estado"] = "marcada"
            marcada_en = _iso(marca.get("hora"))
            reciente = marcada_en is not None and 0 <= (ahora - marcada_en).total_seconds() <= CONFIRMANDO_SEG
            resultado["detalle"] = "esperando confirmación del portal…" if reciente else "sin confirmación independiente"
        return resultado

    hora_prog = _hms(programada)
    if hora_prog is not None:
        limite = datetime.combine(ahora.date(), hora_prog).timestamp() + GRACIA_SEG
        if ahora.timestamp() > limite:
            resultado["estado"] = "vencida"
            resultado["detalle"] = "pasó su hora y no hay marcaje registrado"
            reintentos = [e for e in eventos_emp
                          if e.get("tipo") == "reintento_programado" and e.get("tipo_marcaje") == clave_tipo]
            if reintentos:
                resultado["detalle"] += f" · reintento {reintentos[-1].get('reintento')} programado"
    return resultado


def describir(evento: Dict) -> Dict:
    """Texto corto y nivel (ok/aviso/error) de un evento para la lista de actividad."""
    tipo = evento.get("tipo")
    nivel, texto = "ok", str(tipo)
    if tipo == "programador_inicio":
        texto = f"Programador iniciado (PID {evento.get('pid')}, {evento.get('empleados', '?')} empleados)"
    elif tipo == "programador_fin":
        nivel, texto = "aviso", "Programador detenido"
    elif tipo == "login":
        if evento.get("ok"):
            texto = f"Login correcto ({evento.get('ms', '?')} ms)"
        else:
            nivel, texto = "error", f"Login FALLIDO: {evento.get('motivo') or 'sin detalle'}"
    elif tipo == "estado_portal":
        texto = f"El portal ofrece: {evento.get('boton') or 'ningún botón'}"
    elif tipo == "marcaje":
        if evento.get("resultado") == "ok":
            texto = f"Clic en Marcar {evento.get('accion')}"
        else:
            nivel, texto = "aviso", f"Marcaje no realizado ({evento.get('esperada') or 'manual'})"
    elif tipo == "registro":
        texto = f"Registro local: {evento.get('tipo_marcaje')} ({evento.get('origen')})"
    elif tipo == "confirmacion":
        conf = evento.get("confirmada")
        if conf is True:
            texto = f"Confirmado por el portal ({evento.get('accion')})"
        elif conf is False:
            nivel, texto = "error", f"NO confirmado: el portal sigue ofreciendo '{evento.get('boton')}'"
        else:
            nivel, texto = "aviso", "Confirmación no concluyente (sin botón o sin conexión)"
    elif tipo == "alerta":
        nivel, texto = "error", f"ALERTA: {evento.get('mensaje')}"
    return {"hora": str(evento.get("ts", ""))[11:19], "nombre": evento.get("nombre") or "—",
            "tipo": tipo, "texto": texto, "nivel": nivel}


def _bloque_programador(ahora: datetime, latido: Optional[Dict], eventos: List[Dict], instancias: Optional[int]) -> Dict:
    bloque = {"vivo": False, "edad_seg": None, "pid": None, "inicio": None, "fase": None,
              "scheduler_ok": None, "instancias": instancias,
              "arranques_hoy": sum(1 for e in eventos if e.get("tipo") == "programador_inicio")}
    if not latido:
        return bloque
    ts = _iso(latido.get("ts"))
    bloque.update(pid=latido.get("pid"), inicio=latido.get("inicio"), fase=latido.get("fase"))
    if ts is not None:
        bloque["edad_seg"] = max(0, int((ahora - ts).total_seconds()))
        bloque["vivo"] = bloque["edad_seg"] <= LATIDO_MAX_SEG
    if bloque["vivo"] and latido.get("fase") == "activo":
        tick = _iso(latido.get("tick_scheduler"))
        bloque["scheduler_ok"] = tick is not None and (ahora - tick).total_seconds() <= LATIDO_MAX_SEG
    return bloque


def calcular_estado(
    ahora: datetime,
    empleados: List[Dict],
    registros: Dict[str, Dict],
    eventos: List[Dict],
    latido: Optional[Dict],
    alertas_hoy: Optional[List[Dict]] = None,
    instancias: Optional[int] = None,
    festivo: bool = False,
) -> Dict:
    """Estado completo del día para el monitor (estructura JSON-serializable, sin credenciales)."""
    plan = (latido or {}).get("plan") or {}
    filas, mensajes, nivel = [], [], "ok"

    def subir(n: str, msg: str) -> None:
        nonlocal nivel
        mensajes.append({"nivel": n, "texto": msg})
        if _ORDEN_NIVEL[n] > _ORDEN_NIVEL[nivel]:
            nivel = n

    resumen = {"empleados": 0, "entrada": {}, "salida": {}}
    hay_jornada = False

    for emp in empleados:
        emp_id = emp.get("id")
        propios = [e for e in eventos if e.get("emp_id") == emp_id]
        logins = [e for e in propios if e.get("tipo") == "login"]
        ultimo_login = logins[-1] if logins else None
        fila = {
            "id": emp_id, "nombre": emp.get("nombre"), "activo": emp.get("activo", True),
            "dia": None, "entrada": None, "salida": None,
            "login": ({"ok": bool(ultimo_login.get("ok")), "hora": str(ultimo_login.get("ts", ""))[11:19],
                       "motivo": ultimo_login.get("motivo")} if ultimo_login else None),
            "fallos_login": sum(1 for e in logins if not e.get("ok")),
        }
        if not emp.get("activo", True):
            fila["dia"] = "desactivado"
            filas.append(fila)
            continue

        tipo_dia = _tipo_dia(emp, ahora, festivo)
        fila["dia"] = tipo_dia
        if tipo_dia in _TIPOS:
            hay_jornada = True
            resumen["empleados"] += 1
            registro = registros.get(emp_id) or {}
            for accion in ("entrada", "salida"):
                est = _estado_accion(emp, accion, tipo_dia, ahora, registro, propios, plan)
                fila[accion] = est
                resumen[accion][est["estado"]] = resumen[accion].get(est["estado"], 0) + 1
                nombre = emp.get("nombre")
                if est["estado"] == "vencida":
                    subir("critico", f"{nombre}: {accion} VENCIDA ({est['programada']}), sin marcaje registrado")
                elif est["estado"] == "no_confirmada":
                    subir("critico", f"{nombre}: {accion} NO confirmada por el portal")
                if est["duplicada"]:
                    subir("aviso", f"{nombre}: {accion} con {est['exitos']} clics exitosos (posible duplicado)")
            if (fila["login"] and not fila["login"]["ok"]
                    and fila["entrada"]["estado"] in ("pendiente", "vencida")):
                subir("aviso", f"{emp.get('nombre')}: su último login falló ({fila['login']['motivo'] or 'sin detalle'})")
        filas.append(fila)

    programador = _bloque_programador(ahora, latido, eventos, instancias)
    if not programador["vivo"]:
        edad = programador["edad_seg"]
        detalle = "no hay latido (¿nunca arrancó hoy?)" if edad is None else f"último latido hace {edad // 60} min {edad % 60} s"
        subir("critico" if hay_jornada else "aviso", f"El programador no da señales de vida: {detalle}")
    elif programador["scheduler_ok"] is False:
        subir("critico", "El proceso está vivo pero el scheduler no responde: no se ejecutarán marcajes")
    if instancias is not None and instancias > 1:
        subir("aviso", f"Hay {instancias} instancias del programador corriendo (debe ser 1)")

    alertas_hoy = alertas_hoy or []
    por_usuario: Dict[str, int] = {}
    for a in alertas_hoy:
        por_usuario[a.get("nombre", "?")] = por_usuario.get(a.get("nombre", "?"), 0) + 1

    return {
        "ahora": ahora.isoformat(timespec="seconds"),
        "nivel": nivel,
        "mensajes": mensajes,
        "programador": programador,
        "resumen": resumen,
        "empleados": filas,
        "actividad": [describir(e) for e in reversed(eventos[-25:])],
        "alertas": {"total": len(alertas_hoy), "por_usuario": por_usuario},
    }


_MIN_SECRETO = 4  # un secreto más corto mutilaría líneas del log sin proteger nada útil


def censurar_linea(linea: str, secretos: List[str]) -> str:
    """Oculta usuarios y contraseñas antes de mostrar una línea de log en la página.

    geovictoria.py escribe "Usuario: <usuario>" en su log, así que el monitor nunca debe servir una
    línea sin pasar por aquí: se tapa el valor tras "Usuario:" y cualquier usuario o contraseña
    configurados que aparezca literalmente.
    """
    linea = re.sub(r"(Usuario:\s*)\S+", r"\1***", linea, flags=re.IGNORECASE)
    for secreto in secretos:
        if secreto and len(secreto) >= _MIN_SECRETO:
            linea = linea.replace(secreto, "***")
    return linea


def ultimas_lineas_censuradas(texto: str, cuantas: int, secretos: List[str]) -> List[str]:
    """Las últimas `cuantas` líneas no vacías de `texto`, ya censuradas."""
    lineas = [l.rstrip("\r") for l in texto.split("\n") if l.strip()]
    return [censurar_linea(l, secretos) for l in lineas[-max(cuantas, 0):]] if cuantas else []


def marcajes_sin_confirmar(registro_hoy: Optional[Dict], eventos: List[Dict], emp_id: str) -> List[Tuple[str, str]]:
    """Marcajes de hoy hechos por el programador que aún no tienen confirmación del portal.

    Devuelve (tipo_marcaje, accion). Sirve para reconciliar tras un reinicio: la confirmación
    independiente es un job en memoria y se pierde si el programador se reinicia (o si el marcaje
    lo hizo una versión anterior). Se omiten los detectados en el portal y los que ya tienen una
    confirmación concluyente (True o False: un False ya generó su alerta).
    """
    pendientes: List[Tuple[str, str]] = []
    for tipo, marca in (registro_hoy or {}).items():
        if not isinstance(marca, dict) or not marca.get("ejecutado") or marca.get("origen") == "portal":
            continue
        accion = "Entrada" if "ENTRADA" in tipo.upper() else "Salida"
        resultados = [e.get("confirmada") for e in eventos
                      if e.get("tipo") == "confirmacion" and e.get("emp_id") == emp_id and e.get("accion") == accion]
        if resultados and resultados[-1] is not None:
            continue
        pendientes.append((tipo, accion))
    return pendientes


_ANTES_SEG = 120      # un marcaje programado en los próximos 2 min bloquea el reinicio
_DESPUES_SEG = GRACIA_SEG  # y hasta que venza su gracia: puede estar ejecutándose o esperando navegador


def bloqueo_por_marcaje(estado: Dict, ahora: datetime) -> Optional[str]:
    """Motivo por el que NO conviene reiniciar o detener el programador ahora, o None si se puede.

    Un reinicio a mitad de un marcaje lo deja a medias, y uno recién hecho pierde su confirmación
    independiente (job en memoria). Se bloquea si hay un marcaje a punto de ejecutarse, en curso o
    esperando su confirmación.
    """
    for fila in estado.get("empleados", []):
        for accion in ("entrada", "salida"):
            a = fila.get(accion) or {}
            if a.get("estado") == "pendiente":
                hora = _hms(a.get("programada"))
                if hora is None:
                    continue
                falta = (datetime.combine(ahora.date(), hora) - ahora).total_seconds()
                if -_DESPUES_SEG <= falta <= _ANTES_SEG:
                    return f"{fila.get('nombre')}: su {accion} está programada a las {a['programada']}"
            elif a.get("estado") == "marcada" and str(a.get("detalle", "")).startswith("esperando"):
                return f"{fila.get('nombre')}: se está confirmando su {accion} en el portal"
    return None


def pendientes_de_marcar(estado: Dict) -> List[Dict]:
    """Marcajes de hoy que hay que hacer: vencidos o contradichos por el portal.

    Devuelve [{"id", "nombre", "accion"}] con accion "entrada" o "salida". Los usa el botón
    "Marcar pendientes" del monitor; quien marca vuelve a comprobar el portal antes de cada clic,
    así que esta lista nunca basta por sí sola para marcar.
    """
    pendientes: List[Dict] = []
    for fila in estado.get("empleados", []):
        for accion in ("entrada", "salida"):
            if (fila.get(accion) or {}).get("estado") in ("vencida", "no_confirmada"):
                pendientes.append({"id": fila.get("id"), "nombre": fila.get("nombre"), "accion": accion})
    return pendientes
