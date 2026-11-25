/* ==========================================================================
   Interfaz de línea de comandos del motor Prolog, usada por Python.
   Uso: swipl prolog/cli.pl codigo=valor codigo=valor ...
   Valor es si, no o desconoce. Responde una línea JSON por la salida estándar.
   ========================================================================== */

:- use_module(varicela).
/* Librería JSON de SWI-Prolog 10 o superior. */
:- use_module(library(json)).

/* Ejecuta main/0 al cargar el archivo y termina el proceso al acabar. */
:- initialization(main, main).

/* Lee los argumentos, evalúa las reglas e imprime el resultado en JSON. */
main :-
    current_prolog_flag(argv, Argumentos),
    maplist(argumento_a_respuesta, Argumentos, Respuestas),
    evaluar(Respuestas, Dictamen, Razones, Fase, Diferenciales),
    version_reglas(Version),
    maplist(term_string, Razones, RazonesTexto),
    json_write_dict(current_output,
                    _{dictamen: Dictamen, razones: RazonesTexto, fase: Fase,
                      diferenciales: Diferenciales, version_reglas: Version},
                    [width(0)]),
    nl.

/* Convierte un argumento "codigo=valor" en el término s(codigo, valor). */
argumento_a_respuesta(Texto, s(Codigo, Valor)) :-
    split_string(Texto, "=", "", [CodigoTexto, ValorTexto]),
    atom_string(Codigo, CodigoTexto),
    atom_string(Valor, ValorTexto),
    must_be(oneof([si, no, desconoce]), Valor).
