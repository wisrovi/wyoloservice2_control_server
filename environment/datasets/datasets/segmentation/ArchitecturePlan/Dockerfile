FROM ultralytics/ultralytics:8.3.86


USER root


# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1


RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get -y install net-tools
RUN apt-get -y install git
RUN apt install iputils-ping -y

RUN apt-get update && \
    apt-get install -y libgl1-mesa-glx
RUN apt-get install ffmpeg libsm6 libxext6  -y
RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y



RUN pip install 'ultralytics[explorer]'


WORKDIR /app
CMD ["yolo", "explorer"]
