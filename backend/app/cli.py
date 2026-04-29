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

from app.db.models import Project
from app.db.session import get_sessionmaker, init_db
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


def main() -> None:
    parser = argparse.ArgumentParser(prog="conexus")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db")
    p = sub.add_parser("create-project")
    p.add_argument("--name", required=True)
    p = sub.add_parser("create-key")
    p.add_argument("--project-id", required=True)
    p.add_argument("--label", default=None)
    args = parser.parse_args()

    match args.cmd:
        case "init-db":
            asyncio.run(_cmd_init_db())
        case "create-project":
            asyncio.run(_cmd_create_project(args.name))
        case "create-key":
            asyncio.run(_cmd_create_key(args.project_id, args.label))


if __name__ == "__main__":
    main()
