import hashlib

from querymaster.faqs.models import FAQ


def build_faq_chunk(faq: FAQ) -> dict:
    raw_text = f"Question: {faq.question}\nAnswer: {faq.answer}"
    embed_text = faq.question
    chunk_hash = hashlib.sha256(raw_text.encode()).hexdigest()
    return {
        "raw_text": raw_text,
        "embed_text": embed_text,
        "chunk_hash": chunk_hash,
    }
