import asyncpg

# Dirección de la base de datos
DATABASE_URL = "postgresql://vetuser:vetpass@localhost:5432/vetclinic"


class BaseDatos:
    """
    Clase que gestiona la conexión con PostgreSQL.

    Uso:
        db = BaseDatos()
        await db.conectar()          # Al arrancar el servidor
        await db.desconectar()       # Al apagar el servidor

        async with db.pool.acquire() as conn:
            filas = await conn.fetch("SELECT * FROM duenos")
    """

    def __init__(self):
        # pool = reserva de conexiones listas para usar
        # (es más eficiente que abrir/cerrar una conexión cada vez)
        self.pool = None

    async def conectar(self):
        """Conecta a PostgreSQL y crea las tablas si no existen."""

        # Crear el pool de conexiones
        self.pool = await asyncpg.create_pool(DATABASE_URL)

        # Crear las tablas
        await self._crear_tablas()

        print("✅ Base de datos conectada")

    async def desconectar(self):
        """Cierra todas las conexiones. Se llama al apagar el servidor."""
        if self.pool:
            await self.pool.close()
            print("🔌 Base de datos desconectada")

    async def _crear_tablas(self):
        """
        Crea las tres tablas de la clínica si aún no existen.
        El IF NOT EXISTS hace que sea seguro llamarlo cada vez que arranca el servidor.
        """
        async with self.pool.acquire() as conn:
            await conn.execute("""

                -- ─────────────────────────────────────────
                -- TABLA: duenos
                -- Personas propietarias de las mascotas
                -- ─────────────────────────────────────────
                CREATE TABLE IF NOT EXISTS duenos (
                    id            SERIAL PRIMARY KEY,
                    nombre        TEXT NOT NULL,
                    email         TEXT UNIQUE NOT NULL,
                    telefono      TEXT,
                    direccion     TEXT,

                    -- JSONB: campo flexible para datos de contacto extra
                    -- Ejemplo: {"contacto_preferido": "whatsapp", "telefono_emergencia": "600..."}
                    info_contacto JSONB DEFAULT '{}'::jsonb,

                    creado_en     TIMESTAMP DEFAULT NOW()
                );


                -- ─────────────────────────────────────────
                -- TABLA: mascotas
                -- Pacientes de la clínica. Cada mascota
                -- pertenece a un dueño.
                -- ─────────────────────────────────────────
                CREATE TABLE IF NOT EXISTS mascotas (
                    id          SERIAL PRIMARY KEY,

                    -- Clave foránea: si borramos el dueño,
                    -- sus mascotas se borran también (CASCADE)
                    dueno_id    INTEGER REFERENCES duenos(id) ON DELETE CASCADE,

                    nombre      TEXT NOT NULL,
                    especie     TEXT NOT NULL,
                    raza        TEXT,
                    fecha_nac   DATE,
                    peso_kg     NUMERIC(5,2),

                    -- JSONB: información médica flexible
                    -- Ejemplo: {"alergias": ["penicilina"], "microchip": "985...", "esterilizado": true}
                    info_medica JSONB DEFAULT '{}'::jsonb,

                    creado_en   TIMESTAMP DEFAULT NOW()
                );


                -- ─────────────────────────────────────────
                -- TABLA: citas
                -- Visitas a la clínica. Cada cita está
                -- ligada a una mascota y a su dueño.
                -- ─────────────────────────────────────────
                CREATE TABLE IF NOT EXISTS citas (
                    id          SERIAL PRIMARY KEY,
                    mascota_id  INTEGER REFERENCES mascotas(id) ON DELETE CASCADE,
                    dueno_id    INTEGER REFERENCES duenos(id)   ON DELETE CASCADE,
                    fecha_hora  TIMESTAMP NOT NULL,
                    motivo      TEXT NOT NULL,

                    -- Solo puede tener uno de estos cuatro valores
                    estado      TEXT DEFAULT 'programada'
                                CHECK (estado IN ('programada','completada','cancelada','no_asistio')),

                    notas       TEXT,

                    -- JSONB: detalles de la consulta
                    -- Ejemplo: {"sintomas": ["fiebre"], "veterinario": "Dr. López", "coste": 50}
                    datos_cita  JSONB DEFAULT '{}'::jsonb,

                    creado_en   TIMESTAMP DEFAULT NOW()
                );


                -- ─────────────────────────────────────────
                -- ÍNDICES: aceleran las búsquedas
                -- ─────────────────────────────────────────

                -- Índices normales (por columna)
                CREATE INDEX IF NOT EXISTS idx_mascotas_dueno ON mascotas(dueno_id);
                CREATE INDEX IF NOT EXISTS idx_citas_mascota  ON citas(mascota_id);
                CREATE INDEX IF NOT EXISTS idx_citas_fecha    ON citas(fecha_hora);

                -- Índices GIN: especiales para buscar DENTRO de campos JSONB
                CREATE INDEX IF NOT EXISTS idx_info_medica ON mascotas USING GIN(info_medica);
                CREATE INDEX IF NOT EXISTS idx_datos_cita  ON citas    USING GIN(datos_cita);

            """)
