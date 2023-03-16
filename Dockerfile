FROM alpine:3.17

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
    # Dirty compatibility workaround: Due to `py3-flask-sqlalchemy` originating from the Alpine testing repository
    # and therefore being built for a newer version of python, we need to move its files from python3.11 to python3.10.
    && mv /usr/lib/python3.11/site-packages/* /usr/lib/python3.10/site-packages/ \
    && mkdir -p /srv/nateman/app

COPY nateman /srv/nateman/app
WORKDIR /srv/nateman

EXPOSE 8080

CMD ["flask","--debug","run","--host=0.0.0.0","--port=8080"]
