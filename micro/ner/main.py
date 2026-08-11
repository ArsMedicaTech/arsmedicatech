"""
A simple FastAPI app for extracting named entities (with clinical assertion
status) from text using spaCy + scispaCy + medspaCy's ConText algorithm.
"""
import os
from fastapi import FastAPI
from pydantic import BaseModel
import spacy, logging, subprocess, sys

# medspacy_context is registered as a spaCy factory as a side effect of this
# import (the class itself is ConText in current medspacy releases; older
# releases called it ConTextComponent).
from medspacy.context import ConText  # noqa: F401  (registers "medspacy_context")

MODEL = os.environ.get("MODEL_NAME", "en_core_sci_sm")
PIPE_DISABLE = ["lemmatizer"]  # keep the parser: needed for sentence + ConText scoping

import time
print("Starting load...")
t0 = time.time()

# Lazy-load with download fallback (useful for local dev runs)
try:
    nlp = spacy.load(MODEL, disable=PIPE_DISABLE)
except OSError:
    logging.warning(f"{MODEL} not found – downloading...")
    subprocess.run([sys.executable, "-m", "spacy", "download", MODEL], check=True)
    nlp = spacy.load(MODEL, disable=PIPE_DISABLE)

if "medspacy_context" not in nlp.pipe_names:
    nlp.add_pipe("medspacy_context")

print(f"Model loaded in {time.time() - t0:.2f} seconds")

app = FastAPI(title="Concept Extraction API", version="0.2.0")


class TextIn(BaseModel):
    text: str


class EntityOut(BaseModel):
    text: str
    label: str
    start_char: int
    end_char: int
    assertion: str          # present | absent | family_history | hypothetical | historical
    is_uncertain: bool
    sentence: str            # ent.sent.text
    sentence_start_char: int  # ent.sent.start_char


class ExtractionOut(BaseModel):
    entities: list[EntityOut]
    schema_version: int = 2
    model: str = MODEL


def _assertion_for(ent) -> str:
    """
    Map medspacy_context's ConText attributes to a single assertion label.
    First match wins, in this order: negated > family > hypothetical >
    historical > present.
    """
    if ent._.is_negated:
        return "absent"
    if ent._.is_family:
        return "family_history"
    if ent._.is_hypothetical:
        return "hypothetical"
    if ent._.is_historical:
        return "historical"
    return "present"


@app.post("/ner/extract", response_model=ExtractionOut)
async def extract(payload: TextIn) -> ExtractionOut:
    """
    Extract named entities from the provided text, annotated with clinical
    assertion status (present / absent / family_history / hypothetical /
    historical) and sentence context.
    """
    doc = nlp(payload.text)
    ents = [
        EntityOut(
            text=e.text,
            label=e.label_,
            start_char=e.start_char,
            end_char=e.end_char,
            assertion=_assertion_for(e),
            is_uncertain=e._.is_uncertain,
            sentence=e.sent.text,
            sentence_start_char=e.sent.start_char,
        )
        for e in doc.ents
    ]
    return ExtractionOut(entities=ents, model=MODEL)


@app.get("/ner/ready")
async def ready() -> dict:
    """
    Check if the service is ready. Reports the resolved model, schema
    version, active pipeline, and whether assertion detection is enabled so
    a misconfiguration is visible without sending a probe document.
    """
    return {
        "status": "ready",
        "model": MODEL,
        "schema_version": 2,
        "pipeline": nlp.pipe_names,
        "context_enabled": "medspacy_context" in nlp.pipe_names,
    }
