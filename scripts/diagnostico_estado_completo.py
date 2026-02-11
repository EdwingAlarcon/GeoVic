"""
Script para verificar el estado actual del sistema de marcajes
"""
import sys
import json
from datetime import datetime, date
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.programador import (
    leer_registro_ejecuciones, 
    ya_se_ejecuto_hoy,
    verificar_marcajes_pendientes
)

def main():
    print("=" * 80)
    print("🔍 DIAGNÓSTICO DEL SISTEMA DE MARCAJES")
    print("=" * 80)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Verificar registro de ejecuciones
    print("📋 REGISTRO DE EJECUCIONES:")
    print("-" * 80)
    registro = leer_registro_ejecuciones()
    
    if not registro or registro == {}:
        print("⚠️  Registro vacío - No hay marcajes registrados")
    else:
        # Mostrar últimos 7 días
        fechas = sorted(registro.keys(), reverse=True)[:7]
        for fecha in fechas:
            print(f"\n📅 {fecha}:")
            for tipo_marcaje, info in registro[fecha].items():
                hora = info.get('hora', 'N/A')
                if isinstance(hora, str):
                    try:
                        hora_obj = datetime.fromisoformat(hora)
                        hora_str = hora_obj.strftime('%H:%M:%S')
                    except:
                        hora_str = hora
                else:
                    hora_str = str(hora)
                
                variacion = info.get('variacion_minutos', 0)
                if variacion != 0:
                    print(f"  ✅ {tipo_marcaje}: {hora_str} (variación: {variacion:+d} min)")
                else:
                    print(f"  ✅ {tipo_marcaje}: {hora_str}")
    
    print("\n" + "=" * 80)
    print("📅 ESTADO DE HOY:")
    print("-" * 80)
    
    hoy = date.today()
    dia_semana = hoy.weekday()
    
    # Determinar tipos de marcaje según el día
    if dia_semana == 5:  # Sábado
        tipo_entrada = "ENTRADA SÁBADO"
        tipo_salida = "SALIDA SÁBADO"
    elif dia_semana == 6:  # Domingo
        print("📅 Hoy es domingo - No hay marcajes programados")
        tipo_entrada = None
        tipo_salida = None
    else:  # Lunes a Viernes
        tipo_entrada = "ENTRADA SEMANA (L-V)"
        tipo_salida = "SALIDA SEMANA (L-V)"
    
    if tipo_entrada:
        entrada_hecha = ya_se_ejecuto_hoy(tipo_entrada)
        salida_hecha = ya_se_ejecuto_hoy(tipo_salida)
        
        print(f"Entrada: {'✅ Registrada' if entrada_hecha else '❌ Pendiente'} ({tipo_entrada})")
        print(f"Salida:  {'✅ Registrada' if salida_hecha else '❌ Pendiente'} ({tipo_salida})")
    
    print("\n" + "=" * 80)
    print("🔍 VERIFICANDO MARCAJES PENDIENTES...")
    print("=" * 80)
    
    # Ejecutar verificación
    verificar_marcajes_pendientes()
    
    print("\n" + "=" * 80)
    print("✅ DIAGNÓSTICO COMPLETADO")
    print("=" * 80)

if __name__ == "__main__":
    main()
