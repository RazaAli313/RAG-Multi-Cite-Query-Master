import hashlib

from django.contrib import admin
from django.utils import timezone

from querymaster.faqs.choices import IngestionStatus
from querymaster.faqs.models import FAQ
from querymaster.faqs.tasks import ingest_faq


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):

    list_display = ["question", "ingestion_status", "content_updated_at", "created"]
    readonly_fields = ["content_hash", "content_updated_at", "ingestion_status", "created", "modified"]

    def save_model(self, request, faq, form, change):
        new_hash = hashlib.sha256(f"{faq.question}{faq.answer}".encode()).hexdigest()
        content_changed = new_hash != faq.content_hash

        if content_changed:
            faq.content_hash = new_hash
            faq.content_updated_at = timezone.now()
            faq.ingestion_status = IngestionStatus.PROCESSING

        super().save_model(request, faq, form, change)

        if content_changed:
            ingest_faq.delay(faq.id)
