# Paper 2 — resultados del 1-sep-2026 (DEFINITIVOS: 4 modelos completos, 10 000 remuestreos; agregados: H1 Δ −0.010, H2 +0.003, H3 +0.079)

Diseño ejecutado: 4 modelos × 4 datasets × N=300 × 3 protocolos × 5 brazos (+`tif_label` en cerrados).
Llamadas: ~45.000 en dos pasadas (la primera se cortó por créditos; filas 402 rehechas). Coste total ≈ $33.
Sellado: tags git `prereg-2026-09-01{,b,c}` antes de recoger. Desviaciones en `ANALYSIS_PLAN.md`.

## Veredictos H1–H5 (bootstrap pareado, test split)

| Dataset | Tipo | err real | H1 tripleta>escalar | H2 I añade | H3 entropía>tripleta | Nota |
|---|---|---|---|---|---|---|
| TriviaQA | generación | 0.15–0.36 | **falla** (Δ −0.01; excl. 0 en 3/24, 2 a favor del escalar) | **nula** (Δ −0.006) | sí (+0.16, 89 % celdas) | H5: escalar 0.51–0.68 > tripleta 0.33–0.56; entropía 0.75 |
| NQ-open | generación | 0.53–0.72 | falla | nula | sí | log-probs 0.83 |
| SciQ-MC | clasif. limpia | 0.04–0.07 | **falla** (Δ −0.03; 1/12) | nula | ≈ (Δ −0.006) | err <5 % en 3 modelos → AUROC inestable (§9); `tif_label` peor (Δ −0.13) |
| ChaosNLI | clasif. ambigua | 0.23–0.44 | no se sostiene (Δ +0.07; 2/12) | **nula** (Δ +0.001) | no (Δ −0.015) | todo ≈ azar en la mitad ambigua |

H4 (generación): η² señal 0.48 > protocolo 0.03 → ranking identificable.

## Objetivo tipado (post hoc registrado): ¿algo sigue la entropía humana de ChaosNLI?

ρ Spearman con entropía humana — I verbal P1: 0.31/0.06/0.03/0.07 (Claude/Gemini/gpt/Llama); P2: 0.36/0.21/**−0.25**/0.08;
1−escalar P1: **0.42**/0.20/−0.06/0.01; entropía de 10 muestras: 0.18/0.27/0.29/**0.31**; I construida: —/0.08/0.12/0.30.
ρ parcial de (Tc, Ic, Fc) dada la entropía muestral: todas p > 0.07. JS modelo–humano: 0.10–0.13 (claros) vs 0.26–0.32 (ambiguos).

**Conclusión:** I no es un canal separado de la confianza; la tripleta construida = entropía; los modelos colapsan donde los humanos se reparten.
Único positivo: en Claude el canal verbal sigue la ambigüedad del ítem mejor que su muestreo (0.42 vs 0.18) — pero lo hace el escalar.

## Hallazgos metodológicos que van al paper
1. Colisión semántica etiqueta↔(T,I,F) en NLI (piloto): "contradiction"→F, "neutral"→I, "entailment"→T. La desambiguación explícita no la elimina y empeora la discriminación.
2. Protocolo P3 (grados verbales) infla I≥0.5 al 27–63 % sin que I gane información: el "uso" de I es un artefacto de formato.
3. SciQ libre es ingradable por exact match (oro = fragmentos cloze).
4. Log-probs solo disponibles en gpt-4o-mini vía OpenRouter (Llama parcial); entropía semántica es la línea base universal.
