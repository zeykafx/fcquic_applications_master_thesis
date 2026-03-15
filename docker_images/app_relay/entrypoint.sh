#!/bin/bash

# NOTE: code from Anthony Doeraene

if [ -z "$NS" ]; then
    # No namespace specified
    /app_relay $@
else
    # Run in specific namespace
    ip netns exec $NS /app_relay $@
fi
