#!/bin/bash
set -e

SKIP_BUILDING_BASE=false
while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-base) SKIP_BUILDING_BASE=true; shift ;;
    *) echo "Unknown: $1"; exit 1 ;;
  esac
done

cd /home/corentin/fcquic_applications_master_thesis

if [ "$SKIP_BUILDING_BASE" = false ]; then
  echo "Building base image"
  docker build -t base -f ./docker_images/base/Dockerfile .
else
  echo "Skipping base image build"
fi

echo "Building fcquic_client image"
docker build -t fcquic_client -f ./docker_images/fcquic_client/Dockerfile ./docker_images/fcquic_client

echo "Building fcquic_server image"
docker build -t fcquic_server -f ./docker_images/fcquic_server/Dockerfile ./docker_images/fcquic_server

echo "Building tquic_client image"
docker build -t tquic_client -f ./docker_images/tquic_client/Dockerfile ./docker_images/tquic_client

echo "Building tquic_server image"
docker build -t tquic_server -f ./docker_images/tquic_server/Dockerfile ./docker_images/tquic_server

echo "Building tcp_client image"
docker build -t tcp_client -f ./docker_images/tcp_client/Dockerfile ./docker_images/tcp_client

echo "Building tcp_server image"
docker build -t tcp_server -f ./docker_images/tcp_server/Dockerfile ./docker_images/tcp_server

echo "All images built."
