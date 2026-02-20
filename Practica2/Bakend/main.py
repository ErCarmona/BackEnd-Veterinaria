from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from BBDD_vete    import BaseDatos
import dependencias

# Routers de cada módulo
import duenos
import mascotas
import citas
import estadisticas



app = FastAPI(
    title       = "🐾 Clínica Veterinaria API",
    description = "API para gestionar dueños, mascotas y citas",
    version     = "2.0.0"
)

# Instancia de la base de datos
db = BaseDatos()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # En producción: solo tu dominio
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.on_event("startup")
async def al_arrancar():
    """
    Se ejecuta automáticamente cuando el servidor arranca.
    Conecta a PostgreSQL, crea las tablas y registra el pool
    en dependencias.py para que los routers lo puedan usar.
    """
    await db.conectar()

    # Registrar el pool en el módulo de dependencias
    # para que todos los routers puedan acceder con Depends(get_db)
    dependencias.set_pool(db.pool)

    print("🚀 Servidor listo en http://localhost:8000")
    print("📖 Documentación en http://localhost:8000/docs")


@app.on_event("shutdown")
async def al_apagar():
    """Se ejecuta cuando el servidor se apaga. Cierra las conexiones."""
    await db.desconectar()



app.include_router(duenos.router)
app.include_router(mascotas.router)
app.include_router(citas.router)
app.include_router(estadisticas.router)

@app.get("/", tags=["Info"])
async def inicio():
    """Comprueba que el servidor está funcionando."""
    return {
        "estado":        "✅ funcionando",
        "documentacion": "http://localhost:8000/docs"
    }
