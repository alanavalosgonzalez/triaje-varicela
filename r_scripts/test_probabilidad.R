# ==========================================================================
# Pruebas del motor estadístico.
# Ejecutar desde la raíz del proyecto: Rscript r_scripts/test_probabilidad.R
# ==========================================================================

source("r_scripts/probabilidad.R")

# Ejecuta una prueba, muestra su resultado y cuenta los fallos.
fallos <- 0
probar <- function(nombre, condicion) {
  if (isTRUE(condicion)) {
    cat("OK    ", nombre, "\n")
  } else {
    cat("FALLO ", nombre, "\n")
    fallos <<- fallos + 1
  }
}

# Un caso típico debe superar el umbral de alta probabilidad.
tipico <- list(vesiculas = 1, lesiones_simultaneas = 1, prurito = 1, fiebre_moderada = 1,
               inicio_tronco = 1, edad = 7)
p <- calcular_probabilidad(tipico)
probar("caso típico con alta probabilidad", categoria(p$probabilidad) == "ALTA_PROBABILIDAD")
probar("el intervalo contiene la probabilidad", p$ic_inferior <= p$probabilidad && p$probabilidad <= p$ic_superior)

# Solo síntomas generales deben dar bajo riesgo.
leve <- list(cefalea = 1, malestar_general = 1, vesiculas = 0, papulas = 0)
probar("solo síntomas generales da bajo riesgo",
       categoria(calcular_probabilidad(leve)$probabilidad) == "NEGATIVO_BAJO_RIESGO")

# El antecedente de varicela debe reducir la probabilidad.
con_antecedente <- modifyList(tipico, list(antecedente_varicela = 1))
probar("el antecedente reduce la probabilidad",
       calcular_probabilidad(con_antecedente)$probabilidad < p$probabilidad)

# Las respuestas "no sé" deben ensanchar el intervalo de confianza.
incierto <- modifyList(tipico, list(papulas = NA, maculas = NA, costras = NA, cefalea = NA))
pi <- calcular_probabilidad(incierto)
probar("las respuestas NA ensanchan el intervalo",
       (pi$ic_superior - pi$ic_inferior) > (p$ic_superior - p$ic_inferior))

# El inmunocompromiso o un signo de alarma elevan el riesgo a ALTO.
probar("inmunocompromiso da riesgo ALTO",
       riesgo_ponderado(list(inmunocompromiso = 1, edad = 30))$nivel == "ALTO")
probar("signo de alarma da riesgo ALTO",
       riesgo_ponderado(list(dificultad_respiratoria = 1, edad = 7))$nivel == "ALTO")
probar("niño sano da riesgo BAJO", riesgo_ponderado(list(edad = 7))$nivel == "BAJO")

# El índice de coherencia debe ser mayor en el caso típico que en el leve.
probar("coherencia mayor en caso típico", indice_coherencia(tipico) > indice_coherencia(leve))

cat("\nFallos:", fallos, "\n")
quit(status = if (fallos > 0) 1 else 0)
