"""Re-ingest all knowledge base sources into ChromaDB.

Fixes knowledge bases that were ingested while _split_text() had a missing
return statement, resulting in 0 chunks in ChromaDB despite sources showing
as "ready" in MongoDB.

Sources with stored content are re-chunked directly (no re-fetch).
Sources without stored content are re-fetched from their URLs.

Usage:
    cd backend
    python -m scripts.reingest_knowledge_bases
"""

import asyncio
import logging

from app.database import init_db
from app.models.knowledge import KnowledgeBase, KnowledgeBaseSource
from app.services.document_manager import DocumentManager
from app.services.knowledge_service import (
    _ingest_url_source,
    recalculate_stats,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    await init_db()
    dm = DocumentManager()

    kbs = await KnowledgeBase.find_all().to_list()
    logger.info("Found %d knowledge bases", len(kbs))

    total_rechunked = 0
    total_refetched = 0
    total_failed = 0

    for kb in kbs:
        sources = await KnowledgeBaseSource.find(
            KnowledgeBaseSource.knowledge_base_uuid == kb.uuid,
        ).to_list()

        if not sources:
            continue

        kb_chunks_before = kb.total_chunks
        logger.info("KB %r (%s): %d sources, %d chunks recorded",
                     kb.title, kb.uuid[:8], len(sources), kb.total_chunks)

        for src in sources:
            # Case 1: source has stored content — re-chunk without re-fetching
            if src.content and src.content.strip():
                chunk_count = dm.add_to_kb(
                    kb.uuid, src.uuid,
                    src.url_title or src.url or src.uuid,
                    src.content,
                )
                src.chunk_count = chunk_count
                src.status = "ready"
                src.error_message = None
                await src.save()
                if chunk_count > 0:
                    total_rechunked += 1
                    logger.info("  Re-chunked %s: %d chunks (from stored content)",
                                src.url_title or src.url or src.uuid, chunk_count)
                else:
                    total_failed += 1
                    logger.warning("  Re-chunk produced 0 chunks for %s",
                                   src.url_title or src.url or src.uuid)

            # Case 2: URL source without stored content — re-fetch
            elif src.source_type == "url" and src.url:
                try:
                    await _ingest_url_source(src, kb)
                    total_refetched += 1
                    logger.info("  Re-fetched %s: %d chunks",
                                src.url or src.uuid, src.chunk_count)
                except Exception as e:
                    total_failed += 1
                    logger.warning("  Failed to re-fetch %s: %s", src.url, e)

            else:
                logger.warning("  Skipped source %s: no content and not a URL", src.uuid)
                total_failed += 1

        await recalculate_stats(kb)
        await kb.reload()
        logger.info("  KB %r: %d → %d chunks", kb.title, kb_chunks_before, kb.total_chunks)

    logger.info("Done. Re-chunked: %d, Re-fetched: %d, Failed: %d",
                total_rechunked, total_refetched, total_failed)


if __name__ == "__main__":
    asyncio.run(main())
