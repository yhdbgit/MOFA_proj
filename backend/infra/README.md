# Infrastructure

Local and deployment infrastructure.

Expected components:

- PostgreSQL.
- Redis.
- Docker Compose.
- Database initialization scripts.

## Docker Compose

After installing and starting Docker Desktop, start local infrastructure from the project root:

```bash
docker compose -f infra/docker/compose.yaml up -d postgres redis
```

When the terminal is currently in `services/main-api/mofa`, use:

```bash
docker compose -f ../../../infra/docker/compose.yaml up -d postgres redis
```

The `-f` path is resolved relative to the terminal's current directory.

Check the containers:

```bash
docker compose -f infra/docker/compose.yaml ps
```

Stop the containers without deleting the stored database volume:

```bash
docker compose -f infra/docker/compose.yaml stop postgres redis
```

## PostgreSQL

Default local connection:

```txt
jdbc:postgresql://localhost:5432/mofa
username: mofa
password: mofa-local-password
```

Check persisted data:

```bash
docker exec mofa-postgres psql -U mofa -d mofa -c "select * from chat_sessions;"
docker exec mofa-postgres psql -U mofa -d mofa -c "select * from chat_messages;"
```

## Redis

Default local connection:

```txt
host: localhost
port: 6379
channel: mofa.events
```

Subscribe to Spring Boot events:

```bash
docker exec mofa-redis redis-cli SUBSCRIBE mofa.events
```

Expected event types:

- `CHAT_CREATED`
- `CHAT_MESSAGE_CREATED`
- `AGENT_RESULT_READY`
