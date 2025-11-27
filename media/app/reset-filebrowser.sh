#!/bin/bash
echo 'Resetting Filebrowser...'
docker stop app-filebrowser-1
docker rm app-filebrowser-1
docker run -d   --name app-filebrowser-1   --network app_default   -p 23443:8080   -v /app/samba/datasets:/data   -v /app/filebrowser:/config   -e PUID=1000   -e PGID=1000   --restart always   hurlenko/filebrowser
echo 'Filebrowser reset with default credentials (admin/admin)'
