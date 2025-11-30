#!/bin/sh

echo "Starting Control Server..."

# Start Docker daemon
dockerd &
DOCKER_PID=$!
echo "Docker daemon started with PID $DOCKER_PID"

# Wait for Docker to be ready
until docker info > /dev/null 2>&1; do sleep 1; done

# Configure SSH password
SSH_PASSWORD=${SSH_PASSWORD:-password}
echo "root:$SSH_PASSWORD" | chpasswd

# Start SSH
echo "Starting SSH server..."
/usr/sbin/sshd -D -p 50422 &

# Start ttyd
echo "Starting ttyd web terminal..."
ttyd -p 7681 -i 0.0.0.0 bash &

# Keep the container running
tail -f /dev/null
