# Secret Vault

Локальный self-hosted сервис для безопасного хранения секретов. Секреты сохраняются в SQLite только в зашифрованном виде, для шифрования используется AES-GCM. Мастер-ключ не хранится на диске: после запуска сервис всегда находится в `sealed`-состоянии, а ключ восстанавливается в памяти из нескольких частей через SHA-256.

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

Сервис будет доступен на `http://localhost:8000`.

## Web UI

В сервисе есть два простых web-интерфейса:

- `http://localhost:8000/ui` - admin UI для `status`, `seal`, `unseal`, сохранения секретов и создания wrap-токенов.
- `http://localhost:8000/unwrap-ui` - публичная страница для одноразового unwrap по wrap-токену.

### Admin UI

Открой:

```text
http://localhost:8000/ui
```

На странице есть поле `Admin token`. В него нужно ввести значение `VAULT_ADMIN_TOKEN` из `.env`.

Для демо, если `.env` скопирован из `.env.example`, это:

```text
change-me
```

Что можно сделать через admin UI:

- `Status` - проверить, sealed vault или нет.
- `Seal` - закрыть vault и удалить master key из памяти процесса.
- `Unseal` - разблокировать vault через key parts.
- `Save Secret` - создать или обновить секрет.
- `Create Wrap Token` - создать одноразовый временный токен для передачи секрета.

### Как сделать unseal через UI

1. В поле `Admin token` введи admin token.
2. В блоке `Unseal` введи ключевые части, каждую с новой строки:

```text
key1
key2
key3
```

3. Нажми `Unseal`.
4. В ответе должно быть:

```json
{
  "sealed": false,
  "message": "Vault unsealed"
}
```

Важно: для реального использования `key1/key2/key3` нужно заменить на длинные случайные строки. Эти части формируют master key. Если использовать другие части или другой порядок, старые секреты не расшифруются.

### Как сохранить секрет через UI

1. Убедись, что vault уже unsealed.
2. В поле `Admin token` введи admin token.
3. В блоке `Save Secret` заполни:
   - `Name` - имя секрета, например `database_password`.
   - `Value` - значение секрета.
4. Нажми `Save`.

Если секрет с таким именем уже есть, он будет обновлен. В базе данных plaintext не хранится: сохраняются только `nonce`, `ciphertext` и служебные поля.

### Как создать wrap-токен через UI

1. Убедись, что vault unsealed.
2. В поле `Admin token` введи admin token.
3. В блоке `Create Wrap Token` заполни:
   - `Secret name` - имя существующего секрета.
   - `TTL seconds` - срок жизни токена в секундах.
4. Нажми `Wrap`.
5. В ответе появится:

```json
{
  "token": "temporary-token",
  "expires_at": "2026-05-07T12:01:00Z"
}
```

Этот токен нужно передать получателю. В БД хранится только SHA-256-хеш токена, сам токен не сохраняется.

### Unwrap UI

Открой:

```text
http://localhost:8000/unwrap-ui
```

На этой странице admin token не нужен. Доступ дает сам wrap-токен.

Порядок работы:

1. Вставь wrap-токен в поле `Wrap token`.
2. Нажми `Unwrap once`.
3. Если токен валиден, не истек и еще не использован, страница покажет имя секрета и его значение.
4. Токен сразу станет использованным.
5. Повторный unwrap тем же токеном вернет ошибку `409 Token already used`.

UI очищает поле токена после запроса. Успешный результат на странице автоматически очищается через 30 секунд.

### Ограничения безопасности UI

- Не передавай wrap-токен через URL query string.
- Не публикуй screenshot с открытым секретом.
- Не сохраняй admin token и key parts в браузере.
- Не используй `change-me`, `key1`, `key2`, `key3` вне демо.
- `/unwrap-ui` публичный по дизайну: любой, у кого есть валидный wrap-токен, может получить секрет один раз до истечения TTL.
- `/unwrap` ограничен in-memory rate limit по IP. По умолчанию: 20 запросов за 60 секунд.

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

Для публикации в GHCR дополнительных секретов не нужно: используется `GITHUB_TOKEN`. Для deploy нужны repository variables/secrets:

- `DEPLOY_HOST` - адрес сервера.
- `DEPLOY_USER` - пользователь SSH.
- `DEPLOY_URL` - публичная ссылка на развернутый сервис для GitHub Environments, например `http://203.0.113.10:8000` или `https://vault.example.com`.
- `DEPLOY_SSH_KEY` - приватный SSH-ключ, лучше хранить как secret.
- `VAULT_ADMIN_TOKEN` - admin token для сервиса, лучше хранить как secret.

На сервере должны быть установлены Docker и Docker Compose plugin. Workflow создаст `~/secret-vault/docker-compose.yml`, подключит volume `~/secret-vault/data:/app/data` и поднимет контейнер на порту `8000`.

Deploy workflow привязан к GitHub Environment `production`. Если задана repository variable `DEPLOY_URL`, GitHub покажет ссылку на текущее развернутое приложение в UI workflow/deployment.

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
- Схема БД управляется Alembic-миграциями при старте приложения.
- `.env` не должен попадать в репозиторий; пример настроек находится в `.env.example`.
