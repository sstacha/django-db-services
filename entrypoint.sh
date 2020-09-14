#!/usr/bin/env bash
set -x
set -e

function fix_linux_internal_host() {
DOCKER_INTERNAL_HOST="host.docker.internal"
if ! grep $DOCKER_INTERNAL_HOST /etc/hosts > /dev/null ; then
DOCKER_INTERNAL_IP="$(ip route | grep -E '(default|docker0)' | grep -Eo '([0-9]+\.){3}[0-9]+' | tail -1)"
echo -e "$DOCKER_INTERNAL_IP\t$DOCKER_INTERNAL_HOST" | tee -a /etc/hosts > /dev/null
echo "Added $DOCKER_INTERNAL_HOST to hosts /etc/hosts"
fi
}

echo "hosts: "
echo "$(cat /etc/hosts)"
echo "param 1: $1"

# todo: determine if we should always collectstatic and migrate

fix_linux_internal_host
echo "running command"
exec "$@"
