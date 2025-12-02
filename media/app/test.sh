docker run \
  --rm \
  -i -t \
  -v ./:/app \
  -v /var/run/docker.sock:/var/run/docker.sock \
  wisrovi/agents:gpu-slim \
  zsh
