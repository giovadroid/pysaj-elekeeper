import pytest

from pysaj import SajAuthError, SajClient


@pytest.mark.asyncio
async def test_authenticated_call_requires_login():
    async with SajClient() as client:
        with pytest.raises(SajAuthError):
            await client.get_login_info()
