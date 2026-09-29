#!/bin/bash
systemctl is-active approval-linker.service || exit 1
echo "approval-linker: ACTIVE"
