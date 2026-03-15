#!/bin/bash

# NOTE: code from Anthony Doeraene

# If NS is not set, then just run the binary as is
# otherwise run in the specified namespace
if [ -z "$NS" ]; then
    # No namespace specified
    /client $@
else
    # Run in specific namespace
    ip netns exec $NS /client $@
fi
