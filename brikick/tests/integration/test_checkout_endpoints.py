import pytest


@pytest.mark.asyncio
async def test_checkout_endpoints_not_implemented():
    pytest.skip("Checkout endpoints require full order flow setup.")
