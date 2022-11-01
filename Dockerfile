FROM alpine

MAINTAINER Niklas Elsbrock

# add apk edge repositories (including `testing` for py3-flask-sqlalchemy)
# and update package index
RUN echo -e "https://dl-cdn.alpinelinux.org/alpine/edge/main/\n"\
"https://dl-cdn.alpinelinux.org/alpine/edge/community/\n"\
"https://dl-cdn.alpinelinux.org/alpine/edge/testing/"\
	> /etc/apk/repositories \
	&& apk --no-cache update

# install nateman
RUN apk --no-cache add \
	python3 \
	py3-flask \
	py3-flask-sqlalchemy \
	py3-click \
	py3-yaml \
	py3-bcrypt \
	py3-openpyxl \
	&& mkdir -p /srv/nateman/nateman

COPY nateman /srv/nateman/nateman
WORKDIR /srv/nateman

# expose webserver port
EXPOSE 8080

# start command
CMD ["env","FLASK_APP=nateman","FLASK_ENV=development",\
	"flask","run","--host=0.0.0.0","--port=8080"]
