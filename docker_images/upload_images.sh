#!/bin/bash
set -e

USERNAME="corentindetry"

IMAGES=("base" "fcquic_client" "fcquic_server" "fcquic_relay" "app_relay" "tquic_client" "tquic_server" "tcp_client" "tcp_server")

for IMAGE in "${IMAGES[@]}"; do
  echo "tagging and pushing $IMAGE"
  docker tag "$IMAGE" "$USERNAME/$IMAGE:latest"
  docker push "$USERNAME/$IMAGE:latest"
done

echo "Pushed all images to dockerhub!"
