# FROM python:3.8.3-buster
FROM python:3.9.2-buster

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client default-libmysqlclient-dev libldap2-dev libsasl2-dev libssl-dev
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

# BUILD
# docker build -t django-db-services .
# RUN
# w/dir mount
# docker run -it --env-file=.env --name django-db-services -p 8000:8000 -v $(pwd)/data:/usr/src/app/data django-db-services
# w/container named mount
# docker run -it --env-file=.env --name django-db-services -p 8000:8000 -v django-db-services-data:/usr/src/app/data django-db-services
# TO PUSH TO REPO
# docker tag django-db-services sasonline/django-db-services
# docker tag django-db-services sasonline/django-db-services:p3.8.3d3.0.8b15
# docker tag django-db-services sasonline/django-db-services:p3.9.2d3.1.7b5
# docker login
# docker push sasonline/django-db-services
# docker push sasonline/django-db-services:p3.9.2d3.1.7b5
