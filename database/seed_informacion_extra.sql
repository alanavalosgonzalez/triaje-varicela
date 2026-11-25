/* ==========================================================================
   Contenido adicional del Centro Informativo (versión 2): realidades para el juego
   "¿Mito o realidad?". Se aplica en cada inicio, también sobre bases ya existentes:
   cada fila solo se inserta si no hay otra con el mismo título, así que nunca se duplica.
   Igual que el resto del contenido, debe revisarlo un profesional de la salud.
   ========================================================================== */

/* Realidad 1: el contagio empieza antes de la erupción. */
INSERT INTO catalogo_informacion (seccion, titulo, contenido_md, fuente, fecha_revision, orden)
SELECT 'MITOS', 'Realidad: "La varicela se contagia antes de que aparezcan las ronchas"',
       '**Realidad.** Una persona con varicela contagia desde **1 a 2 días antes** de que salga la erupción. Por eso se propaga con tanta facilidad en escuelas y guarderías.',
       'CDC: Chickenpox Transmission.', '2026-11-25', 8
WHERE NOT EXISTS (SELECT 1 FROM catalogo_informacion
                  WHERE titulo = 'Realidad: "La varicela se contagia antes de que aparezcan las ronchas"');

/* Realidad 2: la varicela en personas vacunadas. */
INSERT INTO catalogo_informacion (seccion, titulo, contenido_md, fuente, fecha_revision, orden)
SELECT 'MITOS', 'Realidad: "Una persona vacunada puede tener varicela, aunque suele ser más leve"',
       '**Realidad.** La vacuna protege mucho, pero no al cien por ciento. Si una persona vacunada se contagia, suele tener **pocas lesiones**, muchas veces sin ampollas y con poca o nula fiebre. Aun así puede contagiar.',
       'CDC: Chickenpox Vaccination (Breakthrough Varicella).', '2026-11-25', 9
WHERE NOT EXISTS (SELECT 1 FROM catalogo_informacion
                  WHERE titulo = 'Realidad: "Una persona vacunada puede tener varicela, aunque suele ser más leve"');

/* Realidad 3: rascarse tiene consecuencias. */
INSERT INTO catalogo_informacion (seccion, titulo, contenido_md, fuente, fecha_revision, orden)
SELECT 'MITOS', 'Realidad: "Rascarse puede dejar cicatrices e infectar las lesiones"',
       '**Realidad.** Rascar las ampollas puede introducir bacterias de la piel y provocar una **infección** y **cicatrices**. Ayudan las uñas cortas, los baños tibios y la loción de calamina.',
       'AAP HealthyChildren: Chickenpox.', '2026-11-25', 10
WHERE NOT EXISTS (SELECT 1 FROM catalogo_informacion
                  WHERE titulo = 'Realidad: "Rascarse puede dejar cicatrices e infectar las lesiones"');
