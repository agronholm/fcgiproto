#!/bin/sh

# Run this in the same directory!
docker run --rm -p 80:80 -v $PWD/apache_docker.conf:/usr/local/apache2/conf/httpd.conf:ro httpd:alpine
