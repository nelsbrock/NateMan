FROM alpine:3.18

MAINTAINER Niklas Elsbrock

RUN echo "https://dl-cdn.alpinelinux.org/alpine/edge/testing/" >> /etc/apk/repositories \
    && apk add --no-cache \
        python3 \
        py3-flask \
        py3-flask-sqlalchemy \
        py3-click \
        py3-yaml \
        py3-bcrypt \
        py3-openpyxl \
    && mkdir -p /srv/nateman/app

COPY nateman /srv/nateman/app
WORKDIR /srv/nateman

EXPOSE 8080

CMD ["flask","--debug","run","--host=0.0.0.0","--port=8080"]
