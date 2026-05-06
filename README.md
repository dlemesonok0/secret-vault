# Secret Vault

Локальный self-hosted сервис для безопасного хранения секретов. Секреты сохраняются в SQLite только в зашифрованном виде, для шифрования используется AES-GCM. Мастер-ключ не хранится на диске: после запуска сервис всегда находится в `sealed`-состоянии, а ключ восстанавливается в памяти из нескольких частей через SHA-256.

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

Сервис будет доступен на `http://localhost:8000`.

Минимальный web-интерфейс:

- `http://localhost:8000/ui` - admin-страница для seal/unseal, сохранения секрета и создания wrap-токена.
- `http://localhost:8000/unwrap-ui` - публичная страница для одноразового unwrap по токену.

Фронтенд не сохраняет токены и значения секретов в localStorage/sessionStorage. Wrap-токен вводится в тело запроса, а не в URL.

## Локальная проверка

```bash
poetry install --with dev
poetry run ruff check .
poetry run pytest
```

## GitHub Actions

В репозитории есть два workflow:

- `.github/workflows/ci.yml` запускает Ruff, pytest, Docker build и публикует образ в GitHub Container Registry для push в `main` и тегов `v*`.
- `.github/workflows/deploy.yml` вручную разворачивает опубликованный образ на сервер по SSH через `workflow_dispatch`.

Для публикации в GHCR дополнительных секретов не нужно: используется `GITHUB_TOKEN`. Для deploy нужно добавить repository secrets:

- `DEPLOY_HOST` - адрес сервера.
- `DEPLOY_USER` - пользователь SSH.
- `DEPLOY_SSH_KEY` - приватный SSH-ключ.
- `VAULT_ADMIN_TOKEN` - admin token для сервиса.

На сервере должны быть установлены Docker и Docker Compose plugin. Workflow создаст `~/secret-vault/docker-compose.yml`, подключит volume `~/secret-vault/data:/app/data` и поднимет контейнер на порту `8000`.

## Проверка состояния

```bash
curl http://localhost:8000/status
```

Ожидаемо после старта:

```json
{"sealed":true}
```

Readiness-check для контейнера и оркестратора:

```bash
curl http://localhost:8000/ready
```

## Unseal

```bash
curl -X POST http://localhost:8000/unseal \
  -H "Authorization: Bearer change-me" \
  -H "Content-Type: application/json" \
  -d '{"parts":["key1","key2","key3"]}'
```

## Создание секрета

```bash
curl -X POST http://localhost:8000/secrets \
  -H "Authorization: Bearer change-me" \
  -H "Content-Type: application/json" \
  -d '{"name":"database_password","value":"super-secret-password"}'
```

## Получение секрета

```bash
curl http://localhost:8000/secrets/database_password \
  -H "Authorization: Bearer change-me"
```

## Wrap

```bash
curl -X POST http://localhost:8000/secrets/database_password/wrap \
  -H "Authorization: Bearer change-me" \
  -H "Content-Type: application/json" \
  -d '{"ttl_seconds":60}'
```

В ответе вернется временный одноразовый токен. В базе хранится только SHA-256-хеш токена.

## Unwrap

```bash
curl -X POST http://localhost:8000/unwrap \
  -H "Content-Type: application/json" \
  -d '{"token":"TOKEN_FROM_WRAP"}'
```

`/unwrap` не требует admin token: доступ дает сам временный токен. После успешного unwrap токен помечается как использованный.

## Seal

```bash
curl -X POST http://localhost:8000/seal \
  -H "Authorization: Bearer change-me"
```

После `seal` мастер-ключ удаляется из памяти, а операции с секретами и wrap-токенами возвращают `423 Locked`.

## Демонстрационный сценарий

```bash
docker compose up --build
curl http://localhost:8000/status
curl -X POST http://localhost:8000/secrets \
  -H "Authorization: Bearer change-me" \
  -H "Content-Type: application/json" \
  -d '{"name":"database_password","value":"super-secret-password"}'
curl -X POST http://localhost:8000/unseal \
  -H "Authorization: Bearer change-me" \
  -H "Content-Type: application/json" \
  -d '{"parts":["key1","key2","key3"]}'
curl -X POST http://localhost:8000/secrets \
  -H "Authorization: Bearer change-me" \
  -H "Content-Type: application/json" \
  -d '{"name":"database_password","value":"super-secret-password"}'
sqlite3 data/vault.db "select name, ciphertext, nonce from secrets;"
curl -X POST http://localhost:8000/secrets/database_password/wrap \
  -H "Authorization: Bearer change-me" \
  -H "Content-Type: application/json" \
  -d '{"ttl_seconds":60}'
curl -X POST http://localhost:8000/unwrap \
  -H "Content-Type: application/json" \
  -d '{"token":"TOKEN_FROM_WRAP"}'
curl -X POST http://localhost:8000/unwrap \
  -H "Content-Type: application/json" \
  -d '{"token":"TOKEN_FROM_WRAP"}'
curl -X POST http://localhost:8000/seal \
  -H "Authorization: Bearer change-me"
curl http://localhost:8000/secrets/database_password \
  -H "Authorization: Bearer change-me"
```

В выводе SQLite не должно быть исходного значения `super-secret-password`.

## Хранение и безопасность

- Таблица `secrets` хранит `name`, `nonce`, `ciphertext`, даты создания и обновления.
- Поле `crypto_version` зарезервировано для будущей ротации ключей и изменения формата шифрования.
- `ciphertext` содержит результат AES-GCM вместе с authentication tag.
- Для каждого шифрования создается новый случайный 12-байтовый nonce.
- Таблица `wrap_tokens` хранит только SHA-256-хеш токена, имя секрета, TTL и состояние использования.
- Таблица `audit_events` хранит технические события без plaintext, master key и wrap-токенов.
- `/unwrap` ограничен простым in-memory rate limit по клиентскому IP. По умолчанию: 20 запросов за 60 секунд.
- Схема БД управляется Alembic-миграциями при старте приложения.
- `.env` не должен попадать в репозиторий; пример настроек находится в `.env.example`.
