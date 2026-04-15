"""
Reminders Endpoints
====================
POST /reminders/           – Set a deadline reminder
GET  /reminders/           – List user's reminders
DELETE /reminders/{id}     – Cancel a reminder
POST /reminders/cron/send  – Cron job: send due reminders (admin only)
"""
from datetime import datetime, timedelta, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user, require_admin
from app.db.session import get_db
from app.models.models import Reminder, Scholarship
from app.schemas.reminder import CreateReminderRequest, ReminderResponse

router = APIRouter()


@router.post("/", response_model=ReminderResponse, status_code=201)
async def create_reminder(
    body: CreateReminderRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Set a deadline reminder for a scholarship."""
    # Verify scholarship exists
    scholarship = await db.get(Scholarship, body.scholarship_id)
    if not scholarship:
        raise HTTPException(status_code=404, detail="Scholarship not found.")

    # Calculate remind_at date
    if scholarship.deadline:
        remind_at = scholarship.deadline - timedelta(days=body.remind_days_before)
        if remind_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=400,
                detail=f"Reminder date has already passed. Deadline: {scholarship.deadline.date()}"
            )
    else:
        remind_at = datetime.now(timezone.utc) + timedelta(days=7)

    reminder = Reminder(
        user_id=current_user.id,
        scholarship_id=body.scholarship_id,
        remind_at=remind_at,
        remind_days_before=body.remind_days_before,
        channel=body.channel,
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return ReminderResponse.model_validate(reminder)


@router.get("/", response_model=List[ReminderResponse])
async def list_reminders(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all active reminders for the current user."""
    result = await db.execute(
        select(Reminder)
        .where(Reminder.user_id == current_user.id, Reminder.is_sent == False)
        .order_by(Reminder.remind_at.asc())
    )
    return [ReminderResponse.model_validate(r) for r in result.scalars().all()]


@router.delete("/{reminder_id}", status_code=204)
async def delete_reminder(
    reminder_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Cancel a reminder."""
    reminder = await db.get(Reminder, reminder_id)
    if not reminder or reminder.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Reminder not found.")
    await db.delete(reminder)
    await db.commit()


@router.post("/cron/send", tags=["Admin"])
async def send_due_reminders(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """
    Simulated cron job: processes and marks due reminders as sent.
    In production, call this via a scheduled task (APScheduler/Celery).
    """
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Reminder).where(
            Reminder.remind_at <= now,
            Reminder.is_sent == False,
        )
    )
    due_reminders = result.scalars().all()
    sent_count = 0

    for reminder in due_reminders:
        # In production: send email/SMS/push notification here
        reminder.is_sent = True
        reminder.sent_at = now
        sent_count += 1

    await db.commit()
    return {"message": f"Processed {sent_count} reminders.", "sent_count": sent_count}
