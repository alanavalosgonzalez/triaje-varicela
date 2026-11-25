/* ==========================================================================
   Pruebas unitarias de las reglas de varicela con plunit.
   Ejecutar: swipl -g run_tests -t halt prolog/test_varicela.pl
   ========================================================================== */

:- use_module(varicela).
:- use_module(library(plunit)).

:- begin_tests(dictamen).

/* Un cuadro típico con vesículas, lesiones simultáneas y comezón da alta probabilidad. */
test(caso_tipico) :-
    evaluar([s(vesiculas, si), s(lesiones_simultaneas, si), s(prurito, si),
             s(fiebre_moderada, si)], D, _, F, _),
    D == alta_probabilidad,
    F == vesicular.

/* Un signo de alarma gana sobre cualquier otro patrón. */
test(alarma_prioritaria) :-
    evaluar([s(vesiculas, si), s(lesiones_simultaneas, si), s(prurito, si),
             s(dificultad_respiratoria, si)], D, R, _, _),
    D == derivar_medico,
    R == [signos_alarma([dificultad_respiratoria])].

/* Tres o más síntomas clave respondidos con "no sé" activan el umbral de duda. */
test(umbral_duda) :-
    evaluar([s(vesiculas, desconoce), s(papulas, desconoce), s(prurito, desconoce)],
            D, R, _, _),
    D == derivar_medico,
    R == [datos_ambiguos(3)].

/* Erupción con fiebre pero sin vesículas queda como sospecha inicial. */
test(sospecha_erupcion) :-
    evaluar([s(maculas, si), s(fiebre_moderada, si)], D, _, F, Dif),
    D == sospecha_inicial,
    F == eruptiva_temprana,
    memberchk(sarampion_rubeola, Dif).

/* Pródromo más contacto previo con un caso es sospecha inicial aunque no haya erupción. */
test(prodromo_con_contacto) :-
    evaluar([s(fiebre_moderada, si), s(malestar_general, si), s(contacto_previo, si)],
            D, _, F, _),
    D == sospecha_inicial,
    F == prodromica.

/* Sin síntomas compatibles el dictamen es negativo. */
test(negativo) :-
    evaluar([s(cefalea, si), s(vesiculas, no)], D, _, _, _),
    D == negativo_bajo_riesgo.

:- end_tests(dictamen).
