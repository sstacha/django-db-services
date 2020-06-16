FROM python:3.8.3-buster

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
# ENTRYPOINT ["entrypoint.sh"]

# BUILD
# docker build -t django-db-services .
# RUN
# w/dir mount
# docker run -it --env-file=.env --name django-db-services -p 8000:8000 -v $(pwd)/data:/usr/src/app/data django-db-services
# w/container named mount
# docker run -it --env-file=.env --name django-db-services -p 8000:8000 -v django-db-services-data:/usr/src/app/data django-db-services
# TO PUSH TO REPO
# docker tag django-db-services sasonline/django-db-services
# docker tag django-db-services sasonline/django-db-services:p3.8.3d3.0.7b1
# docker login
# docker push sasonline/django-db-services
# docker push sasonline/django-db-services:p3.8.3d3.0.7b2
