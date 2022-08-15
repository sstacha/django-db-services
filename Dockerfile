# FROM python:3.8.3-buster
FROM python:3.10.1-buster

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client default-libmysqlclient-dev libldap2-dev libsasl2-dev libssl-dev \
        wget vim lynx curl
#    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
COPY requirements.txt ./
COPY entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN ln -s /usr/local/bin/docker-entrypoint.sh / # backwards compat
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY . .

# adding 5000 to debug with runserver when needed
EXPOSE 5000
EXPOSE 8000
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# NEW: MULTI-ARCH BUILDS
# PREP (1st time on dev box):
# docker buildx create --name spebuilder
# docker buildx use spebuilder
# docker buildx inspect --bootstrap
# docker buildx ls
# NOTE: at this point should be starred and show arch's we build for

# BUILD (each time):
# docker buildx build -t sasonline/django-db-services:p3.10.1d3.2.14b6 -t sasonline/django-db-services --platform linux/amd64,linux/arm64,linux/ppc64le,linux/arm/v7 --push .
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
