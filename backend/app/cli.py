"""Tiny CLI for development tasks.

Usage::

    python -m app.cli init-db
    python -m app.cli create-project --name "Demo"
    python -m app.cli create-key --project-id <id> [--label local-dev]

The plaintext API key is printed once on creation; it can never be
retrieved again.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
from datetime import datetime, timezone

from app.core.config import settings
from app.db.models import AdminUser, Project
from app.db.session import get_sessionmaker, init_db
from app.services.admin_auth_service import InvalidAdminUsernameError, validate_admin_username_format
from app.services.password_hasher import hash_password
from app.services.project_key_service import create_api_key
from app.services.project_limit_reservation_repair_service import (
    list_stale_reservations,
    repair_stale_reservation,
)


async def _cmd_init_db() -> None:
    await init_db()
    print("ok")


async def _cmd_create_project(name: str) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        project = Project(name=name)
        session.add(project)
        await session.commit()
        print(project.id)


async def _cmd_create_key(project_id: str, label: str | None) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        project = await session.get(Project, project_id)
        if project is None:
            raise SystemExit(f"project not found: {project_id}")
        issued = await create_api_key(session, project=project, label=label)
        await session.commit()
        print(issued.plaintext)


async def _cmd_create_admin(
    *, username: str, password: str, email: str | None, inactive: bool
) -> None:
    username = username.strip()
    if not username:
        raise SystemExit("username cannot be blank")
    try:
        validate_admin_username_format(username)
    except InvalidAdminUsernameError as exc:
        raise SystemExit(str(exc)) from exc
    password = password.strip()
    if not password:
        raise SystemExit("password cannot be blank")
    email = email.strip() if email else None
    if email == "":
        email = None

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        user = AdminUser(
            username=username,
            email=email,
            password_hash=hash_password(password),
            is_active=not inactive,
        )
        session.add(user)
        try:
            await session.commit()
        except Exception as exc:
            await session.rollback()
            raise SystemExit(f"failed to create admin user: {exc}") from exc
        print(user.id)


async def _cmd_limits_list_stale(
    *,
    older_than_seconds: int | None,
    project_id: str | None,
    limit: int,
) -> None:
    threshold = (
        older_than_seconds
        if older_than_seconds is not None
        else settings.limit_reservation_stale_after_seconds
    )
    now = datetime.now(timezone.utc)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        items = await list_stale_reservations(
            session,
            older_than_seconds=threshold,
            project_id=project_id,
            limit=limit,
            now=now,
        )
    print(
        f"older_than_seconds={threshold}  now={now.isoformat()}  "
        f"listed={len(items)} (limit {limit})"
    )
    for it in items:
        print(
            f"{it.reservation_id}\t{it.project_id}\tage={it.age_seconds}s\t"
            f"kind={it.repair_kind}\trec={it.recommended_action}\t"
            f"gw={it.gateway_request_status or '—'}"
        )


async def _cmd_limits_repair_stale(
    *,
    older_than_seconds: int | None,
    project_id: str | None,
    limit: int,
    dry_run: bool,
) -> None:
    threshold = (
        older_than_seconds
        if older_than_seconds is not None
        else settings.limit_reservation_stale_after_seconds
    )
    mode = "dry_run" if dry_run else "apply"
    now = datetime.now(timezone.utc)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        items = await list_stale_reservations(
            session,
            older_than_seconds=threshold,
            project_id=project_id,
            limit=limit,
            now=now,
        )
    print(
        f"mode={mode}  older_than_seconds={threshold}  "
        f"candidates={len(items)}  now={now.isoformat()}"
    )
    for it in items:
        async with sessionmaker() as session:
            async with session.begin():
                result = await repair_stale_reservation(
                    session,
                    reservation_id=it.reservation_id,
                    mode=mode,
                    now=now,
                )
        if result is None:
            print(f"{it.reservation_id}\tmissing")
            continue
        print(
            f"{it.reservation_id}\t{result.project_id}\t{result.action}\t"
            f"applied={result.applied}\t{result.message}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(prog="conexus")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db")
    p = sub.add_parser("create-project")
    p.add_argument("--name", required=True)
    p = sub.add_parser("create-key")
    p.add_argument("--project-id", required=True)
    p.add_argument("--label", default=None)
    p = sub.add_parser("create-admin")
    p.add_argument("--username", required=True)
    p.add_argument("--password", default=None)
    p.add_argument(
        "--password-stdin",
        action="store_true",
        help="Read password from stdin (recommended for CI/automation).",
    )
    p.add_argument("--email", default=None)
    p.add_argument("--inactive", action="store_true")

    plimits = sub.add_parser("limits")
    pl_sub = plimits.add_subparsers(dest="limits_cmd", required=True)
    p_ls = pl_sub.add_parser(
        "list-stale-reservations",
        help="List stale unreconciled limit reservations",
    )
    p_ls.add_argument("--older-than-seconds", type=int, default=None)
    p_ls.add_argument("--project-id", default=None)
    p_ls.add_argument("--limit", type=int, default=100)

    p_rep = pl_sub.add_parser(
        "repair-stale-reservations",
        help="Dry-run or apply repair for each stale reservation in the list",
    )
    p_rep.add_argument("--older-than-seconds", type=int, default=None)
    p_rep.add_argument("--project-id", default=None)
    p_rep.add_argument("--limit", type=int, default=100)
    rep_g = p_rep.add_mutually_exclusive_group(required=True)
    rep_g.add_argument("--dry-run", action="store_true")
    rep_g.add_argument("--apply", action="store_true")

    args = parser.parse_args()

    match args.cmd:
        case "init-db":
            asyncio.run(_cmd_init_db())
        case "create-project":
            asyncio.run(_cmd_create_project(args.name))
        case "create-key":
            asyncio.run(_cmd_create_key(args.project_id, args.label))
        case "create-admin":
            if args.password_stdin:
                password = sys.stdin.read().strip()
            elif args.password is not None:
                password = args.password
            else:
                password = getpass.getpass("Admin password: ")
            asyncio.run(
                _cmd_create_admin(
                    username=args.username,
                    password=password,
                    email=args.email,
                    inactive=args.inactive,
                )
            )
        case "limits":
            match args.limits_cmd:
                case "list-stale-reservations":
                    asyncio.run(
                        _cmd_limits_list_stale(
                            older_than_seconds=args.older_than_seconds,
                            project_id=args.project_id,
                            limit=args.limit,
                        )
                    )
                case "repair-stale-reservations":
                    asyncio.run(
                        _cmd_limits_repair_stale(
                            older_than_seconds=args.older_than_seconds,
                            project_id=args.project_id,
                            limit=args.limit,
                            dry_run=args.dry_run,
                        )
                    )


if __name__ == "__main__":
    main()
