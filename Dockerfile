FROM alpine:3.16

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

ENV FLASK_ENV=development
CMD ["flask","run","--host=0.0.0.0","--port=8080"]
