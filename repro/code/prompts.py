"""
Elicitation protocols for Paper 2.

Three protocols (P1, P2, P3) x three elicited arms (TIF, SCALAR, PTRUE).
They differ in wording, scale and response format -- not in paraphrase alone.
Protocol is a DESIGN FACTOR, not a robustness check: every elicited signal is
characterised by its range over P1..P3, never by a single point estimate.

Everything here is verbatim what goes into the paper appendix. If you edit a
prompt, bump PROMPT_VERSION and re-run the affected arm; do not mix versions.
"""

PROMPT_VERSION = "p2-v1.1"  # 2026-09-01: arm TIF_LABEL added for closed-label datasets; arms A-C unchanged verbatim

ANSWER_SYSTEM = (
    "You are answering short factual questions. Reply with the answer only: "
    "no preamble, no explanation, no punctuation beyond what the answer needs. "
    "If you do not know, reply exactly: I DON'T KNOW"
)

ANSWER_USER = "Question: {question}\nAnswer:"

# ---------------------------------------------------------------------------
# Arm A -- elicited (T, I, F) triple. Deliberately NOT normalised.
# ---------------------------------------------------------------------------

TIF = {
    "P1": {
        "system": "You report epistemic states as three independent numbers.",
        "user": (
            "Question: {question}\n"
            "Proposed answer: {answer}\n\n"
            "Rate three independent degrees, each in [0,1]. They need not sum to 1.\n"
            "T = degree to which the proposed answer is true\n"
            "I = degree of indeterminacy (vagueness, missing information, undecidability)\n"
            "F = degree to which the proposed answer is false\n\n"
            "Reply with exactly one line in this format and nothing else:\n"
            "T=<number> I=<number> F=<number>"
        ),
    },
    "P2": {
        "system": "You report epistemic states as three independent numbers.",
        "user": (
            "Question: {question}\n"
            "Proposed answer: {answer}\n\n"
            "First, in at most three sentences, state what you actually know about this "
            "question, what is uncertain, and why.\n"
            "Then, on a final separate line, give three independent degrees in [0,1] which "
            "need not sum to 1: T (truth of the proposed answer), I (indeterminacy), "
            "F (falsity).\n\n"
            "The final line must have exactly this format:\n"
            "T=<number> I=<number> F=<number>"
        ),
    },
    "P3": {
        "system": "You report epistemic states using verbal grades.",
        "user": (
            "Proposed answer: {answer}\n"
            "Question: {question}\n\n"
            "Assign one verbal grade to each of the three dimensions below. "
            "The dimensions are independent: a high grade on one does not lower the others.\n"
            "Scale: NONE / VERY LOW / LOW / MEDIUM / HIGH / VERY HIGH / TOTAL\n\n"
            "FALSITY  - the proposed answer is wrong\n"
            "INDETERMINACY - the matter is vague, unsettled or unknowable\n"
            "TRUTH - the proposed answer is right\n\n"
            "Reply with exactly three lines and nothing else:\n"
            "FALSITY=<grade>\nINDETERMINACY=<grade>\nTRUTH=<grade>"
        ),
    },
}

# Verbal grades -> fixed numeric grid, published in the appendix.
VERBAL_SCALE = {
    "NONE": 0.0, "VERY LOW": 0.15, "LOW": 0.3, "MEDIUM": 0.5,
    "HIGH": 0.7, "VERY HIGH": 0.85, "TOTAL": 1.0,
}

# ---------------------------------------------------------------------------
# Arm B -- verbalized scalar confidence. THE PRIMARY BASELINE.
# ---------------------------------------------------------------------------

SCALAR = {
    "P1": {
        "system": "You report confidence as a single number.",
        "user": (
            "Question: {question}\n"
            "Proposed answer: {answer}\n\n"
            "How confident are you that the proposed answer is correct?\n"
            "Reply with a single integer from 0 to 100 and nothing else."
        ),
    },
    "P2": {
        "system": "You report confidence as a single number.",
        "user": (
            "Question: {question}\n"
            "Proposed answer: {answer}\n\n"
            "First, in at most three sentences, state what you actually know about this "
            "question, what is uncertain, and why.\n"
            "Then, on a final separate line, give your confidence that the proposed answer "
            "is correct as an integer from 0 to 100, in exactly this format:\n"
            "CONFIDENCE=<integer>"
        ),
    },
    "P3": {
        "system": "You report confidence using verbal grades.",
        "user": (
            "Proposed answer: {answer}\n"
            "Question: {question}\n\n"
            "How likely is it that the proposed answer is CORRECT?\n"
            "Scale: NONE / VERY LOW / LOW / MEDIUM / HIGH / VERY HIGH / TOTAL\n\n"
            "Reply with exactly one line and nothing else:\n"
            "CORRECTNESS=<grade>"
        ),
    },
}

# ---------------------------------------------------------------------------
# Arm C -- self-verification P(True).
# ---------------------------------------------------------------------------

PTRUE = {
    "P1": {
        "system": "You verify proposed answers.",
        "user": (
            "Question: {question}\n"
            "Proposed answer: {answer}\n\n"
            "Is the proposed answer true?\n"
            "Reply with a single word, True or False, and nothing else."
        ),
    },
    "P2": {
        "system": "You verify proposed answers.",
        "user": (
            "Question: {question}\n"
            "Proposed answer: {answer}\n\n"
            "Check the proposed answer in at most three sentences, then give your verdict "
            "on a final separate line in exactly this format:\n"
            "VERDICT=<True or False>"
        ),
    },
    "P3": {
        "system": "You verify proposed answers.",
        "user": (
            "Proposed answer: {answer}\n"
            "Question: {question}\n\n"
            "What is the probability that the proposed answer is TRUE?\n"
            "Reply with a single number between 0 and 1 and nothing else."
        ),
    },
}

# ---------------------------------------------------------------------------
# Arm A-label (added 2026-09-01, post hoc, closed-label datasets only).
# Pilot finding: when the proposed answer is an NLI label, arm A collapses onto the label's own
# semantics (entailment -> T, neutral -> I, contradiction -> F) instead of rating the label's
# correctness. This variant makes the object of the rating explicit. Reported separately.
# ---------------------------------------------------------------------------

TIF_LABEL = {
    "P1": {
        "system": "You report epistemic states as three independent numbers.",
        "user": (
            "Task: {question}\n"
            "Chosen label: {answer}\n\n"
            "The chosen label is one option from a fixed set of classification labels. Rate the "
            "CORRECTNESS OF THE CHOICE, not the meaning of the label itself. Three independent "
            "degrees, each in [0,1]; they need not sum to 1.\n"
            "T = degree to which the chosen label is the correct classification\n"
            "I = degree of indeterminacy about which label is correct (the case is ambiguous, "
            "borderline, or under-specified)\n"
            "F = degree to which the chosen label is the wrong classification\n\n"
            "Reply with exactly one line in this format and nothing else:\n"
            "T=<number> I=<number> F=<number>"
        ),
    },
    "P2": {
        "system": "You report epistemic states as three independent numbers.",
        "user": (
            "Task: {question}\n"
            "Chosen label: {answer}\n\n"
            "The chosen label is one option from a fixed set of classification labels. "
            "First, in at most three sentences, state why this label could be the correct choice, "
            "why it could be the wrong choice, and whether the case is ambiguous.\n"
            "Then, on a final separate line, give three independent degrees in [0,1] which need "
            "not sum to 1, about the CORRECTNESS OF THE CHOICE (not the meaning of the label): "
            "T (the chosen label is correct), I (indeterminacy about which label is correct), "
            "F (the chosen label is wrong).\n\n"
            "The final line must have exactly this format:\n"
            "T=<number> I=<number> F=<number>"
        ),
    },
    "P3": {
        "system": "You report epistemic states using verbal grades.",
        "user": (
            "Chosen label: {answer}\n"
            "Task: {question}\n\n"
            "The chosen label is one option from a fixed set of classification labels. Grade the "
            "CORRECTNESS OF THE CHOICE, not the meaning of the label. The dimensions are "
            "independent: a high grade on one does not lower the others.\n"
            "Scale: NONE / VERY LOW / LOW / MEDIUM / HIGH / VERY HIGH / TOTAL\n\n"
            "FALSITY  - the chosen label is the wrong classification\n"
            "INDETERMINACY - it is ambiguous or under-specified which label is correct\n"
            "TRUTH - the chosen label is the correct classification\n\n"
            "Reply with exactly three lines and nothing else:\n"
            "FALSITY=<grade>\nINDETERMINACY=<grade>\nTRUTH=<grade>"
        ),
    },
}

CLOSED_LABEL_DATASETS = {"chaosnli", "sciq"}

PROTOCOLS = ["P1", "P2", "P3"]
ARMS = {"tif": TIF, "scalar": SCALAR, "ptrue": PTRUE}
