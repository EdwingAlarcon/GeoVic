"""
Sistema de caché simple para estado de GeoVictoria
Evita múltiples consultas redundantes en corto tiempo
"""
from datetime import datetime, timedelta
from typing import Optional, Dict
import threading

class CacheEstado:
    """Cache thread-safe para el estado del botón en GeoVictoria"""
    
    def __init__(self, ttl_segundos: int = 60):
        """
        Args:
            ttl_segundos: Tiempo de vida del caché en segundos (default: 60s)
        """
        self._cache: Dict[str, tuple[Optional[str], datetime]] = {}
        self._ttl = timedelta(seconds=ttl_segundos)
        self._lock = threading.Lock()
    
    def get(self, key: str = "estado_actual") -> Optional[str]:
        """
        Obtiene el estado del caché si aún es válido
        
        Returns:
            Estado del botón ("Entrada", "Salida", None) o None si no hay caché válido
        """
        with self._lock:
            if key not in self._cache:
                return None
            
            estado, timestamp = self._cache[key]
            
            # Verificar si el caché expiró
            if datetime.now() - timestamp > self._ttl:
                del self._cache[key]
                return None
            
            return estado
    
    def set(self, estado: Optional[str], key: str = "estado_actual") -> None:
        """
        Guarda el estado en el caché
        
        Args:
            estado: Estado del botón ("Entrada", "Salida", None)
        """
        with self._lock:
            self._cache[key] = (estado, datetime.now())
    
    def invalidar(self, key: str = "estado_actual") -> None:
        """Invalida el caché para forzar una nueva verificación"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def limpiar_todo(self) -> None:
        """Limpia todo el caché"""
        with self._lock:
            self._cache.clear()

# Instancia global del caché
_cache_global = CacheEstado(ttl_segundos=60)

def get_cache() -> CacheEstado:
    """Retorna la instancia global del caché"""
    return _cache_global
