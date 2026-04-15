import pytest
from datetime import datetime, timezone
from models import ConversationMessage


@pytest.mark.asyncio
async def test_save_and_load_conversation(db):
    from sqlalchemy import select

    db.add(ConversationMessage(user_phone="5511999", role="user", content="oi"))
    db.add(ConversationMessage(user_phone="5511999", role="model", content="olá!"))
    await db.commit()

    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.user_phone == "5511999")
        .order_by(ConversationMessage.created_at)
    )
    msgs = list(result.scalars().all())

    assert len(msgs) == 2
    assert msgs[0].role == "user"
    assert msgs[0].content == "oi"
    assert msgs[1].role == "model"
    assert msgs[1].content == "olá!"
    assert msgs[0].created_at is not None


@pytest.mark.asyncio
async def test_conversation_isolated_by_phone(db):
    from sqlalchemy import select

    db.add(ConversationMessage(user_phone="phone_a", role="user", content="msg a"))
    db.add(ConversationMessage(user_phone="phone_b", role="user", content="msg b"))
    await db.commit()

    result = await db.execute(
        select(ConversationMessage).where(ConversationMessage.user_phone == "phone_a")
    )
    msgs = list(result.scalars().all())
    assert len(msgs) == 1
    assert msgs[0].content == "msg a"
