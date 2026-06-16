"""Tests for Document and Chunk schemas."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.schemas.document import Chunk, Document


class TestDocument:
    """Document 스키마 테스트."""

    def test_document_valid(self):
        """Document 정상 생성."""
        source_id = uuid4()
        doc = Document(
            source_id=source_id,
            source_type="notice",
            source_table="cms_board",
            site_code="ROYAL",
            title="공지사항 제목",
            content="공지사항 내용입니다.",
            created_at=datetime.now(),
        )
        assert doc.source_id == source_id
        assert isinstance(doc.source_id, UUID)
        assert doc.source_type == "notice"
        assert doc.site_code == "ROYAL"
        assert doc.index_status == "pending"
        assert doc.content_hash is not None

    def test_invalid_source_type(self):
        """잘못된 source_type → ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            Document(
                source_id=uuid4(),
                source_type="invalid_type",
                source_table="unknown_table",
                site_code="ROYAL",
                title="제목",
                content="내용",
            )
        assert "source_type" in str(exc_info.value)

    def test_missing_content(self):
        """content 누락 → ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Document(
                source_id=uuid4(),
                source_type="notice",
                source_table="cms_board",
                site_code="ROYAL",
                title="제목만 있음",
                # content 필드 누락
            )
        assert "content" in str(exc_info.value)

    def test_extra_field_forbidden(self):
        """추가 필드 → ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Document(
                source_id=uuid4(),
                source_type="notice",
                source_table="cms_board",
                site_code="ROYAL",
                title="제목",
                content="내용",
                invalid_field="should not be allowed",  # type: ignore
            )
        assert "extra_forbidden" in str(exc_info.value)

    def test_content_hash_auto_generated(self):
        """content_hash 자동 생성 확인."""
        content = "테스트 콘텐츠"
        doc = Document(
            source_id=uuid4(),
            source_type="notice",
            source_table="cms_board",
            site_code="ROYAL",
            title="해시 테스트",
            content=content,
        )
        assert doc.content_hash is not None
        assert isinstance(doc.content_hash, str)
        assert len(doc.content_hash) == 32  # MD5 해시 길이

    def test_index_status_default(self):
        """index_status 기본값 "pending" 확인."""
        doc = Document(
            source_id=uuid4(),
            source_type="page_content",
            source_table="cms_menu_contents",
            site_code="ROYAL",
            title="메뉴 페이지",
            content="페이지 내용",
        )
        assert doc.index_status == "pending"

    def test_invalid_index_status(self):
        """잘못된 index_status → ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Document(
                source_id=uuid4(),
                source_type="notice",
                source_table="cms_board",
                site_code="ROYAL",
                title="제목",
                content="내용",
                index_status="unknown",  # type: ignore
            )
        assert "index_status" in str(exc_info.value)


class TestChunk:
    """Chunk 스키마 테스트."""

    def test_chunk_valid(self):
        """Chunk 정상 생성."""
        chunk_id = uuid4()
        source_id = uuid4()
        chunk = Chunk(
            chunk_id=chunk_id,
            source_id=source_id,
            source_type="notice",
            source_table="cms_board",
            site_code="ROYAL",
            title="공지사항 제목",
            content="첫 번째 텍스트 조각",
            chunk_index=0,
        )
        assert chunk.chunk_id == chunk_id
        assert isinstance(chunk.chunk_id, UUID)
        assert chunk.source_id == source_id
        assert isinstance(chunk.source_id, UUID)
        assert chunk.chunk_index == 0
        assert chunk.index_status == "pending"
        assert chunk.content_hash is not None

    def test_chunk_index_status_default(self):
        """Chunk index_status 기본값 확인."""
        chunk = Chunk(
            chunk_id=uuid4(),
            source_id=uuid4(),
            source_type="notice",
            source_table="cms_board",
            site_code="ROYAL",
            title="공지사항",
            content="청크 내용",
            chunk_index=0,
        )
        assert chunk.index_status == "pending"
        assert chunk.indexed_at is None
        assert chunk.content_hash is not None
