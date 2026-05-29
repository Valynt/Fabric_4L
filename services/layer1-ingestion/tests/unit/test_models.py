"""Unit tests for shared models."""

from uuid import UUID, uuid4

from layer1_ingestion.shared.models import (
    CrawlQueueItem,
    JobStatus,
    RawContent,
    SourceCategory,
    TargetType,
    create_scraping_job,
    create_scraping_target,
)


class TestScrapingJob:
    """Test cases for ScrapingJob model."""
    
    def test_create_scraping_job(self):
        """Test creating a scraping job."""
        org_id = uuid4()
        target_id = uuid4()
        created_by = uuid4()
        
        job = create_scraping_job(
            tenant_id=org_id,
            target_id=target_id,
            created_by=created_by,
            configuration={'url': 'https://example.com'}
        )
        
        assert job.target_id == target_id
        assert job.tenant_id == org_id
        assert job.configuration['url'] == 'https://example.com'
    
    def test_job_status_enum(self):
        """Test job status enumeration."""
        assert JobStatus.PENDING.value == 'PENDING'
        assert JobStatus.QUEUED.value == 'QUEUED'
        assert JobStatus.COMPLETED.value == 'COMPLETED'
        assert JobStatus.FAILED.value == 'FAILED'


class TestScrapingTarget:
    """Test cases for ScrapingTarget model."""
    
    def test_create_scraping_target(self):
        """Test creating a scraping target."""
        org_id = uuid4()
        created_by = uuid4()
        
        target = create_scraping_target(
            tenant_id=org_id,
            name='Test Target',
            url='https://example.com',
            target_type=TargetType.SINGLE_PAGE,
            created_by=created_by,
            description='Test description'
        )
        
        assert target.name == 'Test Target'
        assert target.url == 'https://example.com'
        assert target.target_type == TargetType.SINGLE_PAGE.value
        assert target.source_category is None

    def test_create_scraping_target_with_source_category(self):
        """Test creating a scraping target with source_category."""
        org_id = uuid4()
        created_by = uuid4()
        
        target = create_scraping_target(
            tenant_id=org_id,
            name='CRM Target',
            url='https://salesforce.com',
            target_type=TargetType.API_ENDPOINT,
            source_category=SourceCategory.CRM,
            created_by=created_by,
        )
        
        assert target.target_type == TargetType.API_ENDPOINT.value
        assert target.source_category == SourceCategory.CRM.value


class TestCrawlQueueItem:
    """Test cases for CrawlQueueItem model."""
    
    def test_create_queue_item(self):
        """Test creating a queue item."""
        
        job_id = UUID('12345678-1234-1234-1234-123456789abc')
        org_id = UUID('12345678-1234-1234-1234-123456789abc')
        
        item = CrawlQueueItem(
            job_id=job_id,
            tenant_id=org_id,
            url='https://example.com/page',
            domain='example.com',
            depth=1,
            priority=3,
            parent_url='https://example.com'
        )
        
        assert item.job_id == job_id
        assert item.url == 'https://example.com/page'
        assert item.domain == 'example.com'
        assert item.depth == 1
        assert item.priority == 3
        assert item.parent_url == 'https://example.com'


class TestRawContent:
    """Test cases for RawContent model."""
    
    def test_content_creation(self):
        """Test creating raw content."""
        
        job_id = UUID('12345678-1234-1234-1234-123456789abc')
        org_id = UUID('12345678-1234-1234-1234-123456789abc')
        
        content = RawContent(
            job_id=job_id,
            tenant_id=org_id,
            source_url='https://example.com/page',
            source_domain='example.com',
            source_http_status=200,
            content_hash='abc123'
        )
        
        assert content.source_url == 'https://example.com/page'
        assert content.source_domain == 'example.com'
        assert content.source_http_status == 200
        assert content.content_hash == 'abc123'

