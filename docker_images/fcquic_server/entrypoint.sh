#!/bin/bash

# NOTE: code from Anthony Doeraene

if [ -z "$NS" ]; then
    # No namespace specified
    /server $@
else
    # Run in specific namespace
    ip netns exec $NS /server $@
fi
