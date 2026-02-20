import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import date

from funciones     import fila_a_dict, lista_a_dicts
from dependencias  import get_db

router = APIRouter(
    prefix="/mascotas",
    tags=["Mascotas"]
)



class InfoMedica(BaseModel):
    """
    Información médica de la mascota.
    Se guarda como JSONB: estructura flexible que no
    requiere cambios en la tabla para añadir nuevos campos.
    """
    alergias:     Optional[List[str]] = []    # Ej: ["penicilina", "ácaros"]
    condiciones:  Optional[List[str]] = []    # Enfermedades crónicas
    vacunas:      Optional[List[str]] = []    # Vacunas puestas
    microchip:    Optional[str]       = None  # ID del microchip
    esterilizado: Optional[bool]      = None  # True/False/None (no se sabe)
    notas:        Optional[str]       = None  # Observaciones del vet


class CrearMascota(BaseModel):
    """Datos necesarios para registrar una mascota."""
    dueno_id:    int
    nombre:      str
    especie:     str                    # perro, gato, ave, conejo, reptil, otro
    raza:        Optional[str]   = None
    fecha_nac:   Optional[date]  = None
    peso_kg:     Optional[float] = None
    info_medica: InfoMedica      = InfoMedica()



@router.get("")
async def listar_mascotas(
    especie:  Optional[str] = None,
    dueno_id: Optional[int] = None,
    db=Depends(get_db)
):
    """
    Devuelve todas las mascotas registradas.

    Parámetros opcionales:
        ?especie=gato      →  solo gatos
        ?dueno_id=3        →  solo las mascotas del dueño 3

    Ejemplos:
        GET /mascotas
        GET /mascotas?especie=perro
        GET /mascotas?dueno_id=2
    """
    async with db.acquire() as conn:

        # JOIN para incluir el nombre del dueño en la respuesta
        consulta = """
            SELECT m.*, d.nombre AS nombre_dueno
            FROM mascotas m
            JOIN duenos d ON d.id = m.dueno_id
            WHERE 1=1
        """
        parametros = []
        contador   = 1

        if especie:
            consulta += f" AND m.especie ILIKE ${contador}"
            parametros.append(f"%{especie}%")
            contador += 1

        if dueno_id:
            consulta += f" AND m.dueno_id = ${contador}"
            parametros.append(dueno_id)
            contador += 1

        consulta += " ORDER BY m.id DESC"
        filas = await conn.fetch(consulta, *parametros)

    return lista_a_dicts(filas)


@router.post("", status_code=201)
async def crear_mascota(datos: CrearMascota, db=Depends(get_db)):
    """
    Registra una nueva mascota en el sistema.

    Ejemplo de body JSON:
    {
        "dueno_id": 1,
        "nombre": "Rocky",
        "especie": "perro",
        "raza": "Labrador",
        "peso_kg": 25.5,
        "info_medica": {
            "alergias": ["penicilina"],
            "microchip": "985112345678901",
            "esterilizado": true
        }
    }
    """
    async with db.acquire() as conn:

        # Verificar que el dueño existe antes de crear la mascota
        dueno = await conn.fetchrow(
            "SELECT id FROM duenos WHERE id = $1", datos.dueno_id
        )
        if not dueno:
            raise HTTPException(status_code=404, detail="El dueño especificado no existe")

        fila = await conn.fetchrow(
            """
            INSERT INTO mascotas
                (dueno_id, nombre, especie, raza, fecha_nac, peso_kg, info_medica)
            VALUES
                ($1, $2, $3, $4, $5, $6, $7::jsonb)
            RETURNING *
            """,
            datos.dueno_id,
            datos.nombre,
            datos.especie,
            datos.raza,
            datos.fecha_nac,
            datos.peso_kg,
            json.dumps(datos.info_medica.model_dump())
        )

    return fila_a_dict(fila)


@router.get("/{mascota_id}")
async def ver_mascota(mascota_id: int, db=Depends(get_db)):
    """
    Devuelve los datos de una mascota y su historial completo de citas.

    Ejemplo:
        GET /mascotas/1
    """
    async with db.acquire() as conn:

        mascota = await conn.fetchrow(
            """
            SELECT m.*, d.nombre AS nombre_dueno, d.telefono AS telefono_dueno
            FROM mascotas m
            JOIN duenos d ON d.id = m.dueno_id
            WHERE m.id = $1
            """,
            mascota_id
        )
        if not mascota:
            raise HTTPException(status_code=404, detail="Mascota no encontrada")

        # Historial de citas (las más recientes primero)
        citas = await conn.fetch(
            "SELECT * FROM citas WHERE mascota_id = $1 ORDER BY fecha_hora DESC",
            mascota_id
        )

        resultado                   = fila_a_dict(mascota)
        resultado["historial_citas"] = lista_a_dicts(citas)

    return resultado


@router.patch("/{mascota_id}")
async def actualizar_mascota(mascota_id: int, datos: dict, db=Depends(get_db)):
    """
    Actualiza uno o varios campos de una mascota.
    Solo hay que enviar los campos que se quieren cambiar.

    Campos permitidos: nombre, raza, fecha_nac, peso_kg, info_medica

    Ejemplos:
        Cambiar solo el peso:
            PATCH /mascotas/1
            Body: { "peso_kg": 26.5 }

        Actualizar info médica (JSONB):
            PATCH /mascotas/1
            Body: { "info_medica": { "alergias": ["penicilina"] } }
    """
    async with db.acquire() as conn:

        mascota = await conn.fetchrow(
            "SELECT * FROM mascotas WHERE id = $1", mascota_id
        )
        if not mascota:
            raise HTTPException(status_code=404, detail="Mascota no encontrada")

        # Solo permitir actualizar estos campos (evitar SQL injection)
        campos_permitidos = {"nombre", "raza", "fecha_nac", "peso_kg", "info_medica"}
        campos = {k: v for k, v in datos.items() if k in campos_permitidos}

        if not campos:
            return fila_a_dict(mascota)  # Nada que cambiar

        # Construir "nombre = $1, peso_kg = $2" dinámicamente
        partes  = []
        valores = []
        i = 1

        for campo, valor in campos.items():
            if campo == "info_medica":
                partes.append(f"{campo} = ${i}::jsonb")  # Cast necesario para JSONB
                valores.append(json.dumps(valor))
            else:
                partes.append(f"{campo} = ${i}")
                valores.append(valor)
            i += 1

        valores.append(mascota_id)
        fila = await conn.fetchrow(
            f"UPDATE mascotas SET {', '.join(partes)} WHERE id = ${i} RETURNING *",
            *valores
        )

    return fila_a_dict(fila)


@router.delete("/{mascota_id}", status_code=204)
async def borrar_mascota(mascota_id: int, db=Depends(get_db)):
    """
    Borra una mascota y todas sus citas (CASCADE).

    Ejemplo:
        DELETE /mascotas/1
    """
    async with db.acquire() as conn:
        resultado = await conn.execute(
            "DELETE FROM mascotas WHERE id = $1", mascota_id
        )
        if resultado == "DELETE 0":
            raise HTTPException(status_code=404, detail="Mascota no encontrada")
