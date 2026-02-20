

import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from funciones     import fila_a_dict, lista_a_dicts
from dependencias  import get_db

router = APIRouter(
    prefix="/citas",
    tags=["Citas"]
)

# Los cuatro estados posibles de una cita
ESTADOS_VALIDOS = ["programada", "completada", "cancelada", "no_asistio"]



class DatosCita(BaseModel):
    """
    Detalles de la consulta veterinaria.
    Se guarda como JSONB: flexible y extensible
    sin necesidad de alterar la estructura de la tabla.
    """
    sintomas:             Optional[List[str]] = []          # Síntomas de la mascota
    tratamiento:          Optional[str]       = None        # Tratamiento aplicado
    veterinario:          Optional[str]       = None        # Nombre del veterinario
    coste:                Optional[float]     = None        # Precio en euros
    pago:                 Optional[str]       = "pendiente" # pendiente | pagado | parcial
    requiere_seguimiento: Optional[bool]      = False       # Si hay revisión posterior


class CrearCita(BaseModel):
    """Datos necesarios para crear una cita."""
    mascota_id: int
    dueno_id:   int
    fecha_hora: datetime           # Ej: "2025-03-15T10:30:00"
    motivo:     str
    notas:      Optional[str]  = None
    datos_cita: DatosCita      = DatosCita()



@router.get("")
async def listar_citas(
    estado:     Optional[str] = None,
    mascota_id: Optional[int] = None,
    db=Depends(get_db)
):
    """
    Devuelve todas las citas con información de la mascota y el dueño.

    Parámetros opcionales:
        ?estado=programada    →  solo citas programadas
        ?mascota_id=2         →  solo citas de esa mascota

    Estados: programada, completada, cancelada, no_asistio

    Ejemplos:
        GET /citas
        GET /citas?estado=programada
        GET /citas?mascota_id=1
    """
    async with db.acquire() as conn:

        consulta = """
            SELECT
                c.*,
                m.nombre   AS nombre_mascota,
                m.especie,
                d.nombre   AS nombre_dueno,
                d.telefono AS telefono_dueno
            FROM citas c
            JOIN mascotas m ON m.id = c.mascota_id
            JOIN duenos   d ON d.id = c.dueno_id
            WHERE 1=1
        """
        parametros = []
        contador   = 1

        if estado:
            consulta += f" AND c.estado = ${contador}"
            parametros.append(estado)
            contador += 1

        if mascota_id:
            consulta += f" AND c.mascota_id = ${contador}"
            parametros.append(mascota_id)
            contador += 1

        consulta += " ORDER BY c.fecha_hora ASC"
        filas = await conn.fetch(consulta, *parametros)

    return lista_a_dicts(filas)


@router.get("/hoy")
async def citas_de_hoy(db=Depends(get_db)):
    """
    Devuelve solo las citas del día de hoy.
    Útil para la agenda diaria del dashboard.

    Ejemplo:
        GET /citas/hoy
    """
    async with db.acquire() as conn:
        filas = await conn.fetch(
            """
            SELECT
                c.*,
                m.nombre   AS nombre_mascota,
                m.especie,
                d.nombre   AS nombre_dueno,
                d.telefono AS telefono_dueno
            FROM citas c
            JOIN mascotas m ON m.id = c.mascota_id
            JOIN duenos   d ON d.id = c.dueno_id
            WHERE DATE(c.fecha_hora) = CURRENT_DATE
            ORDER BY c.fecha_hora ASC
            """
        )
    return lista_a_dicts(filas)


@router.post("", status_code=201)
async def crear_cita(datos: CrearCita, db=Depends(get_db)):
    """
    Crea una nueva cita en el sistema.

    Ejemplo de body JSON:
    {
        "mascota_id": 1,
        "dueno_id": 1,
        "fecha_hora": "2025-03-15T10:30:00",
        "motivo": "Revisión anual",
        "datos_cita": {
            "veterinario": "Dr. López",
            "sintomas": ["fiebre leve"],
            "coste": 45.00
        }
    }
    """
    async with db.acquire() as conn:

        # Verificar que la mascota existe
        mascota = await conn.fetchrow(
            "SELECT id FROM mascotas WHERE id = $1", datos.mascota_id
        )
        if not mascota:
            raise HTTPException(status_code=404, detail="La mascota no existe")

        fila = await conn.fetchrow(
            """
            INSERT INTO citas
                (mascota_id, dueno_id, fecha_hora, motivo, notas, datos_cita)
            VALUES
                ($1, $2, $3, $4, $5, $6::jsonb)
            RETURNING *
            """,
            datos.mascota_id,
            datos.dueno_id,
            datos.fecha_hora,
            datos.motivo,
            datos.notas,
            json.dumps(datos.datos_cita.model_dump())
        )

    return fila_a_dict(fila)


@router.patch("/{cita_id}/estado")
async def cambiar_estado(cita_id: int, nuevo_estado: str, db=Depends(get_db)):
    """
    Cambia el estado de una cita.

    Estados posibles:
        programada  →  pendiente de realizarse
        completada  →  la consulta ya tuvo lugar
        cancelada   →  se canceló antes de la fecha
        no_asistio  →  el paciente no apareció

    Ejemplo:
        PATCH /citas/1/estado?nuevo_estado=completada
    """
    if nuevo_estado not in ESTADOS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Estado no válido. Opciones: {ESTADOS_VALIDOS}"
        )

    async with db.acquire() as conn:
        fila = await conn.fetchrow(
            "UPDATE citas SET estado = $1 WHERE id = $2 RETURNING *",
            nuevo_estado, cita_id
        )
        if not fila:
            raise HTTPException(status_code=404, detail="Cita no encontrada")

    return fila_a_dict(fila)


@router.delete("/{cita_id}", status_code=204)
async def borrar_cita(cita_id: int, db=Depends(get_db)):
    """
    Borra una cita por su ID.

    Ejemplo:
        DELETE /citas/1
    """
    async with db.acquire() as conn:
        resultado = await conn.execute(
            "DELETE FROM citas WHERE id = $1", cita_id
        )
        if resultado == "DELETE 0":
            raise HTTPException(status_code=404, detail="Cita no encontrada")
