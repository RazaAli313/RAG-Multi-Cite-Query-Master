from django.contrib import admin

from querymaster.knowledge.models import Chunk


@admin.register(Chunk)
class ChunkAdmin(admin.ModelAdmin):

    list_display = ["id", "content_type", "object_id", "chunk_hash", "is_active", "position"]
    readonly_fields = ["content_type", "object_id", "source", "raw_text", "chunk_hash", "embedding", "is_active", "position"]
