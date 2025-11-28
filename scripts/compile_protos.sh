#!/bin/bash
mkdir -p tvos/protos
protoc -I=protos --python_out=tvos/protos --pyi_out=tvos/protos events.proto
touch tvos/protos/__init__.py
