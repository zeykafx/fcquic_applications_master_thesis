#!/bin/bash

# NOTE: code from Anthony Doeraene

if [ -z "$NS" ]; then
    # No namespace specified
    /tcp-server $@
else
    # Run in specific namespace
    ip netns exec $NS /tcp-server $@
fi
