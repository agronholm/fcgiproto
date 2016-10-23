#!/bin/sh

# Run this in the same directory!
docker run --rm -p 80:80 -v $PWD/nginx_docker.conf:/etc/nginx/conf.d/default.conf:ro nginx
