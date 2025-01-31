FROM python:3.11-slim

# Install dependencies necessary to build and run FFmpeg
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    yasm \
    git \
    curl \
    portaudio19-dev \
    libffi-dev \
    libssl-dev \
    libx264-dev \
    libopus-dev

RUN echo "deb http://deb.debian.org/debian/ bullseye main\ndeb-src http://deb.debian.org/debian/ bullseye main" | tee /etc/apt/sources.list.d/ffmpeg.list  &&\
    apt-get update && \
    apt-get install -y ffmpeg


WORKDIR /characters

# Install Python dependencies
COPY requirements.txt /characters
RUN pip install -r /characters/requirements.txt

# Copy the project files
COPY ./ /characters

# Expose 8000 port from the docker image.
EXPOSE 8000

# Make the entrypoint script executable
RUN chmod +x /characters/entrypoint.sh

# Run the application
CMD ["/bin/sh", "/characters/entrypoint.sh"]
