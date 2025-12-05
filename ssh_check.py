#!/usr/bin/env python3
"""SSH connection helper"""
import subprocess
import sys
import os

def ssh_command(host, user, password, cmd):
    """Execute SSH command with password"""
    try:
        # Using ssh with password via stdin (not ideal but works)
        process = subprocess.Popen(
            ['ssh', '-o', 'StrictHostKeyChecking=no', f'{user}@{host}', cmd],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input='', timeout=30)
        return process.returncode, stdout, stderr
    except Exception as e:
        return 1, '', str(e)

if __name__ == '__main__':
    host = '31.44.7.144'
    user = 'root'
    password = '4x6EltSOS41MbhyD'
    
    # Get bot status
    print('🔍 Проверяю статус бота на сервере...\n')
    code, out, err = ssh_command(host, user, password, 'systemctl status uspsocdowloader --no-pager')
    print(out)
    if err:
        print('STDERR:', err)
    
    # Get logs
    print('\n📋 Последние логи:\n')
    code, out, err = ssh_command(host, user, password, 'journalctl -u uspsocdowloader -n 10 --no-pager')
    print(out)
    if err:
        print('STDERR:', err)
