# ==========================================================================
# Motor estadístico de Triaje Varicela.
# Calcula la probabilidad de varicela con un modelo logístico, su intervalo
# de confianza por simulación Monte Carlo, un índice de coherencia de los
# síntomas con el perfil típico y el riesgo de complicaciones por edad e historial.
#
# Uso: Rscript probabilidad.R clave=valor clave=valor ...
#   Síntomas y antecedentes: 1 (sí), 0 (no) o NA (no sabe).
#   edad: años cumplidos; embarazo, inmunocompromiso: 0 o 1.
# Salida: una sola línea JSON por la salida estándar.
# No usa paquetes externos para que funcione con una instalación limpia de R.
# ==========================================================================

VERSION_MODELO <- "logit-1.0.0"

# Coeficientes del modelo en escala log-odds y su error estándar.
# Son valores iniciales de referencia basados en la presentación clínica típica.
# Deben recalibrarse con datos reales antes de cualquier uso clínico.
COEFICIENTES <- data.frame(
  variable = c("intercepto", "contacto_previo", "vesiculas", "lesiones_simultaneas",
               "inicio_tronco", "prurito", "papulas", "maculas", "costras",
               "fiebre_moderada", "malestar_general", "perdida_apetito", "cefalea",
               "vacunado_varicela", "antecedente_varicela"),
  beta = c(-3.0, 1.5, 1.8, 1.6, 0.9, 0.8, 0.5, 0.4, 0.6, 0.6, 0.3, 0.2, 0.1, -1.2, -2.5),
  ee   = c( 0.4, 0.3, 0.3, 0.3, 0.3, 0.2, 0.2, 0.2, 0.2, 0.2, 0.15, 0.15, 0.1, 0.3, 0.4),
  stringsAsFactors = FALSE
)

# Perfil típico de varicela (1 = síntoma esperado) para el índice de coherencia.
PERFIL_TIPICO <- c(fiebre_moderada = 1, malestar_general = 1, perdida_apetito = 1,
                   cefalea = 0, maculas = 1, papulas = 1, vesiculas = 1, costras = 1,
                   lesiones_simultaneas = 1, inicio_tronco = 1, prurito = 1)

# Signos de alarma que elevan el riesgo a ALTO sin importar la probabilidad.
SIGNOS_ALARMA <- c("dificultad_respiratoria", "fiebre_alta_persistente",
                   "lesiones_infectadas", "confusion_rigidez")

# Convierte los argumentos clave=valor en una lista con valores numéricos o NA.
leer_argumentos <- function(args) {
  datos <- list()
  for (arg in args) {
    partes <- strsplit(arg, "=", fixed = TRUE)[[1]]
    if (length(partes) != 2) stop(paste("Argumento inválido:", arg))
    valor <- if (toupper(partes[2]) == "NA") NA_real_ else as.numeric(partes[2])
    datos[[partes[1]]] <- valor
  }
  datos
}

# Devuelve el valor de una variable o NA si no se envió.
obtener <- function(datos, nombre) {
  if (is.null(datos[[nombre]])) NA_real_ else datos[[nombre]]
}

# Calcula el predictor lineal; los valores NA aportan 0 (sin evidencia en ningún sentido).
predictor_lineal <- function(datos, betas) {
  x <- sapply(COEFICIENTES$variable[-1], function(v) obtener(datos, v))
  x[is.na(x)] <- 0
  betas[1] + sum(betas[-1] * x)
}

# Estima la probabilidad puntual y un intervalo de confianza del 95 % simulando
# la incertidumbre de los coeficientes; más respuestas NA ensanchan el intervalo.
calcular_probabilidad <- function(datos, n_sim = 5000, semilla = 42) {
  set.seed(semilla)
  p_puntual <- plogis(predictor_lineal(datos, COEFICIENTES$beta))
  # Solo cuentan las respuestas "no sé" explícitas; un síntoma no enviado no es duda.
  enviados <- intersect(names(datos), names(PERFIL_TIPICO))
  n_desconocidos <- sum(sapply(enviados, function(v) is.na(datos[[v]])))
  factor_ee <- 1 + 0.15 * n_desconocidos
  simulaciones <- replicate(n_sim, {
    betas <- rnorm(nrow(COEFICIENTES), COEFICIENTES$beta, COEFICIENTES$ee * factor_ee)
    plogis(predictor_lineal(datos, betas))
  })
  ic <- quantile(simulaciones, c(0.025, 0.975), names = FALSE)
  list(probabilidad = p_puntual, ic_inferior = ic[1], ic_superior = ic[2],
       n_desconocidos = n_desconocidos)
}

# Mide qué tanto se parece el cuadro al perfil típico (similitud coseno de 0 a 1).
indice_coherencia <- function(datos) {
  x <- sapply(names(PERFIL_TIPICO), function(v) obtener(datos, v))
  x[is.na(x)] <- 0
  if (sum(x) == 0) return(0)
  sum(x * PERFIL_TIPICO) / (sqrt(sum(x^2)) * sqrt(sum(PERFIL_TIPICO^2)))
}

# Pondera el riesgo de complicaciones según edad, embarazo, inmunidad y alarmas.
riesgo_ponderado <- function(datos) {
  alarmas <- SIGNOS_ALARMA[sapply(SIGNOS_ALARMA, function(s) isTRUE(obtener(datos, s) == 1))]
  edad <- obtener(datos, "edad")
  puntos <- 0
  if (!is.na(edad) && edad < 1) puntos <- puntos + 2                 # Lactantes.
  if (!is.na(edad) && edad >= 15) puntos <- puntos + 1               # Adolescentes y adultos.
  if (isTRUE(obtener(datos, "embarazo") == 1)) puntos <- puntos + 2
  if (isTRUE(obtener(datos, "inmunocompromiso") == 1)) puntos <- puntos + 3
  nivel <- if (length(alarmas) > 0 || puntos >= 3) "ALTO" else if (puntos >= 1) "MODERADO" else "BAJO"
  list(nivel = nivel, puntos = puntos, alarmas = alarmas)
}

# Clasifica la probabilidad en las tres categorías del triaje.
categoria <- function(p) {
  if (p >= 0.70) "ALTA_PROBABILIDAD" else if (p >= 0.30) "SOSPECHA_INICIAL" else "NEGATIVO_BAJO_RIESGO"
}

# Construye el JSON de salida sin depender de paquetes externos.
a_json <- function(prob, coherencia, riesgo) {
  alarmas_json <- if (length(riesgo$alarmas) == 0) "[]" else
    paste0("[", paste0('"', riesgo$alarmas, '"', collapse = ","), "]")
  sprintf(paste0('{"probabilidad":%.4f,"ic_inferior":%.4f,"ic_superior":%.4f,',
                 '"categoria":"%s","indice_coherencia":%.4f,"respuestas_desconocidas":%d,',
                 '"riesgo_ponderado":"%s","puntos_riesgo":%d,"banderas_alarma":%s,',
                 '"version_modelo":"%s"}'),
          prob$probabilidad, prob$ic_inferior, prob$ic_superior,
          categoria(prob$probabilidad), coherencia, as.integer(prob$n_desconocidos),
          riesgo$nivel, as.integer(riesgo$puntos), alarmas_json, VERSION_MODELO)
}

# Punto de entrada: solo se ejecuta al llamar el script con Rscript, no al cargarlo con source().
main <- function() {
  datos <- leer_argumentos(commandArgs(trailingOnly = TRUE))
  cat(a_json(calcular_probabilidad(datos), indice_coherencia(datos), riesgo_ponderado(datos)), "\n")
}

if (sys.nframe() == 0) main()
