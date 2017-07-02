#!/bin/sh -e

cd "$(dirname "$0")"
exec python3 -m sittager.app "$@"
