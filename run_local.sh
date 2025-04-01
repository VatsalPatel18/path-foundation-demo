docker build -t path-foundation-demo . &&
docker stop $(docker ps -a -q) &&
docker run -p 8080:8080 -it --env-file env.list path-foundation-demo 
