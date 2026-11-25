/* ==========================================================================
   Base de conocimientos y reglas de inferencia para el triaje de varicela.
   Punto de entrada: evaluar/5.
   Las respuestas llegan como una lista de términos s(Codigo, Valor), donde
   Valor es si, no o desconoce, y Codigo coincide con catalogo_sintomas.codigo.
   Además se acepta s(contacto_previo, Valor), que proviene de consultas.contacto_previo.
   Las reglas son puras (no usan assert), así que cada consulta es independiente.
   ========================================================================== */

:- module(varicela, [evaluar/5, version_reglas/1]).

/* Versión de la base de reglas; se guarda en resultados_triaje.version_motor. */
version_reglas('reglas-1.0.0').

/* --------------------------------------------------------------------------
   HECHOS: catálogo de síntomas y su clasificación clínica.
   sintoma(Codigo, Tipo) con Tipo en primario, secundario o alarma.
   -------------------------------------------------------------------------- */
sintoma(fiebre_moderada,          primario).
sintoma(malestar_general,         secundario).
sintoma(perdida_apetito,          secundario).
sintoma(cefalea,                  secundario).
sintoma(maculas,                  primario).
sintoma(papulas,                  primario).
sintoma(vesiculas,                primario).
sintoma(costras,                  primario).
sintoma(lesiones_simultaneas,     primario).
sintoma(inicio_tronco,            primario).
sintoma(prurito,                  primario).
sintoma(dificultad_respiratoria,  alarma).
sintoma(fiebre_alta_persistente,  alarma).
sintoma(lesiones_infectadas,      alarma).
sintoma(confusion_rigidez,        alarma).

/* Lesiones cutáneas propias de la erupción de varicela. */
lesion(maculas).
lesion(papulas).
lesion(vesiculas).
lesion(costras).

/* Síntomas del pródromo (fase previa a la erupción). */
prodromo(fiebre_moderada).
prodromo(malestar_general).
prodromo(perdida_apetito).
prodromo(cefalea).

/* --------------------------------------------------------------------------
   PREDICADOS AUXILIARES sobre la lista de respuestas.
   -------------------------------------------------------------------------- */

/* tiene(+Respuestas, ?Codigo) se cumple si el paciente afirmó el síntoma. */
tiene(Respuestas, Codigo) :-
    member(s(Codigo, si), Respuestas).

/* desconoce(+Respuestas, ?Codigo) se cumple si el paciente respondió "no sé". */
desconoce(Respuestas, Codigo) :-
    member(s(Codigo, desconoce), Respuestas).

/* alguna_lesion(+Respuestas) se cumple si hay al menos una lesión cutánea. */
alguna_lesion(R) :-
    lesion(L), tiene(R, L), !.

/* algun_prodromo(+Respuestas) se cumple si hay algún síntoma prodrómico. */
algun_prodromo(R) :-
    prodromo(P), tiene(R, P), !.

/* signos_alarma(+Respuestas, -Lista) devuelve los signos de alarma presentes. */
signos_alarma(R, Lista) :-
    findall(S, (sintoma(S, alarma), tiene(R, S)), Lista).

/* primarios_desconocidos(+Respuestas, -N) cuenta síntomas primarios sin respuesta clara. */
primarios_desconocidos(R, N) :-
    findall(S, (sintoma(S, primario), desconoce(R, S)), L),
    length(L, N).

/* --------------------------------------------------------------------------
   REGLAS DE FASE: estiman en qué etapa de la enfermedad está el cuadro.
   El orden importa: se elige la fase más avanzada que se cumpla.
   -------------------------------------------------------------------------- */

/* Fase de costras: todas las lesiones visibles ya están en costra. */
fase(R, costras) :-
    tiene(R, costras),
    \+ tiene(R, vesiculas), !.

/* Fase vesicular: hay vesículas (ampollas con líquido). */
fase(R, vesicular) :-
    tiene(R, vesiculas), !.

/* Fase eruptiva temprana: manchas o granitos sin vesículas todavía. */
fase(R, eruptiva_temprana) :-
    ( tiene(R, maculas) ; tiene(R, papulas) ), !.

/* Fase prodrómica: síntomas generales sin erupción. */
fase(R, prodromica) :-
    algun_prodromo(R),
    \+ alguna_lesion(R), !.

/* Sin datos suficientes para ubicar una fase. */
fase(_, indeterminada).

/* --------------------------------------------------------------------------
   REGLAS DE DIAGNÓSTICO DIFERENCIAL: otras causas que conviene descartar.
   Se devuelven como sugerencias, nunca como diagnóstico.
   -------------------------------------------------------------------------- */

/* Exantema sin vesículas ni comezón con fiebre: considerar sarampión o rubéola. */
diferencial(R, sarampion_rubeola) :-
    ( tiene(R, maculas) ; tiene(R, papulas) ),
    \+ tiene(R, vesiculas),
    \+ tiene(R, prurito),
    tiene(R, fiebre_moderada).

/* Granitos con comezón, sin fiebre ni pródromo: considerar picaduras o alergia. */
diferencial(R, picaduras_alergia) :-
    tiene(R, papulas),
    tiene(R, prurito),
    \+ algun_prodromo(R),
    \+ tiene(R, lesiones_simultaneas).

/* Lesiones infectadas con costras: considerar impétigo o sobreinfección bacteriana. */
diferencial(R, impetigo_sobreinfeccion) :-
    tiene(R, lesiones_infectadas),
    tiene(R, costras).

/* Vesículas sin lesiones en distintas fases: considerar herpes zóster u otros virus. */
diferencial(R, otras_vesiculares) :-
    tiene(R, vesiculas),
    \+ tiene(R, lesiones_simultaneas),
    \+ tiene(R, inicio_tronco).

/* --------------------------------------------------------------------------
   REGLAS DE DICTAMEN. Se evalúan en orden de gravedad y la primera que se
   cumple decide. Cada una devuelve también las razones que la activaron.
   -------------------------------------------------------------------------- */

/* Regla de seguridad 1: cualquier signo de alarma obliga a derivar al médico. */
dictamen(R, derivar_medico, [signos_alarma(Signos)]) :-
    signos_alarma(R, Signos),
    Signos \== [], !.

/* Regla de seguridad 2 (umbral de duda): demasiadas respuestas "no sé" en síntomas clave. */
dictamen(R, derivar_medico, [datos_ambiguos(N)]) :-
    primarios_desconocidos(R, N),
    N >= 3, !.

/* Alta probabilidad: vesículas con patrón típico (lesiones simultáneas o inicio en tronco)
   y al menos un acompañante (comezón, fiebre o contacto previo). */
dictamen(R, alta_probabilidad, [vesiculas, Patron, Acompanante]) :-
    tiene(R, vesiculas),
    ( tiene(R, lesiones_simultaneas) -> Patron = lesiones_simultaneas
    ; tiene(R, inicio_tronco)        -> Patron = inicio_tronco
    ),
    ( tiene(R, prurito)         -> Acompanante = prurito
    ; tiene(R, fiebre_moderada) -> Acompanante = fiebre_moderada
    ; tiene(R, contacto_previo) -> Acompanante = contacto_previo
    ), !.

/* Sospecha inicial A: hay erupción acompañada de fiebre, comezón o contacto previo. */
dictamen(R, sospecha_inicial, [erupcion, Motivo]) :-
    alguna_lesion(R),
    ( tiene(R, fiebre_moderada) -> Motivo = fiebre_moderada
    ; tiene(R, prurito)         -> Motivo = prurito
    ; tiene(R, contacto_previo) -> Motivo = contacto_previo
    ), !.

/* Sospecha inicial B: pródromo sin erupción, pero con contacto previo con un caso. */
dictamen(R, sospecha_inicial, [prodromo, contacto_previo]) :-
    algun_prodromo(R),
    tiene(R, contacto_previo), !.

/* Caso por defecto: no se cumple ningún patrón compatible. */
dictamen(_, negativo_bajo_riesgo, [sin_patron_compatible]).

/* --------------------------------------------------------------------------
   PUNTO DE ENTRADA para Python.
   evaluar(+Respuestas, -Dictamen, -Razones, -Fase, -Diferenciales).
   -------------------------------------------------------------------------- */
evaluar(Respuestas, Dictamen, Razones, Fase, Diferenciales) :-
    dictamen(Respuestas, Dictamen, Razones),
    fase(Respuestas, Fase),
    findall(D, diferencial(Respuestas, D), Diferenciales).
