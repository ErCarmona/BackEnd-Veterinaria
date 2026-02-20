from datetime import datetime, date


def fila_a_dict(fila) -> dict | None:
    """
    Convierte una fila de PostgreSQL a un diccionario Python normal.

    El problema es que asyncpg devuelve un tipo especial (Record),
    no un dict normal. Además, las fechas hay que convertirlas a texto
    para que el frontend las pueda leer en formato JSON.

    Ejemplo:
        fila = <Record id=1 nombre='Ana' creado_en=datetime(2025,1,1)>
        fila_a_dict(fila) → {"id": 1, "nombre": "Ana", "creado_en": "2025-01-01T00:00:00"}

    Parámetros:
        fila: una fila de asyncpg (o None si no se encontró el registro)

    Devuelve:
        Un dict con todos los campos, o None si la fila era None
    """
    if fila is None:
        return None

    resultado = dict(fila)

    # Recorrer todos los campos y convertir fechas a texto ISO 8601
    # ISO 8601 es el formato estándar: "2025-03-15" o "2025-03-15T10:30:00"
    for clave, valor in resultado.items():
        if isinstance(valor, (datetime, date)):
            resultado[clave] = valor.isoformat()

    return resultado


def lista_a_dicts(filas: list) -> list[dict]:
    """
    Convierte una lista de filas de PostgreSQL a una lista de dicts.

    Es un atajo para no escribir el bucle en cada sitio:
        [fila_a_dict(f) for f in filas]

    Ejemplo:
        filas = [<Record id=1>, <Record id=2>]
        lista_a_dicts(filas) → [{"id": 1}, {"id": 2}]
    """
    return [fila_a_dict(f) for f in filas]
