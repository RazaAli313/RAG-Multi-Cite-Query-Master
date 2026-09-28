import logging

from celery import shared_task

from querymaster.core.services.ingestion import ingest_chunk
from querymaster.faqs.choices import IngestionStatus
from querymaster.faqs.models import FAQ
from querymaster.faqs.services.chunking import build_faq_chunk

logger = logging.getLogger(__name__)


@shared_task
def ingest_faq(faq_id: int) -> None:
    faq = FAQ.objects.get(id=faq_id)

    try:
        chunk_data = build_faq_chunk(faq)
        ingest_chunk(
            source_instance=faq,
            raw_text=chunk_data["raw_text"],
            chunk_hash=chunk_data["chunk_hash"],
        )
        faq.ingestion_status = IngestionStatus.SUCCESS
        faq.save(update_fields=["ingestion_status"])

    except Exception as exception:
        logger.exception("FAQ ingestion failed for faq_id=%s: %s", faq_id, exception)
        faq.ingestion_status = IngestionStatus.FAILED
        faq.save(update_fields=["ingestion_status"])
