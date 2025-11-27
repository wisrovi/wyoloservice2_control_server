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

# Start Portainer
echo "Starting Portainer..."
docker rm -f portainer || true
# Hash for password '1234567891011'
HASH='$2b$12$ePHQ.0KcGw6/GKENVv2g3ex6BgRYDRt.8BblMnbtlRHh2nYgm9U1C'
docker run -d --name portainer --restart=always \
    -p 9000:9000 \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v portainer_data:/data \
    portainer/portainer-ce:latest \
    --admin-password "$HASH"

echo "Portainer started."

# Keep the container running
tail -f /dev/null
