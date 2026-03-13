#!/bin/bash

# NOTE: code from Anthony Doeraene

if [ -z "$NS" ]; then
    # No namespace specified
    /tquic-client $@
else
    # Run in specific namespace
    ip netns exec $NS /tquic-client $@
fi
