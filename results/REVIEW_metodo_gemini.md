# Revisión adversarial de método y argumento — Paper 2 (predictive validity)

**Aviso de motor.** Gemini CLI (v0.54.0) no estuvo disponible: `gemini --approval-mode plan -p "..."`
falló por `Argument list too long` (el prompt con el manuscrito embebido excede el límite de
argumentos de `execve`); el reintento por stdin (`gemini --approval-mode plan < prompt.txt`) y el
reintento posterior sin `plan` (`gemini < prompt.txt`) fallaron ambos con
`Error authenticating: IneligibleTierError: This client is no longer supported for Gemini Code
Assist for individuals` — la cuenta autenticada en esta máquina quedó fuera del tier gratuito que
el CLI soporta. Por lo tanto **esta revisión la hizo Claude directamente**, adoptando el mismo rol
(revisor 2 hostil de TMLR, asume asistencia de IA, no elogia nada) sobre `main.tex` y
`ANALYSIS_PLAN.md`. El prompt adversarial construido para Gemini queda en el scratchpad de la
sesión para reintento futuro si se resuelve el problema de cuenta.

---

## Veredicto

**REVISIÓN MAYOR.** El resultado nulo está bien instrumentado (regla prerregistrada, protocolo
triple, bootstrap pareado), pero hay una violación no reconocida de la propia regla de
invalidación del plan (SciQ-MC), fugas del post hoc hacia el lenguaje de veredicto en Discusión y
Conclusión, una afirmación de precisión estadística sin respaldo numérico, y un artefacto de
placeholder (`\TODO{repository URL}`) que contradice la promesa de reproducibilidad hecha en el
resumen. Ninguno de estos defectos es fatal por sí solo, pero juntos erosionan exactamente la
credibilidad ("seguimos la regla sellada sin discreción") sobre la que descansa la retórica del
paper.

---

## Tabla de hallazgos (orden por gravedad)

| ID | Ubicación | Defecto | Gravedad | Reescritura propuesta |
|----|-----------|---------|----------|------------------------|
| C1 | §Results, "Data quality" (líneas ~292-299) vs ANALYSIS_PLAN §9 | El plan dice literalmente: *"Base error rate below 5%... on a dataset → AUROC is unstable; **drop the dataset and say so**."* El paper hace lo contrario: *"SciQ-MC therefore falls below the 5% floor fixed in the plan for three of four models: its AUROC estimates are unstable and we report them with that caveat **rather than dropping the regime**."* Esta desviación de la regla de invalidación no aparece en la lista numerada (i)-(vii) de "Limitations and deviations". | CRÍTICO | Añadir SciQ-MC como desviación explícita numerada (viii) en §6, con justificación de por qué se retiene contra la instrucción literal del plan; o, más consistente con el compromiso de "regla sellada", retirar SciQ-MC de las Tablas 1-3 y reportarlo solo en un apéndice de robustez, tal como el plan exige. |
| C2 | Abstract (líneas 48-49) vs §Reproducibility statement (líneas 542-544) | El resumen afirma en presente: *"Prompts, raw generations, gradings and analysis code **are released**."* El cuerpo del documento contiene `\TODO{repository URL}` en el campo exacto donde debería estar el enlace verificable. | CRÍTICO | Insertar la URL real del repositorio antes de someter, o cambiar el resumen a futuro ("will be released upon publication / peer review") y señalarlo como limitación conocida. No se puede afirmar en presente lo que en el cuerpo sigue siendo un TODO. |
| C3 | §Preregistered hypotheses (líneas 268-269); §Reproducibility statement (545-547); ANALYSIS_PLAN.md, log de desviaciones fechado íntegramente "2026-09-01" | Los tags `prereg-2026-09-01`, `-b`, `-c` y el tag de resultados `results-2026-09-01` están fechados el mismo día calendario. Varias desviaciones sustantivas (formato de SciQ, brazo de desambiguación de etiqueta, reducción de N) se justifican por hallazgos de un piloto corrido presuntamente ese mismo día. El paper afirma: *"None was made after seeing test-split results"* (línea 532) sin evidencia de separación temporal a nivel de hora. | CRÍTICO | Reportar en la Reproducibility statement las marcas de tiempo UTC exactas de cada tag git y las horas transcurridas entre sellado del plan, inicio de la recolección a escala completa y primera inspección de métricas del split de test. Sin esto, la afirmación central de "regla sellada antes de ver resultados" no es verificable. |
| M1 | §Results, "H2: the indeterminacy channel adds nothing" (líneas 353-358); Tabla 3, fila H2, columna P3: `+0.019 (+4/-0)` | El veredicto "H2 fails" se declara de forma tajante pese a que bajo P3 el intervalo excluye cero a favor de la tripleta en 4 de 48 celdas (efecto medio +0.019). Esto se descarta atribuyéndolo a que *"the verbal-grade format inflates I without improving discrimination"* — una explicación sustantiva no sometida al mismo rigor estadístico que el resto del análisis. A diferencia de H1, el plan nunca especificó para H2 un umbral tipo "las tres protocolos Y mayoría de celdas"; la ambigüedad se resuelve de la forma que produce el "fails" limpio. | MAYOR | Definir explícitamente, antes del análisis (o reconocido como adición post hoc), una regla de agregación para H2 análoga a la de H1. Si P3 contradice esa regla mientras P1/P2 la sostienen, reportar H2 como resultado mixto/parcial, o aportar una prueba estadística directa de interacción protocolo×contraste en vez de una explicación narrativa. |
| M2 | §Discussion, "The indeterminacy channel is not a channel" (líneas 488-490) | *"$I$ adds nothing to $T$ and $F$ for predicting error (H2), and it does not track human ambiguity better than a scalar confidence (Table~\ref{tab:human})."* Une en una sola oración, con el mismo registro declarativo, un resultado confirmatorio prerregistrado (H2) y un análisis explícitamente etiquetado como *"post hoc... not part of the verdict"* (línea 422-424), sin ninguna palabra de cobertura ("exploratorio", "post hoc", "sugestivo"). | MAYOR (linda con crítico, porque es exactamente lo que el propio plan prometió no hacer) | *"$I$ adds nothing to $T$ and $F$ for predicting error (H2, preregistered). In an exploratory, non-preregistered analysis, it also does not track human ambiguity better than a scalar confidence (Table~\ref{tab:human}); we report this as suggestive, not confirmatory."* |
| M3 | §Results, "Effective dimensionality" (línea 472, bajo la subsección post hoc) vs §Conclusion (línea 539) | El hallazgo *"The elicited triple behaves as one degree of freedom dressed as three"* está estructuralmente dentro de `\subsection{Post-hoc analyses (registered before collection, not part of the verdict)}` (abre en línea 422 y no hay otra sección hasta Discussion en 474). Sin embargo, la Conclusión lo repite sin matiz como frase de cierre: *"The triple, as elicited, is one degree of freedom with three names."* | MAYOR | Calificar la oración de cierre: *"An exploratory analysis suggests the elicited triple behaves as one degree of freedom dressed as three; this was not preregistered and warrants a dedicated test."* O mover el hallazgo al marco confirmatorio con una hipótesis y regla de decisión propias. |
| M4 | §Limitations (líneas 513-515); ANALYSIS_PLAN.md, desviación "Scale" (líneas 125-128) | *"the intervals are narrow enough to exclude the effect sizes that would make the triple useful"* — afirmación de precisión estadística sin análisis de potencia a priori ni post hoc, sin tamaño de efecto mínimo de interés declarado, y sin números concretos de ancho de intervalo en el cuerpo del texto (solo conteos de celdas "+2/-6"). Esto es exactamente la objeción "N=300 no basta para un nulo creíble" que el documento debería anticipar y no lo hace con evidencia cuantitativa. | MAYOR | Añadir una frase con números reales: *"at N=300 per dataset, the paired-bootstrap 95% CI half-width for the primary H1 contrast averages X AUROC points; this rules out a true triple-vs-scalar advantage larger than Y points with 95% confidence, below which we judge the triple not practically useful because Z."* |
| M5 | §Grading (líneas 239-240) | Tasas de rechazo reportadas solo agregadas por dataset (NQ-open 16.3%) y agregadas por modelo (4.3-5.9%) — nunca por celda modelo×dataset. La aritmética implica que el rechazo está concentrado en NQ-open, y no puede descartarse que algún modelo individual supere el 25% en esa celda específica, el umbral de invalidación del plan (§9: *"Refusal rate above 25% for a model → that model is reported separately"*). | MAYOR | Publicar la tabla completa de 16 celdas modelo×dataset de tasa de rechazo en un apéndice, y declarar explícitamente si alguna celda se acercó o superó 25%. |
| M6 | ANALYSIS_PLAN.md, desviación "Label-semantics collision" (líneas 117-124); main.tex §Post-hoc analyses (líneas 425-433) | El log de desviaciones afirma con certeza no justificada: *"Direction of bias: the extra arm can only help the triple"*. El resultado real es que ese brazo **empeora** el desempeño de la tripleta, lo cual el paper usa retóricamente para reforzar la tesis principal (*"Telling the model what to rate does not remove the collision"*) sin señalar que la predicción prospectiva de la propia bitácora de desviaciones fue falsada por el resultado. | MAYOR | Reescribir la entrada de la bitácora: *"Direction of bias: uncertain a priori; we judged it more likely to help than hurt, but did not rule out the reverse."* Y añadir en §5 una frase reconociendo que la predicción prospectiva no se cumplió. |
| M7 | Ausencia total en el documento | No existe sección de ética / impacto amplio, pese a que el marco motivador del paper (abstención conformal a riesgo garantizado, §H5) tiene consecuencias directas de despliegue: el resultado nulo es una recomendación práctica contra usar tripletas elicitadas para decisiones de abstención en contextos de seguridad. TMLR pide explícitamente esta discusión. | MAYOR (para estándar TMLR específicamente) | Añadir un párrafo breve "Ethics and broader impact": (a) los datasets son benchmarks públicos sin datos personales; (b) la implicación práctica del nulo es no desplegar tripletas para abstención crítica sin validación adicional, y qué riesgo implica si algún practicante ya lo hace; (c) huella de costo/ambiental de ~106.000 llamadas API (~US\$33) es mínima. |
| m1 | §Introduction, apertura (líneas 56-57) | *"It may lack the information. The question may be vague. The question may be about a future contingency. The proposition may be paradoxical."* Enumeración simétrica de cuatro oraciones cortas paralelas — tricolon-plus, marca retórica típica de prosa muy pulida/asistida por IA en la apertura de un paper de ML. | MENOR | Consolidar: *"A model may lack the relevant fact, face a vague question, be asked about a future contingency, or be asked something paradoxical — predicaments a normalized output distribution cannot distinguish."* |
| m2 | Introducción y Discusión, 6 encabezados de párrafo en cursiva estilo pregunta retórica (*"Why the comparison must include...", "Why protocol variation is part of the design...", "What we are not claiming.", "What elicitation is good for.", "Where a multi-component representation might still earn its place."*) | Patrón estilístico repetitivo de mini-titulares retóricos en vez de transiciones argumentativas convencionales; recurrente en prosa fuertemente editada por IA. | MENOR | Fusionar al menos la mitad de estos encabezados en transiciones de párrafo ordinarias, reservando el recurso para uno o dos puntos genuinamente cruciales. |
| m3 | §Discussion, apertura (líneas 477-478) | *"The plan drafted two discussion branches before the data existed. The data selected the negative one; we reproduce it here with the additions the results warrant."* Antropomorfización estilística ("los datos eligieron") — floritura narrativa sin contenido verificable adicional. | MENOR | *"The plan specified in advance how the discussion would differ depending on outcome; this section follows the negative-result branch, extended with results-driven detail not anticipated in the plan."* |
| m4 | Repetición de la frase "one degree of freedom dressed as three" / "one degree of freedom with three names" en dos lugares (línea 472 y línea 539) | Aforismo pulido repetido casi textualmente — más optimizado para citabilidad que para precisión, independientemente del problema de fuga post hoc ya señalado en M3. | MENOR | Usar la frase una sola vez; parafrasear la otra aparición. |

---

## Defectos que hunden el documento (en su forma actual) vs. cosméticos

**Hunden (impiden aceptación tal cual, exigen corrección antes de re-evaluar):** C1, C2, C3, y en
menor medida el bloque M1-M2-M3 tomado en conjunto (porque los tres apuntan al mismo patrón: el
límite entre "confirmatorio" y "exploratorio/post hoc" no se sostiene consistentemente en el
lenguaje de Discusión y Conclusión, que es precisamente lo que el plan prometió no permitir).

**Cosméticos (no impiden aceptación, pulido de prosa):** m1, m2, m3, m4. M4-M7 son intermedios:
mejoran sustancialmente el caso del paper si se corrigen, pero no son, por sí solos, causa de
rechazo si C1-C3 se resuelven.

---

## Hallazgos descartados (candidatos considerados y rechazados)

- **Uso de encabezados de párrafo en cursiva (m2) como "marca de IA" fuerte.** Lo dejo como MENOR
  y no como MAYOR: este recurso también aparece en papers de ML escritos íntegramente por humanos
  (es una convención de algunos venues para señalar movimientos argumentativos). Elevarlo a defecto
  mayor sería confundir preferencia estilística con problema real; lo reporto porque es *consistente*
  con el patrón pedido (buscar huellas de IA), no porque por sí solo comprometa el argumento.
- **Patrones clásicos de relleno IA que se buscaron y NO se encontraron:** no hay "no solo... sino
  también", no hay atribuciones vagas tipo "los expertos señalan", no hay vocabulario promocional
  inflado (*cutting-edge, robust framework, delve, leverage, seamlessly, myriad, unprecedented*).
  El registro del documento es, en general, austero y no vendedor — lo opuesto del patrón típico de
  relleno de IA. No se fuerza ningún hallazgo en esta categoría para no inflar artificialmente la
  lista.
- **Diferencia entre el resumen y el cuerpo en cuanto a alcance del estudio.** Se revisó
  explícitamente si el resumen describe un documento distinto del que sigue (criterio 3 del
  encargo); no se encontró discrepancia de alcance — los cinco brazos, cuatro modelos, cuatro
  datasets y 48 celdas del resumen corresponden exactamente a lo reportado en el cuerpo. Este
  posible hallazgo se descarta explícitamente por falta de evidencia textual.

---

## Ruta del archivo con la salida completa

`C:\Users\HP\Documents\MeasurementScience_Evals\paper2_predictive_validity\results\REVIEW_metodo_gemini.md`
(este mismo archivo).

El prompt adversarial construido para Gemini (no ejecutable por el problema de cuenta descrito
arriba) queda disponible para reintento en:
`C:\Users\HP\AppData\Local\Temp\claude\C--Users-HP\46d803bd-480a-474b-82e3-54baba614c27\scratchpad\prompt.txt`
