#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para verificar el estado de ejecuciones de marcaje
"""
import json
import os
from datetime import date, datetime
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
LOG_DIR = BASE_DIR / "src" / "logs"
REGISTRO_FILE = LOG_DIR / "registro_ejecuciones.json"

def leer_registro():
    """Lee el archivo de registro de ejecuciones"""
    try:
        if REGISTRO_FILE.exists():
            with open(REGISTRO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"❌ Error leyendo registro: {e}")
    return {}

def mostrar_estado_hoy():
    """Muestra el estado de marcajes de hoy"""
    hoy = str(date.today())
    registro = leer_registro()
    
    print(f"\n{'=' * 80}")
    print(f"📊 ESTADO DE MARCAJES GEOVICTORIA")
    print(f"{'=' * 80}")
    print(f"\n📅 Fecha: {date.today().strftime('%A, %d de %B de %Y')}")
    print(f"⏰ Hora actual: {datetime.now().strftime('%H:%M:%S')}")
    
    if hoy in registro:
        print(f"\n✅ MARCAJES DE HOY:")
        print(f"{'-' * 80}")
        
        for tipo_marcaje, datos in registro[hoy].items():
            hora_ejecucion = datetime.fromisoformat(datos['hora'])
            variacion = datos.get('variacion_minutos', 0)
            
            print(f"\n✓ {tipo_marcaje}")
            print(f"  🕐 Hora: {hora_ejecucion.strftime('%H:%M:%S')}")
            if variacion != 0:
                print(f"  🎲 Variación: {variacion:+d} minutos")
    else:
        print(f"\n❌ NO HAY MARCAJES REGISTRADOS PARA HOY")
        print(f"   Posibles razones:")
        print(f"   • El programador no se ha ejecutado aún")
        print(f"   • Es día festivo o domingo")
        print(f"   • Aún no es la hora programada")
    
    print(f"\n{'=' * 80}")

def mostrar_ultimos_dias(dias=5):
    """Muestra resumen de últimos días"""
    registro = leer_registro()
    fechas = sorted(registro.keys(), reverse=True)[:dias]
    
    print(f"\n📆 HISTORIAL DE ÚLTIMOS {dias} DÍAS:")
    print(f"{'-' * 80}")
    
    for fecha in fechas:
        fecha_obj = datetime.fromisoformat(fecha).date()
        marcajes = registro[fecha]
        
        print(f"\n{fecha_obj.strftime('%A, %d/%m/%Y')}:")
        for tipo, datos in marcajes.items():
            hora = datetime.fromisoformat(datos['hora']).strftime('%H:%M')
            print(f"  ✓ {tipo}: {hora}")
    
    print(f"\n{'-' * 80}")

def verificar_logs_hoy():
    """Verifica si existen logs de hoy"""
    fecha_log = datetime.now().strftime('%Y%m%d')
    programador_log = LOG_DIR / f"programador_{fecha_log}.log"
    geovictoria_log = LOG_DIR / f"geovictoria_{fecha_log}.log"
    
    print(f"\n📋 ARCHIVOS DE LOG:")
    print(f"{'-' * 80}")
    
    if programador_log.exists():
        size = programador_log.stat().st_size
        print(f"✓ Programador: {programador_log.name} ({size:,} bytes)")
        
        # Buscar mensajes importantes en el log
        with open(programador_log, 'r', encoding='utf-8') as f:
            lineas = f.readlines()
            errores = [l for l in lineas if 'ERROR' in l or 'Error' in l]
            marcajes = [l for l in lineas if 'completado exitosamente' in l]
            
            if errores:
                print(f"  ⚠️  {len(errores)} error(es) encontrado(s)")
            if marcajes:
                print(f"  ✓ {len(marcajes)} marcaje(s) completado(s)")
    else:
        print(f"⚠️  Programador: No hay log de hoy")
    
    if geovictoria_log.exists():
        size = geovictoria_log.stat().st_size
        print(f"✓ GeoVictoria: {geovictoria_log.name} ({size:,} bytes)")
    else:
        print(f"⚠️  GeoVictoria: No hay log de hoy")
    
    print(f"{'-' * 80}")

def main():
    """Función principal"""
    print(f"\n🔍 VERIFICADOR DE ESTADO DE MARCAJES")
    
    mostrar_estado_hoy()
    mostrar_ultimos_dias(5)
    verificar_logs_hoy()
    
    print(f"\n✅ Verificación completada")
    print(f"\n💡 TIP: Ejecuta este script en cualquier momento para ver el estado\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Verificación cancelada por el usuario")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
