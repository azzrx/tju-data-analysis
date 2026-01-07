#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from django.core.management.commands.runserver import Command as RunServer


def main():
    """Run administrative tasks."""
    RunServer.default_port = os.environ.get('DJANGO_PORT', '8081')
    # 让开发服务器默认监听所有网卡，便于宿主机访问
    RunServer.default_addr = os.environ.get('DJANGO_ADDR', '0.0.0.0')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deepseek_project.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
