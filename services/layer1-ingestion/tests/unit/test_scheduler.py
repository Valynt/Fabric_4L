"""Unit tests for priority queue scheduler."""

from uuid import uuid4

from layer1_ingestion.scheduler.priority_queue import PriorityScheduler, RoundRobinScheduler


class TestPriorityScheduler:
    """Test cases for PriorityScheduler."""
    
    def test_add_url(self):
        """Test adding URL to queue."""
        scheduler = PriorityScheduler(per_domain_delay=0)
        
        item = scheduler.add_url(
            job_id=str(uuid4()),
            url='https://example.com/page1',
            domain='example.com',
            depth=0,
            priority=3
        )
        
        assert item.url == 'https://example.com/page1'
        assert item.domain == 'example.com'
        assert item.priority == 3  # 0 + 0 + 3
        assert len(scheduler._queue) == 1
    
    def test_priority_ordering(self):
        """Test URLs are retrieved in priority order."""
        scheduler = PriorityScheduler(per_domain_delay=0)
        
        # Add URLs with different priorities
        scheduler.add_url(str(uuid4()), 'https://example.com/low', 'example.com', priority=5)
        scheduler.add_url(str(uuid4()), 'https://example.com/high', 'example.com', priority=1)
        scheduler.add_url(str(uuid4()), 'https://example.com/medium', 'example.com', priority=3)
        
        # Should retrieve in priority order (lowest number first)
        item1 = scheduler.get_next_url(respect_rate_limits=False)
        item2 = scheduler.get_next_url(respect_rate_limits=False)
        item3 = scheduler.get_next_url(respect_rate_limits=False)
        
        assert item1.url == 'https://example.com/high'
        assert item2.url == 'https://example.com/medium'
        assert item3.url == 'https://example.com/low'
    
    def test_depth_affects_priority(self):
        """Test that depth increases effective priority."""
        scheduler = PriorityScheduler(per_domain_delay=0)
        
        # Same priority, different depths
        scheduler.add_url(str(uuid4()), 'https://example.com/shallow', 'example.com', depth=0, priority=5)
        scheduler.add_url(str(uuid4()), 'https://example.com/deep', 'example.com', depth=2, priority=5)
        
        item1 = scheduler.get_next_url(respect_rate_limits=False)
        item2 = scheduler.get_next_url(respect_rate_limits=False)
        
        # Shallow should be first (lower effective priority)
        assert item1.depth == 0
        assert item2.depth == 2
    
    def test_rate_limiting(self):
        """Test per-domain rate limiting."""
        scheduler = PriorityScheduler(per_domain_delay=1.0)
        
        scheduler.add_url(str(uuid4()), 'https://example.com/page1', 'example.com')
        scheduler.add_url(str(uuid4()), 'https://example.com/page2', 'example.com')
        
        # First request should work
        item1 = scheduler.get_next_url(respect_rate_limits=True)
        assert item1 is not None
        
        # Second request should be rate limited (within 1 second)
        item2 = scheduler.get_next_url(respect_rate_limits=True)
        assert item2 is None
    
    def test_get_queue_stats(self):
        """Test queue statistics."""
        scheduler = PriorityScheduler(per_domain_delay=0)
        
        scheduler.add_url(str(uuid4()), 'https://example.com/1', 'example.com')
        scheduler.add_url(str(uuid4()), 'https://example.com/2', 'example.com')
        scheduler.add_url(str(uuid4()), 'https://other.com/1', 'other.com')
        
        stats = scheduler.get_queue_stats()
        
        assert stats['total_pending'] == 3
        assert stats['domains_pending'] == 2
        assert 'example.com' in stats['top_domains']


class TestRoundRobinScheduler:
    """Test cases for RoundRobinScheduler."""
    
    def test_round_robin_selection(self):
        """Test round-robin domain selection."""
        scheduler = RoundRobinScheduler(per_domain_delay=0)
        
        # Add URLs from different domains
        scheduler.add_url(str(uuid4()), 'https://domain-a.com/1', 'domain-a.com')
        scheduler.add_url(str(uuid4()), 'https://domain-a.com/2', 'domain-a.com')
        scheduler.add_url(str(uuid4()), 'https://domain-b.com/1', 'domain-b.com')
        
        # Should alternate between domains
        item1 = scheduler.get_next_url(respect_rate_limits=False)
        item2 = scheduler.get_next_url(respect_rate_limits=False)
        item3 = scheduler.get_next_url(respect_rate_limits=False)
        
        # First two should be different domains
        assert item1.domain != item2.domain
        assert item3.domain in ['domain-a.com', 'domain-b.com']

