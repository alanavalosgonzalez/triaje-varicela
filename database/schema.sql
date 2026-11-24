/* ==========================================================================
   Esquema relacional de Triaje Varicela para SQLite 3.
   Almacena pacientes, consultas, respuestas y resultados del triaje,
   mensajes del chat, análisis de imagen, catálogo médico y derivaciones.
   ========================================================================== */

/* Activa la integridad referencial (SQLite la trae desactivada por conexión). */
PRAGMA foreign_keys = ON;

/* Usa el modo WAL para escrituras más seguras ante cierres inesperados. */
PRAGMA journal_mode = WAL;

/* --------------------------------------------------------------------------
   Control de versiones del esquema para futuras migraciones.
   -------------------------------------------------------------------------- */
CREATE TABLE IF NOT EXISTS esquema_version (
    version      INTEGER PRIMARY KEY,                           -- Número de versión del esquema.
    aplicada_en  TEXT    NOT NULL DEFAULT (datetime('now')),    -- Fecha de aplicación en UTC.
    descripcion  TEXT    NOT NULL                               -- Resumen del cambio.
);

/* --------------------------------------------------------------------------
   Perfil del paciente (puede ser anónimo: solo se guarda un alias).
   Los factores de riesgo alimentan la ponderación estadística en R.
   -------------------------------------------------------------------------- */
CREATE TABLE IF NOT EXISTS pacientes (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    alias                   TEXT    NOT NULL,                                    -- Nombre o alias elegido por el usuario.
    fecha_nacimiento        TEXT,                                                -- Formato ISO AAAA-MM-DD.
    sexo                    TEXT    CHECK (sexo IN ('F', 'M', 'X')),             -- Femenino, masculino u otro.
    embarazo                INTEGER NOT NULL DEFAULT 0 CHECK (embarazo IN (0, 1)),          -- Factor de riesgo.
    inmunocompromiso        INTEGER NOT NULL DEFAULT 0 CHECK (inmunocompromiso IN (0, 1)),  -- Factor de riesgo.
    vacunado_varicela       INTEGER          CHECK (vacunado_varicela IN (0, 1)),           -- NULL indica que no sabe.
    antecedente_varicela    INTEGER          CHECK (antecedente_varicela IN (0, 1)),        -- NULL indica que no sabe.
    creado_en               TEXT    NOT NULL DEFAULT (datetime('now'))
);

/* --------------------------------------------------------------------------
   Consulta: agrupa todo lo ocurrido en una sesión de uso de la aplicación.
   -------------------------------------------------------------------------- */
CREATE TABLE IF NOT EXISTS consultas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente_id     INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    iniciada_en     TEXT    NOT NULL DEFAULT (datetime('now')),
    finalizada_en   TEXT,
    estado          TEXT    NOT NULL DEFAULT 'ABIERTA'
                    CHECK (estado IN ('ABIERTA', 'FINALIZADA', 'DERIVADA')),     -- DERIVADA indica envío a médico.
    contacto_previo INTEGER CHECK (contacto_previo IN (0, 1)),                   -- Contacto con un caso en 10-21 días.
    notas           TEXT
);

CREATE INDEX IF NOT EXISTS idx_consultas_paciente ON consultas(paciente_id);

/* --------------------------------------------------------------------------
   Catálogo de síntomas compartido por Prolog, R y la interfaz.
   El campo codigo es la clave común entre los tres lenguajes.
   -------------------------------------------------------------------------- */
CREATE TABLE IF NOT EXISTS catalogo_sintomas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo      TEXT    NOT NULL UNIQUE,                                         -- Identificador usado en Prolog y R.
    nombre      TEXT    NOT NULL,                                                -- Texto mostrado al usuario.
    descripcion TEXT,
    tipo        TEXT    NOT NULL CHECK (tipo IN ('PRIMARIO', 'SECUNDARIO', 'ALARMA')),
    orden       INTEGER NOT NULL DEFAULT 0                                       -- Orden en el cuestionario.
);

/* --------------------------------------------------------------------------
   Respuestas del cuestionario de triaje, una fila por síntoma preguntado.
   -------------------------------------------------------------------------- */
CREATE TABLE IF NOT EXISTS respuestas_triaje (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    consulta_id     INTEGER NOT NULL REFERENCES consultas(id) ON DELETE CASCADE,
    sintoma_id      INTEGER NOT NULL REFERENCES catalogo_sintomas(id),
    presente        INTEGER CHECK (presente IN (0, 1)),                          -- NULL indica respuesta "no sé".
    intensidad      INTEGER CHECK (intensidad BETWEEN 0 AND 10),                 -- Escala subjetiva opcional.
    dias_evolucion  INTEGER CHECK (dias_evolucion >= 0),
    valor_numerico  REAL,                                                        -- Por ejemplo, temperatura en °C.
    UNIQUE (consulta_id, sintoma_id)
);

/* --------------------------------------------------------------------------
   Resultado combinado del triaje (dictamen lógico de Prolog y probabilidad de R).
   -------------------------------------------------------------------------- */
CREATE TABLE IF NOT EXISTS resultados_triaje (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    consulta_id         INTEGER NOT NULL REFERENCES consultas(id) ON DELETE CASCADE,
    dictamen_prolog     TEXT    NOT NULL,                                        -- Conclusión de las reglas lógicas.
    reglas_activadas    TEXT,                                                    -- Lista JSON de reglas que se cumplieron.
    probabilidad_r      REAL    CHECK (probabilidad_r BETWEEN 0 AND 1),          -- Probabilidad estimada por R.
    ic_inferior         REAL    CHECK (ic_inferior BETWEEN 0 AND 1),             -- Intervalo de confianza inferior.
    ic_superior         REAL    CHECK (ic_superior BETWEEN 0 AND 1),             -- Intervalo de confianza superior.
    riesgo_ponderado    TEXT    CHECK (riesgo_ponderado IN ('BAJO', 'MODERADO', 'ALTO')),
    banderas_alarma     TEXT,                                                    -- Lista JSON de signos de alarma.
    dictamen_final      TEXT    NOT NULL
                        CHECK (dictamen_final IN ('NEGATIVO_BAJO_RIESGO', 'SOSPECHA_INICIAL',
                                                  'ALTA_PROBABILIDAD', 'DERIVAR_MEDICO')),
    version_motor       TEXT    NOT NULL,                                        -- Versión de reglas y modelo usados.
    creado_en           TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_resultados_consulta ON resultados_triaje(consulta_id);

/* --------------------------------------------------------------------------
   Registro del chat con el asistente médico virtual.
   -------------------------------------------------------------------------- */
CREATE TABLE IF NOT EXISTS mensajes_chat (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    consulta_id         INTEGER NOT NULL REFERENCES consultas(id) ON DELETE CASCADE,
    rol                 TEXT    NOT NULL CHECK (rol IN ('usuario', 'asistente', 'sistema')),
    contenido           TEXT    NOT NULL,
    umbral_duda         INTEGER NOT NULL DEFAULT 0 CHECK (umbral_duda IN (0, 1)), -- 1 si se detuvo la inferencia y se derivó.
    modelo_llm          TEXT,                                                    -- Modelo que generó la respuesta.
    creado_en           TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_chat_consulta ON mensajes_chat(consulta_id, creado_en);

/* --------------------------------------------------------------------------
   Análisis de imágenes de la erupción cutánea.
   Se guarda la ruta local y su hash, nunca la imagen dentro de la base.
   -------------------------------------------------------------------------- */
CREATE TABLE IF NOT EXISTS analisis_imagen (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    consulta_id     INTEGER NOT NULL REFERENCES consultas(id) ON DELETE CASCADE,
    ruta_imagen     TEXT    NOT NULL,
    sha256          TEXT    NOT NULL,                                            -- Evita analizar dos veces la misma imagen.
    modelo          TEXT    NOT NULL,
    version_modelo  TEXT    NOT NULL,
    clase_predicha  TEXT    NOT NULL,                                            -- Por ejemplo varicela, sarampion, otra.
    confianza       REAL    NOT NULL CHECK (confianza BETWEEN 0 AND 1),          -- Probabilidad calibrada.
    umbral_usado    REAL    NOT NULL CHECK (umbral_usado BETWEEN 0 AND 1),
    decision        TEXT    NOT NULL CHECK (decision IN ('COMPATIBLE', 'NO_COMPATIBLE', 'INDETERMINADO')),
    creado_en       TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_imagen_consulta ON analisis_imagen(consulta_id);

/* --------------------------------------------------------------------------
   Catálogo del Centro Informativo con su fuente y fecha de revisión.
   -------------------------------------------------------------------------- */
CREATE TABLE IF NOT EXISTS catalogo_informacion (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    seccion         TEXT    NOT NULL CHECK (seccion IN ('QUE_ES', 'CUIDADOS', 'AISLAMIENTO', 'MITOS')),
    titulo          TEXT    NOT NULL,
    contenido_md    TEXT    NOT NULL,                                            -- Texto en formato Markdown.
    fuente          TEXT    NOT NULL,                                            -- Referencia verificable (OMS, CDC, etc.).
    fecha_revision  TEXT    NOT NULL,
    orden           INTEGER NOT NULL DEFAULT 0
);

/* --------------------------------------------------------------------------
   Centros de salud mostrados al usuario cuando hubo derivación.
   -------------------------------------------------------------------------- */
CREATE TABLE IF NOT EXISTS derivaciones (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    consulta_id     INTEGER NOT NULL REFERENCES consultas(id) ON DELETE CASCADE,
    origen          TEXT    NOT NULL CHECK (origen IN ('TRIAJE', 'CHAT', 'IMAGEN')),  -- Módulo que activó la derivación.
    nombre_centro   TEXT    NOT NULL,
    tipo_centro     TEXT,                                                        -- Hospital, clínica o consultorio.
    latitud         REAL    NOT NULL,
    longitud        REAL    NOT NULL,
    distancia_km    REAL,
    telefono        TEXT,
    fuente_datos    TEXT    NOT NULL DEFAULT 'OpenStreetMap',
    creado_en       TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_derivaciones_consulta ON derivaciones(consulta_id);

/* --------------------------------------------------------------------------
   Datos iniciales del catálogo de síntomas (códigos compartidos).
   INSERT OR IGNORE permite ejecutar el script varias veces sin duplicar.
   -------------------------------------------------------------------------- */
INSERT OR IGNORE INTO catalogo_sintomas (codigo, nombre, tipo, orden) VALUES
    ('fiebre_moderada',       'Fiebre moderada (37.8 a 39 °C)',                    'PRIMARIO',   1),
    ('malestar_general',      'Malestar general o cansancio',                      'SECUNDARIO', 2),
    ('perdida_apetito',       'Pérdida de apetito',                                'SECUNDARIO', 3),
    ('cefalea',               'Dolor de cabeza',                                   'SECUNDARIO', 4),
    ('maculas',               'Manchas rojas planas en la piel',                   'PRIMARIO',   5),
    ('papulas',               'Granitos elevados',                                 'PRIMARIO',   6),
    ('vesiculas',             'Ampollas pequeñas con líquido claro',               'PRIMARIO',   7),
    ('costras',               'Lesiones con costra',                               'PRIMARIO',   8),
    ('lesiones_simultaneas',  'Lesiones en distintas fases al mismo tiempo',       'PRIMARIO',   9),
    ('inicio_tronco',         'Erupción que comenzó en tronco, cara o cuero cabelludo', 'PRIMARIO', 10),
    ('prurito',               'Comezón intensa',                                   'PRIMARIO',  11),
    ('dificultad_respiratoria','Dificultad para respirar',                         'ALARMA',    12),
    ('fiebre_alta_persistente','Fiebre mayor de 39 °C por más de 3 días',          'ALARMA',    13),
    ('lesiones_infectadas',   'Lesiones con pus, calor o enrojecimiento creciente', 'ALARMA',   14),
    ('confusion_rigidez',     'Confusión, somnolencia extrema o rigidez de nuca',  'ALARMA',    15);

/* Registra la versión inicial del esquema. */
INSERT OR IGNORE INTO esquema_version (version, descripcion)
VALUES (1, 'Esquema inicial de la Fase 1.');
