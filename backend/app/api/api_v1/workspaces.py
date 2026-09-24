import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.activity import Activity
from app.core.security import hash_password
from app.core.auth import (
    get_current_user,
    get_current_workspace,
    WorkspaceContext,
    ROLE_ADMIN,
    ALL_ROLES,
    ROLE_PERMISSIONS
)
from app.schemas.workspace import (
    WorkspaceResponse,
    WorkspaceMemberResponse,
    AddWorkspaceMemberRequest,
    UpdateWorkspaceMemberRequest
)

logger = logging.getLogger("devforge.api.workspaces")

router = APIRouter()


@router.get("", response_model=List[WorkspaceResponse])
def list_workspaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List workspaces where the authenticated user is an active member.
    """
    memberships = db.query(WorkspaceMember).filter(
        WorkspaceMember.user_id == current_user.id,
        WorkspaceMember.status == "active"
    ).all()

    results = []
    for m in memberships:
        ws = m.workspace
        if ws and ws.status == "active":
            resp = WorkspaceResponse(
                id=ws.id,
                name=ws.name,
                slug=ws.slug,
                description=ws.description,
                status=ws.status,
                created_at=ws.created_at.isoformat() if ws.created_at else None,
                updated_at=ws.updated_at.isoformat() if ws.updated_at else None,
                current_user_role=m.role,
                member_count=len(ws.members) if ws.members else 0,
                application_count=len(ws.applications) if ws.applications else 0
            )
            results.append(resp)
    return results


@router.get("/current", response_model=WorkspaceResponse)
def get_current_workspace_details(
    ws_ctx: WorkspaceContext = Depends(get_current_workspace)
):
    """
    Return the active workspace context and authenticated user's authoritative role.
    """
    ws = ws_ctx.workspace
    return WorkspaceResponse(
        id=ws.id,
        name=ws.name,
        slug=ws.slug,
        description=ws.description,
        status=ws.status,
        created_at=ws.created_at.isoformat() if ws.created_at else None,
        updated_at=ws.updated_at.isoformat() if ws.updated_at else None,
        current_user_role=ws_ctx.role,
        member_count=len(ws.members) if ws.members else 0,
        application_count=len(ws.applications) if ws.applications else 0
    )


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve workspace details. User must be an active member of the workspace.
    """
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == current_user.id,
        WorkspaceMember.status == "active"
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: You do not have permission to access workspace ID {workspace_id}."
        )

    ws = member.workspace
    return WorkspaceResponse(
        id=ws.id,
        name=ws.name,
        slug=ws.slug,
        description=ws.description,
        status=ws.status,
        created_at=ws.created_at.isoformat() if ws.created_at else None,
        updated_at=ws.updated_at.isoformat() if ws.updated_at else None,
        current_user_role=member.role,
        member_count=len(ws.members) if ws.members else 0,
        application_count=len(ws.applications) if ws.applications else 0
    )


@router.get("/{workspace_id}/members", response_model=List[WorkspaceMemberResponse])
def list_workspace_members(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all members in the workspace. Requester must be a member of the workspace.
    """
    caller_member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == current_user.id,
        WorkspaceMember.status == "active"
    ).first()

    if not caller_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: You are not a member of workspace ID {workspace_id}."
        )

    members = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id
    ).order_by(WorkspaceMember.id.asc()).all()

    return [
        WorkspaceMemberResponse(
            id=m.id,
            workspace_id=m.workspace_id,
            user_id=m.user_id,
            username=m.user.username if m.user else None,
            email=m.user.email if m.user else None,
            display_name=getattr(m.user, "display_name", None) or (m.user.username if m.user else None),
            role=m.role,
            status=m.status,
            created_at=m.created_at.isoformat() if m.created_at else None,
            updated_at=m.updated_at.isoformat() if m.updated_at else None
        )
        for m in members
    ]


@router.post("/{workspace_id}/members", response_model=WorkspaceMemberResponse, status_code=status.HTTP_201_CREATED)
def add_workspace_member(
    workspace_id: int,
    payload: AddWorkspaceMemberRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add or invite a member to the workspace.
    Only authorized ADMINs of the workspace may add members.
    """
    # Verify caller is ADMIN in this workspace
    caller_member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == current_user.id,
        WorkspaceMember.status == "active"
    ).first()

    if not caller_member or caller_member.role.upper() != ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only workspace administrators can add or invite members."
        )

    target_role = payload.role.strip().upper()
    if target_role not in ALL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{payload.role}'. Must be one of: {ALL_ROLES}"
        )

    clean_email = payload.email.strip().lower()
    if not clean_email or "@" not in clean_email or "." not in clean_email.split("@")[-1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid email address is required."
        )

    # Password validation if provided
    initial_password = payload.password
    if initial_password:
        if payload.confirm_password and initial_password != payload.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords do not match."
            )
        if len(initial_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long."
            )
    else:
        initial_password = "DevForgeUser2026!"

    # Resolve target user
    target_user = db.query(User).filter(User.email.ilike(clean_email)).first()
    if not target_user and payload.username:
        target_user = db.query(User).filter(User.username.ilike(payload.username.strip())).first()

    if not target_user:
        username = (payload.username or clean_email.split("@")[0]).strip()
        username = "".join(c for c in username if c.isalnum() or c in ("-", "_"))[:40] or "user"
        counter = 1
        base_u = username
        while db.query(User).filter(User.username == username).first():
            username = f"{base_u[:35]}_{counter}"
            counter += 1

        display_name = (payload.name or username).strip()
        target_user = User(
            username=username,
            email=clean_email,
            display_name=display_name,
            hashed_password=hash_password(initial_password),
            role=target_role,
            is_active=True,
            status="active"
        )
        db.add(target_user)
        db.commit()
        db.refresh(target_user)

    # Check if membership already exists
    existing_member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == target_user.id
    ).first()

    if existing_member:
        if existing_member.status == "disabled":
            existing_member.status = "active"
            existing_member.role = target_role
            db.commit()
            db.refresh(existing_member)
            return WorkspaceMemberResponse(
                id=existing_member.id,
                workspace_id=existing_member.workspace_id,
                user_id=existing_member.user_id,
                username=target_user.username,
                email=target_user.email,
                display_name=target_user.display_name or target_user.username,
                role=existing_member.role,
                status=existing_member.status,
                created_at=existing_member.created_at.isoformat() if existing_member.created_at else None,
                updated_at=existing_member.updated_at.isoformat() if existing_member.updated_at else None
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User '{target_user.username}' is already a member of this workspace."
        )

    new_member = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=target_user.id,
        role=target_role,
        status="active"
    )
    db.add(new_member)
    db.commit()
    db.refresh(new_member)

    # Audit member added
    try:
        ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        act = Activity(
            actor=current_user.username,
            action="Member added to workspace",
            target=target_user.username,
            target_type="workspace_membership",
            status="completed",
            details=f"User '{target_user.username}' added to workspace '{ws.slug if ws else workspace_id}' with role '{target_role}'"
        )
        db.add(act)
        db.commit()
    except Exception as e:
        logger.warning(f"Could not record member addition audit: {e}")
        db.rollback()

    return WorkspaceMemberResponse(
        id=new_member.id,
        workspace_id=new_member.workspace_id,
        user_id=new_member.user_id,
        username=target_user.username,
        email=target_user.email,
        display_name=target_user.display_name or target_user.username,
        role=new_member.role,
        status=new_member.status,
        created_at=new_member.created_at.isoformat() if new_member.created_at else None,
        updated_at=new_member.updated_at.isoformat() if new_member.updated_at else None
    )


@router.patch("/{workspace_id}/members/{member_id}", response_model=WorkspaceMemberResponse)
def update_workspace_member(
    workspace_id: int,
    member_id: int,
    payload: UpdateWorkspaceMemberRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a workspace member's role or status.
    Only authorized ADMINs of the workspace may change roles.
    Users cannot elevate or change their own role.
    """
    # Verify caller is ADMIN in this workspace
    caller_member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == current_user.id,
        WorkspaceMember.status == "active"
    ).first()

    if not caller_member or caller_member.role.upper() != ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only workspace administrators can modify member roles."
        )

    target_member = db.query(WorkspaceMember).filter(
        WorkspaceMember.id == member_id,
        WorkspaceMember.workspace_id == workspace_id
    ).first()

    if not target_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace member with ID {member_id} not found."
        )

    # Prevent self-promotion or self-demotion
    if target_member.user_id == current_user.id and payload.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-service role modification is forbidden. Contact another workspace administrator."
        )

    old_role = target_member.role
    if payload.role:
        new_role = payload.role.strip().upper()
        if new_role not in ALL_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role '{payload.role}'. Must be one of: {ALL_ROLES}"
            )
        # Protect against demoting the final remaining ADMIN
        if target_member.role == ROLE_ADMIN and new_role != ROLE_ADMIN:
            active_admins = db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.role == ROLE_ADMIN,
                WorkspaceMember.status == "active"
            ).count()
            if active_admins <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot demote the final remaining workspace administrator."
                )
        target_member.role = new_role

    if payload.status:
        st = payload.status.strip().lower()
        if st not in ("active", "disabled"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status must be 'active' or 'disabled'")
        if target_member.role == ROLE_ADMIN and st == "disabled":
            active_admins = db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.role == ROLE_ADMIN,
                WorkspaceMember.status == "active"
            ).count()
            if active_admins <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot disable the final remaining workspace administrator."
                )
        target_member.status = st

    db.commit()
    db.refresh(target_member)

    # Audit role change
    try:
        ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        act = Activity(
            actor=current_user.username,
            action="Workspace member role updated",
            target=target_member.user.username if target_member.user else f"user_{target_member.user_id}",
            target_type="workspace_membership",
            status="completed",
            details=f"Member '{target_member.user.username if target_member.user else target_member.user_id}' role changed from '{old_role}' to '{target_member.role}' in workspace '{ws.slug if ws else workspace_id}'"
        )
        db.add(act)
        db.commit()
    except Exception as e:
        logger.warning(f"Could not record member role update audit: {e}")
        db.rollback()

    return WorkspaceMemberResponse(
        id=target_member.id,
        workspace_id=target_member.workspace_id,
        user_id=target_member.user_id,
        username=target_member.user.username if target_member.user else None,
        email=target_member.user.email if target_member.user else None,
        display_name=getattr(target_member.user, "display_name", None) or (target_member.user.username if target_member.user else None),
        role=target_member.role,
        status=target_member.status,
        created_at=target_member.created_at.isoformat() if target_member.created_at else None,
        updated_at=target_member.updated_at.isoformat() if target_member.updated_at else None
    )


@router.delete("/{workspace_id}/members/{member_id}")
def remove_or_disable_workspace_member(
    workspace_id: int,
    member_id: int,
    permanent: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Disable or remove a member from the workspace. Requires workspace ADMIN.
    Protects against deleting or disabling the final remaining administrator.
    """
    caller_member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == current_user.id,
        WorkspaceMember.status == "active"
    ).first()

    if not caller_member or caller_member.role.upper() != ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only workspace administrators can remove or disable members."
        )

    target_member = db.query(WorkspaceMember).filter(
        WorkspaceMember.id == member_id,
        WorkspaceMember.workspace_id == workspace_id
    ).first()

    if not target_member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")

    # Protect against removing/disabling the final remaining ADMIN
    if target_member.role == ROLE_ADMIN and target_member.status == "active":
        active_admins = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.role == ROLE_ADMIN,
            WorkspaceMember.status == "active"
        ).count()
        if active_admins <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete or disable the final remaining workspace administrator."
            )

    if permanent:
        db.delete(target_member)
    else:
        target_member.status = "disabled"
    db.commit()

    # Audit member disabled
    try:
        ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        act = Activity(
            actor=current_user.username,
            action="Workspace member disabled",
            target=target_member.user.username if target_member.user else f"user_{target_member.user_id}",
            target_type="workspace_membership",
            status="completed",
            details=f"Member '{target_member.user.username if target_member.user else target_member.user_id}' disabled in workspace '{ws.slug if ws else workspace_id}'"
        )
        db.add(act)
        db.commit()
    except Exception as e:
        logger.warning(f"Could not record member disable audit: {e}")
        db.rollback()

    return {"status": "success", "message": "Member disabled successfully."}
