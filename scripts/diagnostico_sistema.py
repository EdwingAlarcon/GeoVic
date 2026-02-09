"""
Script de diagnóstico completo del sistema de marcajes
Verifica estado del programador, registro de ejecuciones y posibles problemas
"""
import json
import sys
import subprocess
from datetime import date, datetime
from pathlib import Path

# Colores para la consola
try:
    import colorama
    colorama.init()
    GREEN = colorama.Fore.GREEN
    YELLOW = colorama.Fore.YELLOW
    RED = colorama.Fore.RED
    RESET = colorama.Style.RESET_ALL
except ImportError:
    GREEN = YELLOW = RED = RESET = ""

script_dir = Path(__file__).parent.parent / "src" / "logs"
registro_file = script_dir / "registro_ejecuciones.json"
lock_file = script_dir / "programador.lock"

def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def print_ok(text):
    print(f"{GREEN}✅ {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠️  {text}{RESET}")

def print_error(text):
    print(f"{RED}❌ {text}{RESET}")

def verificar_procesos():
    """Verifica cuántas instancias del programador están corriendo"""
    print_header("PROCESOS PYTHON ACTIVOS")
    
    try:
        result = subprocess.run(
            ['powershell', '-Command', 
             'Get-Process | Where-Object {$_.ProcessName -match "python"} | Format-Table ProcessName, Id, StartTime -AutoSize'],
            capture_output=True,
            text=True
        )
        
        lines = [l for l in result.stdout.split('\n') if 'python' in l.lower()]
        count = len(lines)
        
        if count == 0:
            print_warning("No hay procesos Python activos")
            print("  • El programador NO está corriendo")
        elif count == 1:
            print_ok(f"1 proceso Python activo (correcto)")
            print(result.stdout)
        else:
            print_error(f"{count} procesos Python activos (¡PROBLEMA!)")
            print("  • Hay múltiples instancias del programador")
            print("  • Ejecute: scripts\\detener_todas_instancias.bat")
            print()
            print(result.stdout)
    
    except Exception as e:
        print_error(f"Error verificando procesos: {e}")

def verificar_lock_file():
    """Verifica el estado del archivo de lock"""
    print_header("ARCHIVO DE LOCK")
    
    if lock_file.exists():
        try:
            with open(lock_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Verificar antigüedad del archivo
            lock_age = datetime.now().timestamp() - lock_file.stat().st_mtime
            lock_age_hours = lock_age / 3600
            
            print_ok("Lock file existe")
            print(f"  • PID: {pid}")
            print(f"  • Antigüedad: {lock_age_hours:.1f} horas")
            print(f"  • Ruta: {lock_file}")
            
            # Verificar si el proceso existe
            try:
                import psutil
                if psutil.pid_exists(pid):
                    print_ok(f"Proceso PID {pid} está activo")
                else:
                    print_warning(f"Proceso PID {pid} NO existe (lock obsoleto)")
                    print("  • Elimine el lock file o reinicie el programador")
            except ImportError:
                print_warning("psutil no disponible - No se puede verificar si el proceso existe")
            
        except Exception as e:
            print_error(f"Error leyendo lock file: {e}")
    else:
        print_warning("Lock file NO existe")
        print("  • El programador probablemente NO está corriendo")
        print("  • O se detuvo incorrectamente")

def verificar_registro_ejecuciones():
    """Verifica el registro de ejecuciones"""
    print_header("REGISTRO DE EJECUCIONES")
    
    if not registro_file.exists():
        print_warning("Archivo de registro no existe")
        return
    
    try:
        with open(registro_file, 'r', encoding='utf-8') as f:
            registro = json.load(f)
        
        hoy = date.today().isoformat()
        
        # Mostrar registro de hoy
        if hoy in registro:
            print_ok(f"Hay registros para hoy ({hoy}):")
            for tipo_marcaje, datos in registro[hoy].items():
                hora = datos.get('hora', 'N/A')
                variacion = datos.get('variacion_minutos', 0)
                
                # Extraer solo la hora (HH:MM:SS)
                try:
                    hora_obj = datetime.fromisoformat(hora)
                    hora_str = hora_obj.strftime('%H:%M:%S')
                    
                    # Verificar si es sospechoso (entrada y salida muy cercanas)
                    if tipo_marcaje == "SALIDA SEMANA (L-V)" or tipo_marcaje == "SALIDA SÁBADO":
                        # Verificar si hay entrada
                        tipo_entrada = "ENTRADA SEMANA (L-V)" if "SEMANA" in tipo_marcaje else "ENTRADA SÁBADO"
                        if tipo_entrada in registro[hoy]:
                            hora_entrada = datetime.fromisoformat(registro[hoy][tipo_entrada]['hora'])
                            diferencia_minutos = (hora_obj - hora_entrada).total_seconds() / 60
                            
                            if diferencia_minutos < 60:  # Menos de 1 hora entre entrada y salida
                                print_error(f"  • {tipo_marcaje}: {hora_str} (variación: {variacion:+d} min)")
                                print(f"    ⚠️  SOSPECHOSO: Solo {diferencia_minutos:.0f} minutos después de entrada")
                                print("    → Ejecute: scripts\\limpiar_registro_hoy.bat")
                            else:
                                print_ok(f"  • {tipo_marcaje}: {hora_str} (variación: {variacion:+d} min)")
                        else:
                            print_ok(f"  • {tipo_marcaje}: {hora_str} (variación: {variacion:+d} min)")
                    else:
                        print_ok(f"  • {tipo_marcaje}: {hora_str} (variación: {variacion:+d} min)")
                except:
                    print(f"  • {tipo_marcaje}: {hora} (variación: {variacion:+d} min)")
        else:
            print_warning(f"No hay registros para hoy ({hoy})")
            print("  • Los marcajes se ejecutarán en sus horarios programados")
        
        # Mostrar últimos 3 días
        print("\n📅 Últimos 3 días:")
        fechas = sorted(registro.keys(), reverse=True)[:3]
        for fecha in fechas:
            if fecha == hoy:
                continue  # Ya se mostró arriba
            print(f"\n  {fecha}:")
            for tipo_marcaje, datos in registro[fecha].items():
                hora = datos.get('hora', 'N/A')
                try:
                    hora_obj = datetime.fromisoformat(hora)
                    hora_str = hora_obj.strftime('%H:%M:%S')
                    print(f"    • {tipo_marcaje}: {hora_str}")
                except:
                    print(f"    • {tipo_marcaje}: {hora}")
    
    except Exception as e:
        print_error(f"Error leyendo registro: {e}")

def verificar_logs_recientes():
    """Verifica los logs más recientes"""
    print_header("LOGS RECIENTES")
    
    log_file = script_dir / f"programador_{datetime.now().strftime('%Y%m%d')}.log"
    
    if log_file.exists():
        print_ok(f"Log de hoy existe: {log_file}")
        
        try:
            # Leer últimas 20 líneas
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Buscar errores o advertencias
            errores = [l for l in lines if '❌' in l or 'ERROR' in l]
            advertencias = [l for l in lines if '⚠️' in l or 'WARNING' in l]
            
            print(f"  • Total líneas: {len(lines)}")
            print(f"  • Errores: {len(errores)}")
            print(f"  • Advertencias: {len(advertencias)}")
            
            if errores:
                print("\n  Últimos errores:")
                for error in errores[-3:]:  # Últimos 3 errores
                    print(f"    {error.strip()}")
            
            if advertencias:
                print("\n  Últimas advertencias:")
                for adv in advertencias[-3:]:  # Últimas 3 advertencias
                    print(f"    {adv.strip()}")
        
        except Exception as e:
            print_error(f"Error leyendo log: {e}")
    else:
        print_warning("No hay log para hoy")

def main():
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 20 + "DIAGNÓSTICO COMPLETO" + " " * 28 + "║")
    print("║" + " " * 15 + "Sistema de Marcajes GeoVictoria" + " " * 22 + "║")
    print("╚" + "═" * 68 + "╝")
    
    verificar_procesos()
    verificar_lock_file()
    verificar_registro_ejecuciones()
    verificar_logs_recientes()
    
    print_header("RESUMEN")
    print()
    print("📋 Acciones recomendadas:")
    print("  1. Si hay múltiples procesos Python:")
    print("     → Ejecute: scripts\\detener_todas_instancias.bat")
    print()
    print("  2. Si el registro de hoy tiene datos incorrectos:")
    print("     → Ejecute: scripts\\limpiar_registro_hoy.bat")
    print()
    print("  3. Si el programador no está corriendo:")
    print("     → Ejecute: scripts\\iniciar_programador.bat")
    print()
    print("  4. Para detener el programador:")
    print("     → Ejecute: scripts\\detener_tarea_programada.bat")
    print()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print_error(f"Error en diagnóstico: {e}")
    finally:
        print()
        input("Presione Enter para salir...")
