from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("knowledge", "0002_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE INDEX ON knowledge_chunk USING hnsw (embedding vector_cosine_ops);",
            reverse_sql="DROP INDEX IF EXISTS knowledge_chunk_embedding_idx;",
        ),
    ]
