"""API endpoints for bill tracking and alerts (Feature 7)."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    User,
    UserFollowPolitician,
    UserFollowBill,
    Alert,
    Politician,
    Bill,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============ Schemas ============

class UserCreateRequest(BaseModel):
    """Request to create or get a user."""
    email: EmailStr


class UserResponse(BaseModel):
    """User response."""
    id: str
    email: str
    notification_frequency: str
    email_verified: bool


class FollowPoliticianRequest(BaseModel):
    """Request to follow a politician."""
    politician_id: str
    notify_votes: bool = True
    notify_trades: bool = True
    notify_finance: bool = False


class FollowBillRequest(BaseModel):
    """Request to follow a bill."""
    bill_id: str
    notify_votes: bool = True
    notify_status: bool = True


class FollowResponse(BaseModel):
    """Response for follow action."""
    id: str
    created: bool
    message: str


class FollowedPoliticianResponse(BaseModel):
    """Response for followed politician."""
    id: str
    politician_id: str
    politician_name: str
    party: str | None
    state: str
    notify_votes: bool
    notify_trades: bool
    notify_finance: bool


class FollowedBillResponse(BaseModel):
    """Response for followed bill."""
    id: str
    bill_id: str
    bill_title: str
    notify_votes: bool
    notify_status: bool


class AlertResponse(BaseModel):
    """Response for alert."""
    id: str
    alert_type: str
    title: str
    message: str
    reference_type: str | None
    reference_id: str | None
    is_read: bool
    created_at: str


class UpdateNotificationRequest(BaseModel):
    """Request to update notification preferences."""
    notification_frequency: str = Field(
        ..., pattern="^(immediate|daily|weekly|none)$"
    )


# ============ User Management ============

@router.post("/users", response_model=UserResponse)
async def create_or_get_user(
    request: UserCreateRequest,
    db: Session = Depends(get_db),
):
    """Create a new user or get existing user by email."""
    existing = db.execute(
        select(User).where(User.email == request.email)
    ).scalar_one_or_none()

    if existing:
        return UserResponse(
            id=str(existing.id),
            email=existing.email,
            notification_frequency=existing.notification_frequency,
            email_verified=existing.email_verified,
        )

    user = User(email=request.email)
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse(
        id=str(user.id),
        email=user.email,
        notification_frequency=user.notification_frequency,
        email_verified=user.email_verified,
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
):
    """Get user by ID."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=str(user.id),
        email=user.email,
        notification_frequency=user.notification_frequency,
        email_verified=user.email_verified,
    )


@router.patch("/users/{user_id}/notifications")
async def update_notification_preferences(
    user_id: UUID,
    request: UpdateNotificationRequest,
    db: Session = Depends(get_db),
):
    """Update user notification preferences."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.notification_frequency = request.notification_frequency
    db.commit()

    return {"status": "updated", "notification_frequency": user.notification_frequency}


# ============ Follow Politicians ============

@router.post("/users/{user_id}/follow/politician", response_model=FollowResponse)
async def follow_politician(
    user_id: UUID,
    request: FollowPoliticianRequest,
    db: Session = Depends(get_db),
):
    """Follow a politician to get updates."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    politician_uuid = UUID(request.politician_id)
    politician = db.get(Politician, politician_uuid)
    if not politician:
        raise HTTPException(status_code=404, detail="Politician not found")

    # Check if already following
    existing = db.execute(
        select(UserFollowPolitician).where(
            UserFollowPolitician.user_id == user_id,
            UserFollowPolitician.politician_id == politician_uuid,
        )
    ).scalar_one_or_none()

    if existing:
        # Update preferences
        existing.notify_votes = request.notify_votes
        existing.notify_trades = request.notify_trades
        existing.notify_finance = request.notify_finance
        db.commit()

        return FollowResponse(
            id=str(existing.id),
            created=False,
            message=f"Updated follow preferences for {politician.full_name}",
        )

    follow = UserFollowPolitician(
        user_id=user_id,
        politician_id=politician_uuid,
        notify_votes=request.notify_votes,
        notify_trades=request.notify_trades,
        notify_finance=request.notify_finance,
    )
    db.add(follow)
    db.commit()
    db.refresh(follow)

    return FollowResponse(
        id=str(follow.id),
        created=True,
        message=f"Now following {politician.full_name}",
    )


@router.delete("/users/{user_id}/follow/politician/{politician_id}")
async def unfollow_politician(
    user_id: UUID,
    politician_id: UUID,
    db: Session = Depends(get_db),
):
    """Unfollow a politician."""
    follow = db.execute(
        select(UserFollowPolitician).where(
            UserFollowPolitician.user_id == user_id,
            UserFollowPolitician.politician_id == politician_id,
        )
    ).scalar_one_or_none()

    if not follow:
        raise HTTPException(status_code=404, detail="Not following this politician")

    db.delete(follow)
    db.commit()

    return {"status": "unfollowed", "politician_id": str(politician_id)}


@router.get("/users/{user_id}/following/politicians", response_model=list[FollowedPoliticianResponse])
async def get_followed_politicians(
    user_id: UUID,
    db: Session = Depends(get_db),
):
    """Get all politicians a user is following."""
    follows = db.execute(
        select(UserFollowPolitician).where(UserFollowPolitician.user_id == user_id)
    ).scalars().all()

    responses = []
    for f in follows:
        politician = db.get(Politician, f.politician_id)
        if politician:
            responses.append(
                FollowedPoliticianResponse(
                    id=str(f.id),
                    politician_id=str(f.politician_id),
                    politician_name=politician.full_name,
                    party=politician.party,
                    state=politician.state,
                    notify_votes=f.notify_votes,
                    notify_trades=f.notify_trades,
                    notify_finance=f.notify_finance,
                )
            )

    return responses


# ============ Follow Bills ============

@router.post("/users/{user_id}/follow/bill", response_model=FollowResponse)
async def follow_bill(
    user_id: UUID,
    request: FollowBillRequest,
    db: Session = Depends(get_db),
):
    """Follow a bill to get updates on votes and status changes."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    bill_uuid = UUID(request.bill_id)
    bill = db.get(Bill, bill_uuid)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    # Check if already following
    existing = db.execute(
        select(UserFollowBill).where(
            UserFollowBill.user_id == user_id,
            UserFollowBill.bill_id == bill_uuid,
        )
    ).scalar_one_or_none()

    if existing:
        existing.notify_votes = request.notify_votes
        existing.notify_status = request.notify_status
        db.commit()

        return FollowResponse(
            id=str(existing.id),
            created=False,
            message=f"Updated follow preferences for {bill.bill_id}",
        )

    follow = UserFollowBill(
        user_id=user_id,
        bill_id=bill_uuid,
        notify_votes=request.notify_votes,
        notify_status=request.notify_status,
    )
    db.add(follow)
    db.commit()
    db.refresh(follow)

    return FollowResponse(
        id=str(follow.id),
        created=True,
        message=f"Now following {bill.bill_id}",
    )


@router.delete("/users/{user_id}/follow/bill/{bill_id}")
async def unfollow_bill(
    user_id: UUID,
    bill_id: UUID,
    db: Session = Depends(get_db),
):
    """Unfollow a bill."""
    follow = db.execute(
        select(UserFollowBill).where(
            UserFollowBill.user_id == user_id,
            UserFollowBill.bill_id == bill_id,
        )
    ).scalar_one_or_none()

    if not follow:
        raise HTTPException(status_code=404, detail="Not following this bill")

    db.delete(follow)
    db.commit()

    return {"status": "unfollowed", "bill_id": str(bill_id)}


@router.get("/users/{user_id}/following/bills", response_model=list[FollowedBillResponse])
async def get_followed_bills(
    user_id: UUID,
    db: Session = Depends(get_db),
):
    """Get all bills a user is following."""
    follows = db.execute(
        select(UserFollowBill).where(UserFollowBill.user_id == user_id)
    ).scalars().all()

    responses = []
    for f in follows:
        bill = db.get(Bill, f.bill_id)
        if bill:
            responses.append(
                FollowedBillResponse(
                    id=str(f.id),
                    bill_id=bill.bill_id,
                    bill_title=bill.title[:100] if bill.title else bill.bill_id,
                    notify_votes=f.notify_votes,
                    notify_status=f.notify_status,
                )
            )

    return responses


# ============ Alerts ============

@router.get("/users/{user_id}/alerts", response_model=list[AlertResponse])
async def get_user_alerts(
    user_id: UUID,
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get alerts for a user."""
    query = select(Alert).where(Alert.user_id == user_id)

    if unread_only:
        query = query.where(Alert.is_read == False)

    query = query.order_by(Alert.created_at.desc()).limit(limit)
    alerts = db.execute(query).scalars().all()

    return [
        AlertResponse(
            id=str(a.id),
            alert_type=a.alert_type,
            title=a.title,
            message=a.message,
            reference_type=a.reference_type,
            reference_id=str(a.reference_id) if a.reference_id else None,
            is_read=a.is_read,
            created_at=a.created_at.isoformat(),
        )
        for a in alerts
    ]


@router.get("/users/{user_id}/alerts/count")
async def get_unread_alert_count(
    user_id: UUID,
    db: Session = Depends(get_db),
):
    """Get count of unread alerts for a user."""
    count = db.execute(
        select(func.count())
        .select_from(Alert)
        .where(Alert.user_id == user_id, Alert.is_read == False)
    ).scalar()

    return {"unread_count": count or 0}


@router.patch("/users/{user_id}/alerts/{alert_id}/read")
async def mark_alert_read(
    user_id: UUID,
    alert_id: UUID,
    db: Session = Depends(get_db),
):
    """Mark an alert as read."""
    alert = db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == user_id)
    ).scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_read = True
    db.commit()

    return {"status": "marked_read", "alert_id": str(alert_id)}


@router.patch("/users/{user_id}/alerts/read-all")
async def mark_all_alerts_read(
    user_id: UUID,
    db: Session = Depends(get_db),
):
    """Mark all alerts as read for a user."""
    result = db.execute(
        select(Alert).where(Alert.user_id == user_id, Alert.is_read == False)
    ).scalars().all()

    for alert in result:
        alert.is_read = True

    db.commit()

    return {"status": "all_marked_read", "count": len(result)}
