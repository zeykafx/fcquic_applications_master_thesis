#!/bin/bash

# NOTE: code from Anthony Doeraene

if [ -z "$NS" ]; then
    # No namespace specified
    /tcp-client $@
else
    # Run in specific namespace
    ip netns exec $NS /tcp-client $@
fi
