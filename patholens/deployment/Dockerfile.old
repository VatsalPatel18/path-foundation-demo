# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# This is used to build a Docker image that includes the necessary dependencies
# for running the Path Foundation as a microservice.

FROM python:3.12-slim-bullseye

#RUN apt-get update && apt-get install -y nano tmux

# Set up a new user named "user" with user ID 1000
RUN useradd -m -u 1000 user

ENV HOME=/home/user \
	PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app
# Change ownership of /app to the non-root user


RUN apt-get update && \
    apt-get install -y --no-install-recommends unzip wget && \
    rm -rf /var/lib/apt/lists/*
RUN mkdir /home/user/app/path-cache

RUN chown -R user /home/user/app


# Switch to the "user" user
USER user

RUN wget https://storage.googleapis.com/healthai-us/pathology/cache/path-cache.zip -O $HOME/app/path-cache.zip
RUN unzip $HOME/app/path-cache.zip -d $HOME/app/path-cache && rm $HOME/app/path-cache.zip


COPY --chown=user ./requirements.txt  $HOME/app
RUN pip3 install -r requirements.txt

COPY --chown=user ./ $HOME/app
ENV PYTHONPATH=${PYTHONPATH}:$HOME/app

RUN ls -R | grep ":$" | sed -e 's/:$//' -e 's/[^-][^\/]*\//--/g' -e 's/^/   /' -e 's/-/|/'

ENTRYPOINT ["python3", "server_gunicorn.py"]
