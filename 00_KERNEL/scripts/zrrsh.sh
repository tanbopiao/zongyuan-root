#!/bin/bash
exec ssh -i /root/.ssh/zongyuan-sh-20261021 -o ProxyCommand="nc -X connect -x 127.0.0.1:18080 %h %p" -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=25 -o UserKnownHostsFile=/dev/null -o IdentitiesOnly=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=6 "$@"
