#!/usr/bin/env python3
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import getpass
from io import StringIO
import json

from app.database import init_db
from app.services.auth_service import create_user
from app.services.system_readiness import collect_system_readiness


def _create_admin(args: argparse.Namespace) -> int:
    password = args.password
    if not password:
        password = getpass.getpass('Password: ')
        confirmation = getpass.getpass('Confirm password: ')
        if password != confirmation:
            raise ValueError('Passwords do not match.')

    init_db()
    user = create_user(
        username=args.username,
        password=password,
        display_name=args.display_name,
        role='admin',
    )
    print(f'Created administrator: {user["username"]}')
    return 0


def _doctor(args: argparse.Namespace) -> int:
    if args.json:
        with redirect_stdout(StringIO()):
            init_db()
    else:
        init_db()
    report = collect_system_readiness()
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        print(f"Core runtime: {'ready' if report['ready'] else 'blocked'}")
        print(f"Publication record: {'ready' if report['publication_ready'] else 'incomplete'}")
        for group in report['groups']:
            print(f"\n{group['label']}:")
            for check in group['checks']:
                marker = {'ok': 'OK', 'warn': 'WARN', 'error': 'ERROR'}.get(check['status'], check['status'].upper())
                print(f"  [{marker}] {check['label']}: {check['detail']}")
                if check.get('path'):
                    print(f"          {check['path']}")
                if check.get('action'):
                    print(f"          Next: {check['action']}")
    return 0 if report['ready'] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='APPAM administration commands')
    subparsers = parser.add_subparsers(dest='command', required=True)

    create_admin = subparsers.add_parser('create-admin', help='Create an administrator account')
    create_admin.add_argument('--username', required=True)
    create_admin.add_argument('--display-name', default='')
    create_admin.add_argument('--password', help='Avoid this option on shared shells; omit it for a hidden prompt.')
    create_admin.set_defaults(handler=_create_admin)

    doctor = subparsers.add_parser('doctor', help='Check APPAM runtime and publication readiness')
    doctor.add_argument('--json', action='store_true', help='Print the machine-readable readiness report')
    doctor.set_defaults(handler=_doctor)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.handler(args)
    except ValueError as exc:
        parser.error(str(exc))
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
