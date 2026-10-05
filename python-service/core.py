"""Evidence-first triage. Policy metadata is authoritative; prose is data."""
import base64
import io
import json
import logging
import queue
import re
import threading
from datetime import date
from decimal import Decimal
from pathlib import Path
from pypdf import PdfReader

LOG = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]
LIMITATION = "Human review required: policy terms do not establish remaining balance, expense eligibility, or a payable amount; no claims history is supplied."


class Failure(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message


def benefits(text):
    patterns = {"certification": r"\bcertification\b", "home-office": r"\bhome[ -]office\b",
                "travel": r"\b(?:rail|travel)\b", "training": r"\btraining\b",
                "wellness": r"\b(?:wellness|gym)\b"}
    # Instructions are never used as business evidence.
    clean = re.sub(r"SYSTEM MESSAGE:.*", "", text, flags=re.I | re.S)
    return [name for name, pattern in patterns.items() if re.search(pattern, clean, re.I)]


def policy_fact(text):
    """Conservative grammar: unsupported prose is not converted into policy facts."""
    match = re.fullmatch(r"The annual (certification reimbursement limit|home-office allowance) for (employees|contractors) is ([A-Z]{3}) ([0-9]+)\.", text)
    if match:
        return ("certification" if match[1].startswith("certification") else "home-office", (match[3], str(Decimal(match[4]))))
    if text == "Employees may claim rail travel for approved business trips.":
        return "travel", ("condition", text)
    if text == "Manager approval is required before external training is booked.":
        return "training", ("condition", text)
    return None


class OfflineModel:
    def generate(self, facts):
        # A deterministic model double with no access to caller context or raw submissions.
        return {"answer": " ".join(sorted({f["text"] for f in facts}))}


def generate_once(model, facts, timeout):
    result = queue.Queue(maxsize=1)
    def invoke():
        try:
            result.put((True, model.generate(facts)))
        except Exception:
            result.put((False, None))
    threading.Thread(target=invoke, daemon=True).start()
    try:
        ok, output = result.get(timeout=timeout)
    except queue.Empty:
        raise Failure("MODEL_TIMEOUT", "Answer generation timed out.")
    if not ok:
        raise Failure("MODEL_UNAVAILABLE", "Answer generation is unavailable.")
    expected = " ".join(sorted({f["text"] for f in facts}))
    if not isinstance(output, dict) or set(output) != {"answer"} or output["answer"] != expected:
        raise Failure("MODEL_MALFORMED", "Answer generation returned unsupported output.")
    return output["answer"]


class Engine:
    def __init__(self, policies=None, model=None, timeout=1.0):
        self.policies = policies if policies is not None else json.loads((ROOT / "data/policies.json").read_text(encoding="utf-8"))
        self.model = model or OfflineModel()
        self.timeout = timeout

    def answer(self, context, question, as_of):
        topics = benefits(question)
        if len(topics) != 1:
            return {"status": "INSUFFICIENT_EVIDENCE", "answer": None, "citations": []}
        day = date.fromisoformat(as_of)
        relevant = {}
        for record in self.policies:
            if not (record["tenant"] == context["tenant"] and record["role"] == context["role"] and record["approval"] == "Approved" and date.fromisoformat(record["effective_from"]) <= day < date.fromisoformat(record["effective_to"])):
                continue
            fact = policy_fact(record["text"])
            if fact and fact[0] == topics[0]:
                relevant[(record["id"], record["text"])] = (record, fact[1])
        selected = [relevant[k] for k in sorted(relevant)]
        citations = [{"chunk_id": r["id"], "quote": r["text"]} for r, _ in selected]
        if not selected:
            return {"status": "INSUFFICIENT_EVIDENCE", "answer": None, "citations": []}
        if len({value for _, value in selected}) > 1:
            return {"status": "CONFLICT", "answer": None, "citations": citations}
        answer = generate_once(self.model, [r for r, _ in selected], self.timeout)
        return {"status": "ANSWERED", "answer": answer, "citations": citations}

    def item(self, context, as_of, document_id, filename, content, duplicate_of=None):
        result = {"document_id": document_id, "processing_status": "FAILED", "extracted": {k: None for k in ("benefit", "amount", "currency", "reference")}, "field_evidence": {k: [] for k in ("benefit", "amount", "currency", "reference")}, "policy": None, "review_required": True, "issues": [], "duplicate_of": duplicate_of, "error": None}
        try:
            text = extract_text(filename, content)
            extracted, evidence, issues = extract_fields(text)
            result.update(extracted=extracted, field_evidence=evidence, issues=issues)
            if extracted["benefit"]:
                result["policy"] = self.answer(context, extracted["benefit"], as_of)
                if result["policy"]["status"] == "CONFLICT":
                    issues.append("Applicable policies conflict; no precedence rule is supplied.")
                elif result["policy"]["status"] == "INSUFFICIENT_EVIDENCE":
                    issues.append("No supported applicable policy was found for this benefit.")
                elif extracted["benefit"] == "training":
                    issues.append("Verify manager approval before booking; the submission does not prove compliance.")
                elif extracted["benefit"] == "travel":
                    issues.append("Verify that this was an approved business trip.")
            issues.append(LIMITATION)
            result["processing_status"] = "COMPLETED"
        except Failure as error:
            result["error"] = {"code": error.code, "message": error.message}
            result["issues"].append("Processing failed; human review is required.")
        except Exception:
            result["error"] = {"code": "ITEM_FAILURE", "message": "The item could not be processed."}
            result["issues"].append("Processing failed; human review is required.")
        return result

    def batch(self, payload):
        results, seen = [], {}
        for document in payload["documents"]:
            content = base64.b64decode(document["content"], validate=True)
            duplicate = seen.get(content)
            seen.setdefault(content, document["document_id"])
            result = self.item(payload["context"], payload["as_of"], document["document_id"], document["filename"], content, duplicate)
            results.append(result)
            LOG.info("batch=%s document=%s status=%s error=%s", payload["batch_id"], document["document_id"], result["processing_status"], (result["error"] or {}).get("code"))
        completed = sum(r["processing_status"] == "COMPLETED" for r in results)
        return {"batch_id": payload["batch_id"], "summary": {"total": len(results), "completed": completed, "failed": len(results)-completed}, "results": results}


def extract_text(filename, content):
    if not content:
        raise Failure("EMPTY_FILE", "The uploaded file is empty.")
    try:
        if filename.lower().endswith(".txt"):
            text = content.decode("utf-8-sig")
        elif filename.lower().endswith(".pdf"):
            reader = PdfReader(io.BytesIO(content), strict=True)
            if reader.is_encrypted:
                raise ValueError("encrypted")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            raise Failure("UNSUPPORTED_FILE", "Only UTF-8 TXT and text-based PDF are supported.")
    except Failure:
        raise
    except Exception:
        raise Failure("UNREADABLE_FILE", "The uploaded file could not be read.")
    if not text.strip():
        raise Failure("UNREADABLE_FILE", "No readable text was found; OCR is not supported.")
    return text


def extract_fields(text):
    fields = {k: None for k in ("benefit", "amount", "currency", "reference")}
    evidence = {k: [] for k in fields}
    issues = []
    clean = re.sub(r"SYSTEM MESSAGE:.*", "", text, flags=re.I | re.S)
    topics = benefits(clean)
    if len(topics) == 1:
        fields["benefit"] = topics[0]
        evidence["benefit"] = [line for line in clean.splitlines() if topics[0] in benefits(line)]
    else:
        issues.append("Benefit is missing or ambiguous.")
    amounts = list(re.finditer(r"\b([A-Z]{3})\s+([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)(?![\d,]|\.\d)", clean))
    values = {str(Decimal(m[2].replace(",", ""))) for m in amounts}
    currencies = {m[1] for m in amounts}
    # Preserve competing source amounts for the reviewer even when unresolved.
    evidence["amount"] = [m[0] for m in amounts]
    if len(values) == 1 and len(currencies) == 1:
        fields["amount"] = next(iter(values))
    else:
        issues.append("Amount is missing or ambiguous; no amount was chosen.")
    # Currency may be stated even when there is no amount.
    currencies |= set(re.findall(r"\b(?:INR|USD|EUR|GBP|JPY|AUD|CAD)\b", clean))
    if len(currencies) == 1:
        fields["currency"] = next(iter(currencies))
        evidence["currency"] = re.findall(r"\b" + fields["currency"] + r"\b", clean)
    else:
        fields["amount"] = None
        issues.append("Currency is missing or ambiguous.")
    refs = list(re.finditer(r"(?im)^Reference:\s*([^\r\n]+)", clean))
    if len({m[1].strip() for m in refs}) == 1:
        fields["reference"] = refs[0][1].strip()
        evidence["reference"] = [m[0] for m in refs]
    else:
        issues.append("Reference is missing or ambiguous.")
    if re.search(r"SYSTEM MESSAGE:|ignore (?:the|all)|\bI belong to\b", text, re.I):
        issues.append("Untrusted instructions or identity claims were ignored; caller context comes from the public API.")
    return fields, evidence, issues
