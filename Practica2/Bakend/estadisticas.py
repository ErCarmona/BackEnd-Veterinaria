from fastapi import APIRouter, Depends
from dependencias import get_db

router = APIRouter(
    prefix="/estadisticas",
    tags=["Dashboard"]
)


@router.get("")
async def obtener_estadisticas(db=Depends(get_db)):
    """
    Devuelve un resumen con los números clave de la clínica.

    Respuesta de ejemplo:
    {
        "total_duenos": 12,
        "total_mascotas": 20,
        "total_citas": 45,
        "citas_hoy": 3,
        "proximas_citas": 8,
        "mascotas_por_especie": [
            {"especie": "perro", "total": 10},
            {"especie": "gato",  "total": 7}
        ]
    }
    """
    async with db.acquire() as conn:

        # fetchval devuelve un único valor escalar (el resultado del COUNT)
        total_duenos   = await conn.fetchval("SELECT COUNT(*) FROM duenos")
        total_mascotas = await conn.fetchval("SELECT COUNT(*) FROM mascotas")
        total_citas    = await conn.fetchval("SELECT COUNT(*) FROM citas")

        # DATE() extrae solo la fecha (sin la hora) para comparar con hoy
        citas_hoy = await conn.fetchval(
            "SELECT COUNT(*) FROM citas WHERE DATE(fecha_hora) = CURRENT_DATE"
        )

        # Citas que están programadas y aún no han pasado
        proximas = await conn.fetchval(
            "SELECT COUNT(*) FROM citas WHERE estado = 'programada' AND fecha_hora >= NOW()"
        )

        # Cuántas mascotas hay de cada especie, de más a menos
        por_especie = await conn.fetch(
            "SELECT especie, COUNT(*) AS total FROM mascotas GROUP BY especie ORDER BY total DESC"
        )

    return {
        "total_duenos":         total_duenos,
        "total_mascotas":       total_mascotas,
        "total_citas":          total_citas,
        "citas_hoy":            citas_hoy,
        "proximas_citas":       proximas,
        "mascotas_por_especie": [dict(r) for r in por_especie]
    }
