# Revisión adversarial de veracidad — Paper 2 (Predictive Validity)

Motor: Codex CLI (`codex exec --sandbox read-only`, codex-cli 0.150.1), complementado y filtrado
con verificación independiente en Python/pandas contra los mismos CSV, y contraste de `refs.bib`
contra `export.arxiv.org` y la API de Crossref (con acceso a internet).

**Veredicto de Codex:** `PUBLICABLE CON CORRECCIONES`

**Mi veredicto tras filtrar falsos positivos:** `PUBLICABLE CON CORRECCIONES` — el diseño, la
estadística y el 90%+ de las cifras reportadas son correctas y reproducibles con precisión exacta
desde `metrics.csv`/`contrasts.csv`/`conformal.csv`/`variance.csv`; pero hay **una cita
bibliográfica con autores fabricados** (crítico, corregible en un minuto) y **cinco cifras
puntuales en el cuerpo del texto que no coinciden con los datos que las respaldan** (mayores, no
invalidan la conclusión general pero sí exigen corrección antes de envío).

---

## Tabla de hallazgos (ordenada por gravedad)

| ID | Ubicación | Problema | Cifra en el texto | Cifra en los datos | Gravedad | Corrección propuesta |
|---|---|---|---|---|---|---|
| H1 | `refs.bib`, entrada `shi2026notall` | Autores fabricados/alterados y uno omitido | `Shi, Yuxuan and Yue, Zihan and Liu, Yifan and Chen, Wei` | AAAI/DOI `10.1609/aaai.v40i30.39727`: **Jie Shi, Xiaodong Yue, Wei Liu, Yufei Chen, Feifan Dong** (título y páginas 25339–25347 sí coinciden) | **CRÍTICO** | `author = {Shi, Jie and Yue, Xiaodong and Liu, Wei and Chen, Yufei and Dong, Feifan}` |
| H2 | §Resultados, H3 (párrafo "sampling bounds elicitation") | Conteo de celdas significativas incorrecto | "significantly so in **22** of 48" | `contrasts.csv`, hypothesis=H3: **25** de 48 (`excludes_zero`=True); por protocolo P1=10, P2=8, P3=7 | **CRÍTICO** | "significantly so in 25 of 48" |
| H3 | §Resultados, H4 | Rango de "uso" de I bajo P1–P2 no cubre el dato real | "rises from **0–4%** (P1–P2) to 27–63% on ChaosNLI" | `results/chaosnli_I.log`: P1 = 0.7–**35.3%**, P2 = 2.0–**31.3%** (gpt-4o-mini domina el máximo por la colisión de etiqueta, no mencionado); P3 = **12.7**–63.0% (Llama por debajo del "27%") | **CRÍTICO** | "rises from 0.7–35.3% (P1), 2.0–31.3% (P2) to 12.7–63.0% (P3); gpt-4o-mini is the outlier under P1–P2 due to the label collision" |
| H4 | §Discusión post-hoc, tabla de correlaciones humanas | Afirmación contradicha por la propia Tabla \ref{tab:human} del artículo | "In every model the scalar confidence tracks human entropy at least as well as I (Claude 0.42)" | En la misma Tabla \ref{tab:human}: Gemini $I$(P2)=0.21 > $1{-}$scalar(P1)=0.20; Llama $I$(P1)=0.07 y $I$(P2)=0.08, ambos > $1{-}$scalar(P1)=0.01 | **CRÍTICO** | "Scalar confidence exceeds I for Claude and gpt-4o-mini; for Gemini and Llama, I(P1/P2) is at least as high as the scalar" |
| H5 | §Resultados, "Data quality" | Conteo/denominador de tasas de parseo incorrecto | "at or above 0.90 in **140** of 144 arm × cell combinations; **the four exceptions**..." | En `metrics.csv`, para los brazos A/B/C (3×3×16=144 celdas) solo hay **3** excepciones (p_true: Claude/ChaosNLI-P3=0.83, Llama/SciQ-MC-P3=0.88; scalar: Claude/NQ-open-P2=0.88) → **141 de 144**. La 4ª excepción citada (tripleta con etiqueta, P3, Llama/SciQ-MC=0.84) pertenece a un conjunto post-hoc distinto de 24 celdas, no a las 144 | **MAYOR** | "141 of 144... the three exceptions were...; additionally, the post-hoc label-disambiguated triple (P3, Llama/SciQ-MC) parsed at 0.84" |
| H6 | §Resultados, H4 (mismo párrafo que H3 arriba) | Cota "hasta 0.10" no se sostiene si se lee como afirmación general (no limitada a ChaosNLI) | "the fitted triple's AUROC moves by up to **0.10** within a model between protocols" | En `metrics.csv`, el rango máximo de AUROC de `s_TIF_lr` entre protocolos, por celda modelo×dataset, es **0.225** (Gemini/NQ-open); también >0.10 en Llama/TriviaQA (0.21), Llama/SciQ (0.18), Llama/NQ-open (0.13), gpt/NQ-open (0.11). Solo es cierto (máx. 0.098) si se restringe a ChaosNLI, que es lo que sugiere el contexto inmediato pero no lo dice explícitamente | **MAYOR** (ambigüedad de alcance) | Acotar explícitamente: "...moves by up to 0.10 on ChaosNLI (up to 0.225 on other datasets, e.g. Gemini/NQ-open)" |
| H7 | §Resultados, "Effective dimensionality" | Afirmación cuantitativa sin respaldo en el dato | "the fitted triple's AUROC equals that of $F-T$ to the third decimal **in most cells**" | En `metrics.csv`: solo **10/48 (21%)** de las celdas coinciden a 3 decimales; solo 21/48 (44%) coinciden a 2 decimales; diferencia absoluta mediana = 0.0063, máxima = 0.218 | **MAYOR** | Sustituir "in most cells" por algo verificable, p. ej. "in about a fifth of cells; the median absolute difference is 0.006" |
| H8 | §Resultados, "Effective dimensionality" | Rango redondeado no coincide con el log fuente | "gpt-4o-mini on ChaosNLI (**41–47%**...)" | `results/chaosnli_I.log`: P1=42.7%, P2=42.0% (nunca 47%) | MENOR | "42.0–42.7%" |
| H9 | §Resultados, "Effective dimensionality" | Excepción adicional no declarada | "$I>T$ is 0–16% in every cell **except** gpt-4o-mini on ChaosNLI" | Recalculado de `raw_paper2.jsonl`: Llama/NQ-open bajo P2 = **17.8%**, también por encima del 16% | MENOR | Reconocer una segunda excepción menor o ajustar el techo a "0–18%" |
| H10 | §Cost | Cifra de gasto no verificable con los archivos del repo | "Total spend was approximately US\$33" | No hay factura/registro de costos en `results/`; el conteo de reintentos (2 657 filas de error) sí es consistente con "about 2,700 failed" | No verificable (no es un error demostrado) | Adjuntar el registro de facturación o eliminar la cifra exacta si no se puede exportar |

### Notas sobre archivos de apoyo (no citados en `main.tex`, pero listados como fuente de datos)

- `results/SUMMARY.md`: "Excluded (refusal or API error): 39.1%" es una cifra engañosa, no un error
  de `main.tex`. `raw_paper2.jsonl` es *append-only*: para ChaosNLI y SciQ-MC cada ítem aparece
  **exactamente dos veces** (el intento fallido por agotamiento de crédito + el reintento exitoso),
  y `analyze.py::build_frame` no deduplica por `item_id` antes de calcular ese cociente. La tasa de
  rechazo final (la que sí usa correctamente `main.tex`: 4.2/16.3/0.8/0%) es de ~5.3% ponderada.
  `main.tex` nunca cita el 39.1%, así que el error no se propaga al artículo, pero es una trampa
  para quien reutilice `SUMMARY.md`.
- `results/RESULTADOS_2026-09-01.md`: contiene cifras obsoletas de una corrida intermedia
  ("Llamadas: ~45.000... filas 402 rehechas", frente a las ~2 657 filas de error reales, consistentes
  con el "~2,700" de `main.tex`) y un bloque de correlaciones Spearman de ChaosNLI que no coincide
  con `results/chaosnli_I.log` (p. ej. gpt-4o-mini $I$ en P1 aparece como 0.03 en las notas y −0.006
  en el log/Tabla \ref{tab:human}; P2 aparece como −0.25 en las notas y −0.180 en el log/tabla).
  `main.tex` usa los valores correctos del log, no los de las notas; la inconsistencia queda
  confinada al archivo informal.

---

## Hallazgos descartados (falsos positivos de Codex)

- **`refs.bib`, entradas `know2guess2026`, `kadavath2022know`, `tian2023just`, `xiong2024can`**:
  Codex las marcó como "autores omitidos" porque usan `and others` tras 3 nombres. Verifiqué cada
  arXiv ID contra `export.arxiv.org`: el título, año e ID son correctos en todos los casos; solo se
  trunca la lista de autores (7 a 36 nombres reales). Truncar con "et al./and others" en artículos
  de muchos autores es práctica bibliográfica estándar y aceptada, no una fabricación ni un error
  de veracidad. El propio encabezado de `refs.bib` solo promete que la entrada fue "verificada"
  (existe, ID correcto), no que la lista de autores sea exhaustiva. Descartado.
- **`refs.bib`, `kwiatkowski2019natural`, corrección de páginas a "452–466"**: Codex propuso ese
  rango como el correcto. Verifiqué directamente contra la API de Crossref
  (`10.1162/tacl_a_00276`): el registro oficial da `page: "453-466"`, **idéntico** al de `refs.bib`.
  La corrección de Codex es en sí misma incorrecta; descartada. (El punto de autores truncados con
  "and others" para un artículo de 18 autores se descarta por el mismo motivo que el punto anterior.)

---

## Verificación propia (no dependiente de Codex)

Para no depender de una sola pasada de Codex, recalculé independientemente en Python/pandas contra
`metrics.csv`, `contrasts.csv`, `conformal.csv`, `variance.csv` y `raw_paper2.jsonl`:

- Tablas 1 y 2 (AUROC pooled y por dataset, las ~40 cifras de ambas tablas): **coinciden
  exactamente** con `metrics.csv`, incluidos los rangos [min, max] entre corchetes y el caso
  especial de `seq_logprob` disponible en 8 de 16 celdas.
- Tabla 3 (contrastes H1/H2/H3 por protocolo, medias y conteos "+/-" de intervalos que excluyen
  cero): **coinciden exactamente**, incluidas las rupturas por dataset citadas en prosa (TriviaQA
  +0.005, NQ-open −0.041 con 4 celdas en contra, SciQ-MC −0.033, ChaosNLI +0.028 con 1 celda a
  favor).
- Tabla de varianza H4 (η² marginal 0.281/0.168/0.024/0.011): coincide exactamente con `SUMMARY.md`
  y con el texto (redondeado a 0.28/0.17/0.024/0.011).
- H5 (conformal, α=0.10): al restringir a las celdas con umbral finito para ambas señales (36 de
  48), la media −0.026, el desglose por protocolo (−0.020/+0.013/−0.071) y el conteo 8 más / 23
  menos / 5 igual **coinciden exactamente**; igual la comparación de entropía semántica frente al
  escalar (+0.11, 18 arriba/12 abajo) usando el par de señales correspondiente.
- Contrastes de la tripleta con etiqueta (post-hoc): −0.102/−0.023/−0.083 vs. escalar y
  −0.107/−0.016/−0.066 vs. tripleta original: **coinciden exactamente** con `contrasts.csv`
  (hypothesis `H1lab`/`Hlab_vs_A`).
- Tasas de rechazo por dataset (4.2/16.3/0.8/0%) y por modelo (4.3–5.9%): recalculadas desde
  `raw_paper2.jsonl` deduplicando filas de error, **coinciden exactamente**.
- Tasas de error base por dataset (0.225/0.625/0.048/0.308) y rango de SciQ-MC por modelo
  (0.037–0.067, 3 de 4 modelos bajo el piso del 5%): **coinciden exactamente**.
- Las 4 excepciones concretas de tasa de parseo citadas por nombre (valores 0.83/0.88/0.88/0.84)
  **sí existen** en `metrics.csv` con esos valores exactos; el error está solo en el conteo total
  ("140 de 144", ver hallazgo H5 arriba).
- Tabla \ref{tab:human} (Spearman ChaosNLI) y `mean_JS` por mitad clara/ambigua: recalculados desde
  `chaosnli_constructed_vs_human.csv` y re-ejecutando `analyze_chaosnli_constructed.py`,
  **coinciden** (incluida la afirmación "Llama reversed": JS claro=0.274 > JS ambiguo=0.181 para
  Llama, al revés que los otros tres modelos).
- Las 24 claves citadas en `main.tex` existen todas en `refs.bib` y viceversa (sin huérfanas, sin
  citas sin entrada). Los 19 identificadores arXiv y 3 DOI se verificaron uno por uno contra
  `export.arxiv.org`/Crossref: todos los IDs, títulos y años son correctos; solo `shi2026notall`
  tiene autores incorrectos (hallazgo H1).
- Los tags de git citados en la declaración de reproducibilidad (`prereg-2026-09-01`, `-b`, `-c`,
  `results-2026-09-01`) existen y están ordenados cronológicamente antes/después de la recolección,
  consistente con lo declarado.

En conjunto, la enorme mayoría (>90%) de las cifras cuantitativas del cuerpo del artículo se
verificó exacta contra los CSV. Los errores encontrados son puntuales y concentrados en: (a) una
cita con autoría mal atribuida, (b) tres o cuatro cifras de redondeo/conteo en los párrafos de H4 y
"Effective dimensionality" sobre ChaosNLI, y (c) una afirmación de la sección post-hoc que
contradice la propia Tabla \ref{tab:human} del artículo.

## Rutas de archivos

- Informe (este archivo): `C:\Users\HP\Documents\MeasurementScience_Evals\paper2_predictive_validity\results\REVIEW_veracidad_codex.md`
- Salida cruda de Codex (respuesta final + veredicto): `C:\Users\HP\Documents\MeasurementScience_Evals\paper2_predictive_validity\results\salida_codex_raw.md`
- Manuscrito revisado: `C:\Users\HP\Documents\MeasurementScience_Evals\paper2_predictive_validity\main.tex`
- Bibliografía: `C:\Users\HP\Documents\MeasurementScience_Evals\paper2_predictive_validity\refs.bib`
