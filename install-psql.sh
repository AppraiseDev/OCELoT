#!/bin/bash
which psql
if [ "$?" -gt "0" ]; then
  echo "Not installed"
  apt-get install -y curl ca-certificates gnupg apt-transport-https
  curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
  sh -c echo "deb [signed-by=/usr/share/keyrings/postgresql-keyring.gpg] http://apt.postgresql.org/pub/repos/apt/ bullseye-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
  apt-get update
  apt-get install -y postgresql-14
fi
