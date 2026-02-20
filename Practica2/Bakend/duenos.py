import json
import asyncpg
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from funciones     import fila_a_dict, lista_a_dicts
from dependencias  import get_db

router = APIRouter(
    prefix="/duenos",
    tags=["Dueños"]
)


class InfoContacto(BaseModel):
    """
    Datos de contacto extra del dueño.
    Se guarda como JSONB en la base de datos.
    """
    contacto_preferido:  Optional[str] = "telefono"  # telefono | email | whatsapp
    telefono_emergencia: Optional[str] = None
    notas:               Optional[str] = None


class CrearDueno(BaseModel):
    """Datos necesarios para crear un dueño."""
    nombre:        str
    email:         str
    telefono:      Optional[str]  = None
    direccion:     Optional[str]  = None
    info_contacto: InfoContacto   = InfoContacto()



@router.get("")
async def listar_duenos(buscar: Optional[str] = None, db=Depends(get_db)):
    """
    Devuelve la lista de todos los dueños.

    Parámetros opcionales:
        ?buscar=Ana  →  filtra por nombre o email que contengan "Ana"

    Ejemplos:
        GET /duenos
        GET /duenos?buscar=garcia
    """
    async with db.acquire() as conn:
        if buscar:
            # ILIKE = búsqueda sin distinción de mayúsculas
            # Los % permiten encontrar el texto en cualquier posición
            filas = await conn.fetch(
                "SELECT * FROM duenos WHERE nombre ILIKE $1 OR email ILIKE $1 ORDER BY id DESC",
                f"%{buscar}%"
            )
        else:
            filas = await conn.fetch("SELECT * FROM duenos ORDER BY id DESC")

    return lista_a_dicts(filas)


@router.post("", status_code=201)
async def crear_dueno(datos: CrearDueno, db=Depends(get_db)):
    """
    Crea un nuevo dueño en la base de datos.

    Ejemplo de body JSON:
    {
        "nombre": "Ana García",
        "email": "ana@email.com",
        "telefono": "600 123 456",
        "info_contacto": {
            "contacto_preferido": "whatsapp",
            "telefono_emergencia": "600 999 888"
        }
    }
    """
    async with db.acquire() as conn:
        try:
            fila = await conn.fetchrow(
                """
                INSERT INTO duenos (nombre, email, telefono, direccion, info_contacto)
                VALUES ($1, $2, $3, $4, $5::jsonb)
                RETURNING *
                """,
                datos.nombre,
                datos.email,
                datos.telefono,
                datos.direccion,
                # model_dump() → dict de Python, json.dumps() → texto JSON para Postgres
                json.dumps(datos.info_contacto.model_dump())
            )
            return fila_a_dict(fila)

        except asyncpg.UniqueViolationError:
            # El email ya está registrado (columna UNIQUE)
            raise HTTPException(
                status_code=409,
                detail="Ya existe un dueño registrado con ese email"
            )


@router.get("/{dueno_id}")
async def ver_dueno(dueno_id: int, db=Depends(get_db)):
    """
    Devuelve los datos de un dueño y la lista de sus mascotas.

    Ejemplo:
        GET /duenos/1
    """
    async with db.acquire() as conn:

        dueno = await conn.fetchrow(
            "SELECT * FROM duenos WHERE id = $1", dueno_id
        )
        if not dueno:
            raise HTTPException(status_code=404, detail="Dueño no encontrado")

        mascotas = await conn.fetch(
            "SELECT * FROM mascotas WHERE dueno_id = $1 ORDER BY id", dueno_id
        )

        resultado             = fila_a_dict(dueno)
        resultado["mascotas"] = lista_a_dicts(mascotas)

    return resultado


@router.delete("/{dueno_id}", status_code=204)
async def borrar_dueno(dueno_id: int, db=Depends(get_db)):
    """
    Borra un dueño y, en cascada, todas sus mascotas y citas.

    Ejemplo:
        DELETE /duenos/1
    """
    async with db.acquire() as conn:
        resultado = await conn.execute(
            "DELETE FROM duenos WHERE id = $1", dueno_id
        )
        if resultado == "DELETE 0":
            raise HTTPException(status_code=404, detail="Dueño no encontrado")
