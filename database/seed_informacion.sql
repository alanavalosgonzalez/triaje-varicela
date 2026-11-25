/* ==========================================================================
   Contenido del Centro Informativo (tabla catalogo_informacion).
   Redactado a partir de las guías públicas de la OMS, los CDC de EE. UU. y la
   Academia Americana de Pediatría. Debe revisarlo un profesional de la salud
   antes de publicar la aplicación y actualizarse cuando cambien las guías.
   Se carga solo si la tabla está vacía (ver app/db/repositorio.py).
   ========================================================================== */

/* --------------------------------------------------------------------------
   Sección QUE_ES: qué es la varicela, cómo evoluciona y a quién afecta más.
   -------------------------------------------------------------------------- */
INSERT INTO catalogo_informacion (seccion, titulo, contenido_md, fuente, fecha_revision, orden) VALUES
('QUE_ES', '¿Qué es la varicela?',
'La varicela es una infección **muy contagiosa** causada por el **virus varicela-zóster**. Se transmite por el aire (al toser, estornudar o respirar cerca) y por contacto con el líquido de las ampollas.

- Es más frecuente en **niños**, pero puede afectar a cualquier persona que no la haya tenido ni esté vacunada.
- En la mayoría de los niños sanos es **leve** y se cura sola en 1 a 2 semanas.
- Después de la infección, el virus queda "dormido" en el cuerpo y años más tarde puede reactivarse como **herpes zóster** (culebrilla).',
'OMS: Varicella and herpes zoster vaccines, WHO position paper (2014); CDC: About Chickenpox.', '2026-11-24', 1),

('QUE_ES', 'Fases de la enfermedad',
'1. **Incubación (10 a 21 días):** después del contagio no hay síntomas, aunque el virus ya se está multiplicando.
2. **Pródromo (1 a 2 días):** fiebre moderada, cansancio, falta de apetito y dolor de cabeza. En niños pequeños a veces la erupción es la primera señal.
3. **Erupción:** aparecen **manchas rojas** que en horas se convierten en **granitos** y luego en **ampollas pequeñas con líquido claro** que dan **mucha comezón**. Suelen empezar en el **pecho, la espalda, la cara o el cuero cabelludo** y después se extienden.
4. **Costras:** las ampollas se secan y forman costras en unos días.

Lo más característico es que **conviven lesiones en distintas fases al mismo tiempo** (manchas, granitos, ampollas y costras), porque salen por "brotes" durante 3 a 5 días.',
'CDC: Chickenpox Signs and Symptoms; AAP HealthyChildren: Chickenpox.', '2026-11-24', 2),

('QUE_ES', '¿Quién tiene más riesgo de complicaciones?',
'Aunque suele ser leve, la varicela puede complicarse, sobre todo en:

- **Bebés menores de 1 año.**
- **Adolescentes y adultos.**
- **Mujeres embarazadas** (riesgo para la madre y el bebé).
- Personas con **defensas bajas**: cáncer, VIH, trasplantes o tratamientos con corticoides u otros inmunosupresores.

Las complicaciones posibles incluyen infección bacteriana de la piel, neumonía, deshidratación e inflamación del cerebro (encefalitis). Si perteneces a alguno de estos grupos y sospechas varicela, **consulta al médico cuanto antes**: puede indicar un tratamiento antiviral que funciona mejor en las primeras 24 horas.',
'CDC: Chickenpox Complications; CDC: People at High Risk for Complications.', '2026-11-24', 3),

('QUE_ES', 'Prevención: la vacuna',
'La forma más eficaz de prevenir la varicela es la **vacuna**. Se aplican **dos dosis**, según el esquema de vacunación de cada país.

- Las personas vacunadas que aun así se contagian suelen tener un cuadro **mucho más leve**, con menos lesiones y poca o nula fiebre.
- Si una persona sin vacunar tuvo contacto con un caso, la vacuna aplicada en los **3 a 5 días** siguientes puede prevenir o suavizar la enfermedad. Consulta a tu médico.',
'OMS: Varicella position paper (2014); CDC: Chickenpox Vaccination.', '2026-11-24', 4);

/* --------------------------------------------------------------------------
   Sección CUIDADOS: protocolo en casa para cuadros leves.
   -------------------------------------------------------------------------- */
INSERT INTO catalogo_informacion (seccion, titulo, contenido_md, fuente, fecha_revision, orden) VALUES
('CUIDADOS', 'Para la fiebre y el malestar',
'- Usa **paracetamol** (acetaminofén) según la dosis que indique el médico o el empaque para la edad y el peso.
- **Nunca uses aspirina** (ácido acetilsalicílico) en niños ni adolescentes: se asocia al **síndrome de Reye**, que daña el hígado y el cerebro.
- **Evita el ibuprofeno** y otros antiinflamatorios durante la varicela salvo indicación médica: se han asociado a infecciones graves de la piel.
- Ofrece **líquidos con frecuencia** (agua, suero oral, caldos) para evitar la deshidratación.',
'CDC: Chickenpox Treatment; AAP HealthyChildren: Chickenpox.', '2026-11-24', 1),

('CUIDADOS', 'Para la comezón y la piel',
'- **Baños** cortos con agua tibia o fresca; puedes añadir avena coloidal. Seca **sin frotar**, dando toquecitos con una toalla limpia.
- **Loción de calamina** sobre las lesiones que pican (no en la cara cerca de los ojos ni en ampollas abiertas).
- **Uñas cortas y limpias**; en niños pequeños, guantes o calcetines en las manos por la noche para no rascarse.
- **Ropa holgada de algodón** y un ambiente fresco: el calor y el sudor aumentan la comezón.
- Los antihistamínicos para la comezón solo deben usarse **si el médico los indica**.',
'CDC: Chickenpox Treatment; AAP HealthyChildren: Chickenpox.', '2026-11-24', 2),

('CUIDADOS', 'Cuándo acudir al médico de inmediato',
'Busca atención médica **urgente** si aparece cualquiera de estos signos:

- **Dificultad para respirar**, respiración rápida o dolor de pecho.
- **Fiebre de 39.5 °C o más**, o fiebre que dura **más de 3 días**.
- Lesiones con **pus**, muy rojas, calientes, hinchadas o dolorosas.
- Lesiones **en los ojos o cerca de ellos**.
- **Confusión**, somnolencia extrema, convulsiones, rigidez de nuca o dificultad para caminar.
- Vómito persistente o signos de deshidratación (orina escasa, boca seca).
- Sangrado o manchas moradas en la piel.',
'CDC: Chickenpox Complications; AAP HealthyChildren: When to Call the Pediatrician.', '2026-11-24', 3);

/* --------------------------------------------------------------------------
   Sección AISLAMIENTO: cómo evitar el contagio a otras personas.
   -------------------------------------------------------------------------- */
INSERT INTO catalogo_informacion (seccion, titulo, contenido_md, fuente, fecha_revision, orden) VALUES
('AISLAMIENTO', '¿Cuándo se contagia?',
'Una persona con varicela contagia **desde 1 a 2 días antes** de que salga la erupción **hasta que todas las lesiones son costras**, lo que suele tardar unos **5 a 7 días**.

En personas vacunadas que solo presentan granitos sin ampollas, el periodo termina cuando **pasan 24 horas sin que aparezcan lesiones nuevas**.',
'CDC: Chickenpox Transmission.', '2026-11-24', 1),

('AISLAMIENTO', 'Medidas en casa',
'- **No asistir a la escuela, guardería ni trabajo** hasta que todas las lesiones sean costras.
- Mantener a la persona en una **habitación ventilada** y limitar las visitas.
- **Lavado de manos** frecuente con agua y jabón, sobre todo después de tocar las lesiones.
- **No compartir** toallas, ropa, sábanas ni cubiertos; lavar la ropa de cama con agua caliente.
- Cubrir boca y nariz al toser o estornudar.',
'CDC: Chickenpox Prevention; OMS: Varicella.', '2026-11-24', 2),

('AISLAMIENTO', 'Protege a las personas de riesgo',
'Evita por completo el contacto con:

- **Mujeres embarazadas** que no hayan tenido varicela ni estén vacunadas.
- **Recién nacidos** y bebés pequeños.
- Personas con **defensas bajas**.

Si alguna de ellas tuvo contacto con el enfermo, debe **consultar a su médico lo antes posible**: existen medidas preventivas que solo funcionan en los primeros días tras el contacto.',
'CDC: Chickenpox Prevention and Post-exposure Management.', '2026-11-24', 3);

/* --------------------------------------------------------------------------
   Sección MITOS: creencias frecuentes contrastadas con la evidencia.
   -------------------------------------------------------------------------- */
INSERT INTO catalogo_informacion (seccion, titulo, contenido_md, fuente, fecha_revision, orden) VALUES
('MITOS', 'Mito: "La aspirina es buena para bajar la fiebre de la varicela"',
'**Falso y peligroso.** En niños y adolescentes con varicela la aspirina puede provocar el **síndrome de Reye**, una enfermedad grave del hígado y el cerebro. Usa paracetamol.',
'CDC: Reye syndrome and aspirin; AAP HealthyChildren.', '2026-11-24', 1),

('MITOS', 'Mito: "Hay que poner pasta de dientes, harina, café, alcohol o cloro en las ronchas"',
'**Falso.** Estos remedios **irritan la piel**, pueden **quemarla** y favorecen las **infecciones**, además de dificultar que el médico valore las lesiones. Lo recomendado es baño tibio, calamina y uñas cortas.',
'AAP HealthyChildren: Chickenpox.', '2026-11-24', 2),

('MITOS', 'Mito: "Con varicela no hay que bañarse"',
'**Falso.** El baño diario con agua tibia **limpia la piel, reduce la comezón y previene infecciones**. Solo hay que secar sin frotar.',
'CDC: Chickenpox Treatment.', '2026-11-24', 3),

('MITOS', 'Mito: "Conviene contagiar a los niños a propósito para que les dé de chicos"',
'**Falso.** Las "fiestas de varicela" exponen a los niños a **complicaciones graves** e incluso a la muerte, y además ponen en riesgo a embarazadas y personas con defensas bajas. La **vacuna** protege sin esos riesgos.',
'CDC: Chickenpox Vaccination; OMS: Varicella position paper.', '2026-11-24', 4),

('MITOS', 'Mito: "La varicela siempre es una enfermedad leve"',
'**Falso.** Es leve en la mayoría de los niños sanos, pero en **bebés, adolescentes, adultos, embarazadas y personas con defensas bajas** puede causar neumonía, encefalitis o infecciones graves de la piel.',
'CDC: Chickenpox Complications.', '2026-11-24', 5),

('MITOS', 'Mito: "Si ya tuve varicela, el virus desapareció para siempre"',
'**Parcialmente falso.** Haberla tenido suele dar protección de por vida contra la varicela, pero el virus **queda latente** y puede reactivarse años después como **herpes zóster** (culebrilla). Existe una vacuna específica contra el zóster para adultos.',
'CDC: About Shingles.', '2026-11-24', 6),

('MITOS', 'Mito: "Hay que abrigar mucho al enfermo para que salgan todas las ronchas"',
'**Falso.** Abrigar en exceso **sube la temperatura y aumenta la comezón**. La erupción sigue su curso natural; lo adecuado es ropa ligera y un ambiente fresco.',
'AAP HealthyChildren: Chickenpox.', '2026-11-24', 7);
