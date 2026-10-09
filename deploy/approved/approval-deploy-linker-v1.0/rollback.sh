#!/bin/bash
systemctl stop approval-linker.service || true
systemctl disable approval-linker.service || true
rm -f /etc/systemd/system/approval-linker.service
systemctl daemon-reload
echo "approval-linker: 已回滚"
