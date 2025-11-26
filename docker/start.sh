#!/bin/sh

echo "Starting Docker-in-Docker with SSH and Portainer..."

# Start Docker daemon in background
dockerd &
DOCKER_PID=$!

echo "Docker daemon started with PID $DOCKER_PID"

# Wait for Docker to be ready
sleep 5
# Wait for Docker to be ready
until docker info > /dev/null 2>&1; do sleep 1; done

# Configure SSH password
SSH_PASSWORD=${SSH_PASSWORD:-password}
echo "root:$SSH_PASSWORD" | chpasswd

# Start SSH
echo "Starting SSH server..."
/usr/sbin/sshd -D -p 50422 &
SSH_PID=$!

echo "SSH started on port 50422"
echo "Starting ttyd web terminal..."
ttyd -p 7681 -i 0.0.0.0 bash &
echo "ttyd started on port 7681"


# Start Portainer
echo "Starting Portainer..."
docker rm -f portainer || true
docker run -d --name portainer --restart=always -p 9000:9000 -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer-ce:latest
echo "Portainer started."

# Keep the container running
tail -f /dev/null
