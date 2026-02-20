# El pool se asigna desde main.py cuando arranca el servidor
# (se hace así para evitar importaciones circulares)
_pool = None


def set_pool(pool):
    """Lo llama main.py una vez que la base de datos está conectada."""
    global _pool
    _pool = pool


def get_db():
    """
    Devuelve el pool de conexiones.
    FastAPI lo llama automáticamente en cada petición
    gracias a Depends(get_db).
    """
    return _pool
