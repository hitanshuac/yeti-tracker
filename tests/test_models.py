import pytest
from datetime import datetime
from uuid import UUID, uuid4

from src.models.carbon_activity import RawTransaction

def test_raw_transaction_valid():
    tx = RawTransaction(
        transaction_id=uuid4(),
        user_id="user_123",
        mcc="4111",
        amount_inr=150.50,
        timestamp=datetime.now()
    )
    assert isinstance(tx.transaction_id, UUID)
    assert tx.amount_inr == 150.50

def test_raw_transaction_negative_amount():
    with pytest.raises(ValueError):
        RawTransaction(
            transaction_id=uuid4(),
            user_id="user_123",
            mcc="4111",
            amount_inr=-50.0,
            timestamp=datetime.now()
        )
