#!/bin/bash

# NOTE: code from Anthony Doeraene

if [ -z "$NS" ]; then
    # No namespace specified
    /fcquic_relay $@
else
    # Run in specific namespace
    ip netns exec $NS /fcquic_relay $@
fi
