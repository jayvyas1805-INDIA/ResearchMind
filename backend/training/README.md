# NER Fine-Tuning (Stretch Feature)

The app's default entity extraction (`app/services/nlp_service.py`) uses a
rule-based PhraseMatcher over curated MODEL/DATASET/METRIC/METHOD/
TECHNOLOGY term lists. That's precise but only recognizes terms already in
the list — it can't generalize to a model name it's never seen.

This directory fine-tunes a spaCy NER model to recognize these categories
more generally, and — importantly — **evaluates honestly** rather than
just claiming it's better.

## Why the evaluation design matters

The obvious-but-wrong approach: generate training labels with the
rule-based matcher, train a model on them, then "evaluate" by comparing
against more matcher-generated labels. That numbers game always favors the
trained model (it's being scored against a proxy for the exact thing it
was trained to imitate) and proves nothing about real generalization.

The workflow here instead:

1. **`generate_weak_labels.py`** — auto-labels real (already-uploaded)
   paper chunks using the existing rule-based matcher + spaCy's generic
   NER. This is *weak supervision*: noisy, automatic labels, split by
   paper (not by chunk) into train/dev so no document leaks across the
   split.
2. **`train_ner.py`** — fine-tunes `en_core_web_sm`'s NER component on
   those weak labels, adding the five new entity types.
3. **`annotate_gold.py`** — an interactive CLI where *you* hand-label a
   small set (20-50+) of real chunk texts. This is the only label source
   in this pipeline not derived from the rule-based system.
4. **`evaluate_ner.py`** — scores **both** the rule-based matcher and the
   fine-tuned model against the hand-labeled gold set, side by side.

Only step 4's numbers are trustworthy for an "is fine-tuning actually
better" claim. Anything measured against weak labels (including
`train_ner.py`'s own dev-set printout) is directional at best — it tells
you training converged, not that the model generalizes.

## Running it

```bash
cd backend
source .venv/bin/activate

# 1. Upload/process a handful of real papers first (more papers = better split)

# 2. Generate weak-supervision training data
python training/generate_weak_labels.py

# 3. Fine-tune
python training/train_ner.py --epochs 20

# 4. Hand-label a gold test set (10-15 min for ~30 examples)
python training/annotate_gold.py --n 30

# 5. The evaluation that actually matters
python training/evaluate_ner.py
```

## What to expect

With only a handful of papers and a small hand-labeled gold set, don't
expect a dramatic win — that's realistic and worth saying plainly in an
interview. The value here isn't "I beat the baseline by 20 F1 points," it's
demonstrating you understand *why* self-referential evaluation is
misleading and know how to design around it. If the fine-tuned model
doesn't clearly beat the rules on your gold set, that itself is a valid,
explainable finding (small weak-label set, few epochs, domain mismatch) —
not a failure to hide.

## Integration status

This is a standalone research/evaluation artifact — the live app still
uses the rule-based extractor by default (`app/services/nlp_service.py`).
Swapping in the fine-tuned model for production use would mean adding a
config flag (e.g. `NER_MODEL_PATH`) and loading `training/model/` via
`spacy.load()` in place of the PhraseMatcher path, plus re-validating on a
larger gold set first. Left as a deliberate follow-up rather than done
here, since a model this small (trained on this little data) shouldn't
silently become the default.
