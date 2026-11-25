# Módulo de visión artificial: método y resultados

## Datos

- **Dataset:** Mpox Skin Lesion Dataset v2.0 (MSLD v2.0), 755 fotos originales de 6 clases: varicela, sarampión, mpox, viruela bovina, enfermedad de mano-pie-boca y piel sana. Solo **75 fotos son de varicela**.
- Se usaron **solo las imágenes originales** (no las aumentadas que trae el dataset, que son copias de las mismas fotos).
- Se respetó la **división por paciente** de los autores (5 pliegues), para que las fotos de una misma persona nunca estén a la vez en entrenamiento y en prueba.

## Método

1. *Transfer learning:* red preentrenada en ImageNet con una capa final nueva de 6 clases.
2. Aumentos de datos (recortes, giros, rotación, brillo y tono) y pesos por clase para compensar el desbalance.
3. Se elige la época con mejor **exactitud balanceada** en validación.
4. **Calibración por temperatura** para que la confianza sea realista.
5. **Validación cruzada de 5 pliegues**: cada foto se evalúa con un modelo que nunca la vio (364 fotos de prueba en total).
6. Exportación a **ONNX**: la aplicación lo ejecuta solo con el procesador, sin PyTorch ni GPU.

## Comparación de arquitecturas (validación cruzada, 364 fotos de prueba)

| Arquitectura | Exactitud | Sensibilidad varicela | Especificidad varicela | Precisión varicela |
|---|---|---|---|---|
| EfficientNet-B0 (receta inicial) | 59.3 % | 67.3 % ± 10.3 | 88.3 % ± 1.7 | 43.3 % |
| EfficientNet-B0 (receta ajustada) | 51.4 % | 58.8 % ± 22.4 | 83.5 % ± 8.6 | 32.1 % |
| **ConvNeXt-Tiny (ImageNet-22k)** | **79.4 %** | 65.5 % ± 19.0 | **95.5 % ± 2.4** | **64.3 %** |
| ViT-Small (ImageNet-21k) | detenido tras 3 pliegues: sensibilidad de 33 % a 56 %, claramente inferior | | | |

**Modelo elegido:** ConvNeXt-Tiny (`convnext_tiny.fb_in22k_ft_in1k`).

## Umbral de confianza (ConvNeXt-Tiny)

La app solo afirma "compatible" o "no compatible" si la confianza calibrada supera el umbral; si no, responde **INDETERMINADO** y recomienda consultar a un médico.

| Umbral | Fotos indeterminadas | Sensibilidad* | Especificidad* |
|---|---|---|---|
| 0.50 | 12 % | 64 % | 96 % |
| **0.60 (elegido)** | **21 %** | **69 %** | **97 %** |
| 0.70 | 32 % | 75 % | 97 % |
| 0.80 | 44 % | 83 % | 98 % |
| 0.90 | 60 % | 95 % | 98 % |

\* Calculadas solo sobre las fotos en las que el modelo sí decide.

Primero se usó 0.70, pero en las pruebas de uso el modelo respondía "no concluyente" con demasiada frecuencia. Se bajó a **0.60** (versión 1.1 de los metadatos): el modelo decide en 4 de cada 5 fotos y la especificidad se mantiene en 97 %, a cambio de algo menos de sensibilidad (69 % frente a 75 %).

## Matriz de confusión combinada (filas = clase real, columnas = predicción)

| | mano-pie-boca | mpox | sana | sarampión | varicela | viruela bovina |
|---|---|---|---|---|---|---|
| **mano-pie-boca** | 74 | 2 | 1 | 5 | 0 | 0 |
| **mpox** | 4 | 86 | 7 | 5 | 14 | 9 |
| **sana** | 3 | 0 | 45 | 2 | 0 | 0 |
| **sarampión** | 0 | 2 | 0 | 28 | 0 | 0 |
| **varicela** | 0 | 10 | 0 | 1 | 27 | 4 |
| **viruela bovina** | 0 | 3 | 0 | 2 | 1 | 29 |

La confusión principal es **varicela ↔ mpox**, esperable porque ambas producen vesículas muy parecidas.

## Modelo final (versión 1.2)

- **v1.1:** entrenado con el pliegue 1 (537 fotos); en sus 74 fotos de prueba, nunca vistas: exactitud 73 %, sensibilidad para varicela 78 % y especificidad 95 %.
- **v1.2 (el publicado):** mismo método, pero se sumaron al entrenamiento las 74 fotos de prueba (611 en total), porque el rendimiento ya se había estimado con la validación cruzada. Por eso **su evaluación independiente es la validación cruzada**, no esas fotos.
- **Cuantizado a 8 bits** (`entrenamiento/cuantizar.py`): pasa de 111 MB a **28 MB** con las mismas predicciones. Tarda unos 140 ms por foto solo con el procesador.

Comparación con las 144 fotos de validación, que ninguno de los dos modelos usó para aprender (umbral 0.60):

| Modelo | No concluyente | Exactitud | Falsos positivos de varicela | Varicelas dichas "no compatible" |
|---|---|---|---|---|
| v1.1 | 35 % | 73 % | 9 | 0 de 16 |
| **v1.2** | **22 %** | **81 %** | **6** | 3 de 16 (2 como mpox, 1 como mano-pie-boca) |

### Regla de seguridad para otras enfermedades

Los errores de v1.2 confunden la varicela con **otras enfermedades** (mpox, mano-pie-boca), nunca con piel sana. Como esas enfermedades también requieren atención médica, la app aplica esta regla: **si la foto parece varicela o cualquier otra enfermedad, recomienda consultar a un médico y habilita el mapa**. Con ella, de las 16 varicelas de validación, 11 terminan con la recomendación de ir al médico, 5 son "no concluyentes" (que también aconsejan confirmar con un médico) y **ninguna recibe "piel sana"**.

### Probado y descartado: analizar también la foto en espejo

Promediar el análisis de la foto original y en espejo (*test-time augmentation*, `entrenamiento/evaluar_tta.py`) redujo los no concluyentes en un conjunto (36 % → 32 %), los aumentó en otro (35 % → 40 %) y bajó la exactitud en ambos. Queda programado pero desactivado.

## Control de calidad de la foto

Antes de analizarla se rechazan las fotos demasiado pequeñas, oscuras, sobreexpuestas o borrosas. Los límites se **calibraron con el propio dataset**, por debajo del percentil 1 de cada medida. Una primera versión, con límites puestos a ojo, rechazaba el 45 % de las fotos válidas por "borrosas", porque la piel es una superficie suave con pocos bordes. La nitidez se mide siempre sobre la foto reducida a 224 px, para que sea comparable entre resoluciones.

## Experimento: agregar un segundo dataset (MSID)

Para reducir los resultados no concluyentes se probó añadir el *Monkeypox Skin Images Dataset* (MSID) solo al entrenamiento.

- 770 imágenes de 4 clases (varicela, sarampión, mpox, piel sana), descargadas de Mendeley Data con verificación SHA-256.
- **Deduplicación con dHash** (`entrenamiento/deduplicar.py`): se quitaron **177 imágenes que ya estaban en MSLD** y 18 repetidas internas. Sin este paso, fotos de prueba habrían entrado al entrenamiento y las métricas saldrían infladas. Quedaron 575 (88 de varicela).
- La evaluación siguió siendo con los mismos 5 pliegues de MSLD, para comparar de forma justa.

| Entrenamiento | Exactitud | Sensibilidad varicela | Especificidad | Indeterminadas (umbral 0.70) | Sensibilidad decidida (0.70) |
|---|---|---|---|---|---|
| Solo MSLD | 79.4 % | **65.5 %** | 95.5 % | 32 % | **75 %** |
| MSLD + MSID | 80.5 % | 54.3 % | 94.2 % | 22 % | 55 % |

**Conclusión:** con MSID el modelo se vuelve *más seguro pero se equivoca más con la varicela*: deja menos fotos sin decidir, pero detecta peor los casos reales. Para el objetivo de la app es peor, así que **se descartó**. Bajar el umbral del modelo original a 0.60 logra la misma reducción de indeterminadas (21 %) con mejor sensibilidad (69 %). Una explicación probable es que las fotos de MSID tienen otro estilo (otras fuentes, encuadres y compresión) que confunde al modelo con tan pocos ejemplos.

Cita: Bala, D. y Hossain, M. S. (2023). *Monkeypox Skin Images Dataset (MSID)*, versión 6. Mendeley Data. DOI [10.17632/r9bfpnvyxr.6](https://doi.org/10.17632/r9bfpnvyxr.6). Licencia CC BY 4.0.

## Limitaciones

- El dataset es pequeño (75 fotos de varicela) y los intervalos de error son amplios (± 19 puntos de sensibilidad entre pliegues).
- Las fotos provienen principalmente de fuentes web; el rendimiento con fotos de celular en condiciones reales puede ser menor.
- El modelo no detecta si la foto no es de piel; el control de calidad solo rechaza fotos oscuras, borrosas o pequeñas.
- **No es un dispositivo médico.** El resultado es orientativo y debe confirmarlo un profesional.

## Reproducir

```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements-train.txt
python -m entrenamiento.preparar_msld "ruta\al\archive.zip"
python -m entrenamiento.validacion_cruzada --epocas 25 --arquitectura convnext_tiny.fb_in22k_ft_in1k
python -m entrenamiento.entrenar_vision --datos datasets/msld/fold1 --epocas 25 --arquitectura convnext_tiny.fb_in22k_ft_in1k --umbral 0.60 --incluir-prueba --version vision-1.2.0
python -m entrenamiento.cuantizar
# Después: renombrar varicela.onnx -> varicela_fp32.onnx y varicela_int8.onnx -> varicela.onnx
```
