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

from app.db.models import AdminUser, Project
from app.db.session import get_sessionmaker, init_db
from app.services.admin_auth_service import InvalidAdminUsernameError, validate_admin_username_format
from app.services.password_hasher import hash_password
from app.services.project_key_service import create_api_key


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


if __name__ == "__main__":
    main()
