import os
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.models import ApprovalAction, ApprovalDecision, AuditLog, Expense, ExpenseStatus, User

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = f"postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}@localhost:5432/{os.environ['POSTGRES_DB']}"
engine = create_engine(DATABASE_URL)


def get_db():
    with Session(engine) as session:
        yield session


def log_action(db: Session, user_id: str, expense_id: uuid.UUID, action: str, before: dict | None, after: dict | None):
    entry = AuditLog(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        expense_id=expense_id,
        action=action,
        before_state=before,
        after_state=after,
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ExpenseCreate(BaseModel):
    amount: float
    currency: str
    category: str
    description: str | None = None


class ExpenseOut(BaseModel):
    id: uuid.UUID
    amount: float
    currency: str
    category: str
    description: str | None
    status: str

    class Config:
        from_attributes = True


class ApprovalRequest(BaseModel):
    decision: str
    comment: str | None = None


@app.get("/health")
def health_check():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


@app.post("/login", response_model=LoginResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(
        select(User).where(User.email == credentials.email)
    ).scalar_one_or_none()

    if user is None or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user_id=str(user.id), role=user.role.value)
    return LoginResponse(access_token=token)


@app.get("/me")
def read_current_user(current_user: dict = Depends(get_current_user)):
    return current_user


@app.post("/expenses", response_model=ExpenseOut)
def create_expense(
    expense_data: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    expense = Expense(
        id=uuid.uuid4(),
        user_id=uuid.UUID(current_user["id"]),
        amount=expense_data.amount,
        currency=expense_data.currency,
        category=expense_data.category,
        description=expense_data.description,
        status=ExpenseStatus.draft,
    )
    db.add(expense)

    log_action(
        db,
        user_id=current_user["id"],
        expense_id=expense.id,
        action="expense_created",
        before=None,
        after={"amount": expense_data.amount, "status": "draft"},
    )

    db.commit()
    db.refresh(expense)

    return expense


@app.get("/expenses/pending", response_model=list[ExpenseOut])
def list_pending_expenses(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] not in ("approver", "admin"):
        raise HTTPException(status_code=403, detail="Only approvers or admins can view the queue")

    expenses = db.execute(
        select(Expense).where(Expense.status == ExpenseStatus.submitted, Expense.deleted_at.is_(None))
    ).scalars().all()
    return expenses


@app.post("/expenses/{expense_id}/submit", response_model=ExpenseOut)
def submit_expense(
    expense_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    expense = db.get(Expense, expense_id)

    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")

    if str(expense.user_id) != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your expense")

    if expense.status != ExpenseStatus.draft:
        raise HTTPException(status_code=400, detail=f"Cannot submit an expense with status '{expense.status.value}'")

    before_status = expense.status.value
    expense.status = ExpenseStatus.submitted

    log_action(
        db,
        user_id=current_user["id"],
        expense_id=expense.id,
        action="expense_submitted",
        before={"status": before_status},
        after={"status": "submitted"},
    )

    db.commit()
    db.refresh(expense)

    return expense


@app.post("/expenses/{expense_id}/approve", response_model=ExpenseOut)
def approve_or_reject_expense(
    expense_id: uuid.UUID,
    approval_data: ApprovalRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] not in ("approver", "admin"):
        raise HTTPException(status_code=403, detail="Only approvers or admins can act on expenses")

    expense = db.get(Expense, expense_id)
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")

    if expense.status != ExpenseStatus.submitted:
        raise HTTPException(status_code=400, detail=f"Cannot act on an expense with status '{expense.status.value}'")

    if str(expense.user_id) == current_user["id"]:
        raise HTTPException(status_code=403, detail="You cannot approve or reject your own expense")

    approver = db.get(User, uuid.UUID(current_user["id"]))

    if approval_data.decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="decision must be 'approved' or 'rejected'")

    if approval_data.decision == "approved" and approver.role.value == "approver":
        if approver.approval_limit is None or expense.amount > approver.approval_limit:
            raise HTTPException(
                status_code=403,
                detail=f"Expense amount {expense.amount} exceeds your approval limit",
            )

    before_status = expense.status.value
    expense.status = ExpenseStatus.approved if approval_data.decision == "approved" else ExpenseStatus.rejected

    action = ApprovalAction(
        id=uuid.uuid4(),
        expense_id=expense.id,
        approver_id=approver.id,
        decision=ApprovalDecision(approval_data.decision),
        comment=approval_data.comment,
        created_at=datetime.now(timezone.utc),
    )
    db.add(action)

    log_action(
        db,
        user_id=current_user["id"],
        expense_id=expense.id,
        action=f"expense_{approval_data.decision}",
        before={"status": before_status},
        after={"status": expense.status.value, "comment": approval_data.comment},
    )

    db.commit()
    db.refresh(expense)

    return expense


@app.delete("/expenses/{expense_id}")
def delete_expense(
    expense_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    expense = db.get(Expense, expense_id)

    if expense is None or expense.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Expense not found")

    if str(expense.user_id) != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this expense")

    expense.deleted_at = datetime.now(timezone.utc)

    log_action(
        db,
        user_id=current_user["id"],
        expense_id=expense.id,
        action="expense_deleted",
        before={"deleted_at": None},
        after={"deleted_at": expense.deleted_at.isoformat()},
    )

    db.commit()
    return {"status": "deleted", "id": str(expense.id)}