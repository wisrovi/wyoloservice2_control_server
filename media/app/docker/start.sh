#!/bin/bash

# Esperar a que Docker esté disponible
echo "Waiting for Docker daemon to start..."
while ! docker info > /dev/null 2>&1; do
    sleep 1
done
echo "Docker daemon is ready!"

# Iniciar servicios Samba
echo "Starting Samba services..."
nmbd -D
smbd -D

# Iniciar los contenedores dentro del DIND
echo "Starting containers inside DIND..."
cd /app
docker-compose up -d

echo "All containers started successfully!"

# Mantener el contenedor corriendo
tail -f /dev/null