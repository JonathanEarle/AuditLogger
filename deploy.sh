#!/usr/bin/env bash

echo "Enter password for postgres user"
read -s DB_PASSWORD

echo "Setting up environment..."
salt=$(echo $RANDOM | md5sum | head -c 32)
echo "TOKEN_SALT=${salt}" > .env

mkdir -p .secrets
echo $DB_PASSWORD > ./.secrets/db_pw

echo "[postgresql]
host=database
database=audit_logging
user=postgres
password=${DB_PASSWORD}" > ./src/database.ini

echo "Removing existing deployment..."
docker-compose down

echo "Deploying..."
docker-compose up --build --force-recreate --detach

echo "Audit Logger deployed to http://localhost:8080"
