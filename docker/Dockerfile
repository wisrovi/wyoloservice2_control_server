# Basic Docker-in-Docker with SSH and Portainer
FROM ubuntu:22.04

# Set environment variables to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
ENV LANG=C.UTF-8

RUN apt-get update && apt-get install -y \
    openssh-server \
    tmux \
    curl \
    docker.io \
    ttyd \
    && rm -rf /var/lib/apt/lists/*

# Create SSH directory
RUN mkdir -p /run/sshd && \
    ssh-keygen -A && \
    echo "root:password" | chpasswd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's/#Port 22/Port 50422/' /etc/ssh/sshd_config

# Expose ports
EXPOSE 50422 9000 7681

# Copy start script
COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/start.sh"]