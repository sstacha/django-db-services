# FROM python:3.8.3-buster
# FROM python:3.10.11-buster
FROM python:3.12.7-bookworm

# this gives Gpg key errors which i think is solveable.  Trying to just use a newer version of mariadb client first
# also, didn't work because mysql uses a compiled binary for new security we can run or build on arm
#RUN apt-get update && apt-get install -y lsb-release inetutils-tools vim lynx curl
#RUN wget https://dev.mysql.com/get/mysql-apt-config_0.8.33-1_all.deb
#RUN DEBIAN_FRONTEND=noninteractive dpkg -i mysql-apt-config_0.8.33-1_all.deb
#RUN apt-get update
#RUN apt install -y mysql-client

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client default-libmysqlclient-dev libldap2-dev libsasl2-dev libssl-dev \
        wget vim lynx curl
#    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
COPY requirements.txt ./
# COPY entrypoint.sh /usr/local/bin/docker-entrypoint.sh
# RUN ln -s /usr/local/bin/docker-entrypoint.sh / # backwards compat
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY . .

# adding 5000 to debug with runserver when needed
EXPOSE 5000
EXPOSE 8000
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
# ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# NEW: MULTI-ARCH BUILDS
# PREP (1st time on dev box):
# docker buildx create --name spebuilder
# docker buildx use spebuilder
# docker buildx inspect --bootstrap
# docker buildx ls
# NOTE: at this point should be starred and show arch's we build for

# BUILD (each time):
# docker buildx build -t sasonline/django-db-services:p3.12.7d3.2.25b3 -t sasonline/django-db-services --platform linux/amd64,linux/arm64 --push .
# OLD: docker buildx build -t sasonline/django-db-services:p3.10.11d3.2.25b1 -t sasonline/django-db-services --platform linux/amd64,linux/arm64,linux/ppc64le,linux/arm/v7 --push .
# NOTE: this should build/build the manifest and push all arches to dockerhub



# BUILD
# docker build -t sasonline/django-db-services .
# RUN
# w/dir mount
# docker run -it --env-file=.env --name django-db-services -p 8000:8000 -v $(pwd)/data:/usr/src/app/data django-db-services
# w/container named mount
# docker run -it --env-file=.env --name django-db-services -p 8000:8000 -v django-db-services-data:/usr/src/app/data django-db-services
# TO PUSH TO REPO
# docker tag django-db-services sasonline/django-db-services
# docker tag django-db-services sasonline/django-db-services:p3.8.3d3.0.8b15
# docker tag django-db-services sasonline/django-db-services:p3.9.2d3.1.7b6
# docker tag django-db-services sasonline/django-db-services:p3.9.6d3.2.9b2
# docker tag sasonline/django-db-services sasonline/django-db-services:p3.10.1d3.2.11b1
# docker login
# docker push sasonline/django-db-services
# docker push sasonline/django-db-services:p3.10.1d3.2.11b1
