from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from database import get_async_session
from teams.models import Team
from teams.schemas import InvitedUserSchema
from events.utils import decrypt_registration_link
from sqlalchemy.ext.asyncio import AsyncSession
from email.message import EmailMessage
from config import REGISTATION_LINK_CIPHER_KEY, EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_HOST, EMAIL_PORT
import aiosmtplib


async def get_team(team_id: int, db: AsyncSession = Depends(get_async_session)):
    stmt = select(Team).where(Team.id == team_id).options(selectinload(Team.members))
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()

    if not team:
        raise {"msg": "Team doesn't exist"}

    return team


async def send_invite_to_team_email(registration_link: str, team_name: str, receiver: InvitedUserSchema):
    sender = EMAIL_SENDER
    email_host = EMAIL_HOST
    email_port = EMAIL_PORT
    email_password = EMAIL_PASSWORD
    message = f"Здравствуйте!\nВы были приглашены в команду - {team_name}\nСсылка на регистрацию: /api/teams/join-link/{registration_link}/"
    email = EmailMessage()
    email["From"] = sender
    email["To"] = receiver.email
    email["Subject"] = "Приглашение в команду"
    email.set_content(message)

    smtp = aiosmtplib.SMTP()
    
    await smtp.connect(hostname=email_host, port=email_port)
    await smtp.login(sender, email_password)

    await smtp.sendmail(sender, receiver.email, email.as_string())
    await smtp.quit()