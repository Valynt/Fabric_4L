from layer3_knowledge.rate_limiting.manager import RateLimitStore
from layer3_knowledge.rate_limiting.types import LeakyBucketState, TokenBucketState


def test_bucket_state_typed_dict_shapes() -> None:
    token_state: TokenBucketState = {
        "tokens": 5.0,
        "last_refill": 1.0,
        "created_at": 1.0,
    }
    leaky_state: LeakyBucketState = {
        "queue_size": 3,
        "last_leak": 2.0,
        "created_at": 1.0,
    }

    assert token_state["tokens"] == 5.0
    assert leaky_state["queue_size"] == 3


def test_rate_limit_store_annotation_is_typed() -> None:
    hints = RateLimitStore.get_bucket_state.__annotations__
    assert "return" in hints
    assert "BucketState" in str(hints["return"])
