-- Bootstrap databases that Temporal's auto-setup expects to exist on the same
-- Postgres instance the app uses. Runs only when the postgres data volume is
-- fresh (docker-entrypoint-initdb.d behavior).
CREATE DATABASE temporal;
CREATE DATABASE temporal_visibility;
