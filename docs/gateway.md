# Gateway

## Назначение

`gateway` — публичный HTTP-вход в систему на NestJS. Сервис принимает REST-запросы, публикует Swagger на `/api` и проксирует операции во внутренние сервисы:

- `auth-service` через RabbitMQ RPC
- `personnel-service` через RabbitMQ RPC
- `production-service` через RabbitMQ RPC
- `etl-service` через прямой HTTP proxy

Сам `gateway` не содержит собственной предметной модели и не хранит бизнес-данные. Его роль — аутентификация входящих запросов, валидация DTO, нормализация ошибок и проксирование вызовов дальше по системе.

## Основные модули

### `AppModule`

Поднимает глобальные инфраструктурные возможности:

- `ConfigModule` как глобальный источник конфигурации
- `CacheModule` с TTL `10000`
- `ThrottlerModule` с тремя профилями лимитов:
  - `short`: `20 req / 1s`
  - `medium`: `100 req / 10s`
  - `long`: `500 req / 60s`
- `LoggerModule` (`nestjs-pino`) с pretty/file transport в non-production
- глобальные `LoggingInterceptor`, `AllExceptionsFilter`, `ThrottlerGuard`
- `RequestIdMiddleware` для всех маршрутов

### `SecurityModule`

Собирает JWT-проверку и ролевую авторизацию:

- `JwtModule` с `JWT_ACCESS_SECRET`, `JWT_ACCESS_TTL`, `JWT_ACCESS_ISSUER`
- `AuthGuard`:
  - извлекает Bearer token из `Authorization`
  - валидирует JWT
  - при наличии `AUTH_USER_RESOLVER` догружает профиль пользователя из `auth-service`
  - кэширует resolved user на `30s`
- `RoleGuard` проверяет роли из декоратора `@Auth(...)`
- `AuthProxyService` зарегистрирован как `AUTH_USER_RESOLVER`

### Доменные HTTP-модули

- `AuthModule`
  - контроллеры `AuthController` и `UsersController`
  - маршруты аутентификации и администрирования пользователей
- `PersonnelModule`
  - `PersonnelController` + `PersonnelProxyService`
  - маршруты по подразделениям, должностям, сотрудникам и шаблонам смен
- `ProductionModule`
  - `ProductionController` + `ProductionProxyService`
  - маршруты по продуктам, заказам, выпуску, продажам, остаткам, качеству, датчикам, KPI
- `EtlModule`
  - `EtlController` + `EtlProxyService`
  - HTTP proxy в ETL API, включая multipart upload и file download

### `RabbitModule`

Подключает `@golevelup/nestjs-rabbitmq` через `getRMQConfig()`:

- `AMQP_URI` берется из конфигурации
- `prefetchCount = 32`
- publish persistent
- `connectionInitOptions.wait = false`
- очереди создаются как quorum (`x-queue-type = quorum`)

## Внешний API

### Аутентификация и пользователи

Контроллеры:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/refresh-session`
- `GET /api/users`
- `PATCH /api/users/:userId`
- `POST /api/users/deactivate`

Особенности:

- `login` и `refresh-session` выставляют `httpOnly` cookie `refreshToken`
- `register` и `login` имеют отдельные throttling-лимиты
- `GET /auth/me` опирается на `AuthGuard`, который после валидации JWT догружает пользователя из `auth-service`
- часть маршрутов ограничена ролями через `@Auth(...)`
- `GET /users` в коде помечен как admin-only по Swagger/описанию, но decorator `@Auth(UserRole.ADMIN)` сейчас закомментирован

### Personnel API

`PersonnelController` публикует CRUD/queries для:

- подразделений
- должностей
- сотрудников
- шаблонов смен

Маршруты защищены ролями `ADMIN`, `MANAGER`, `SHIFT_MANAGER`, `ANALYST` в зависимости от операции.

### Production API

`ProductionController` публикует операции для:

- продуктов
- производственных заказов
- выпуска продукции
- продаж и их сводки
- складских остатков
- результатов контроля качества
- показаний датчиков
- KPI

Контроллер оформлен как публичный HTTP фасад поверх `ProductionProxyService`.

### ETL API

`EtlController` проксирует запросы в отдельный ETL HTTP API:

- `POST /api/etl/import`
- `POST /api/etl/import/file`
- `GET /api/etl/imports`
- `GET /api/etl/imports/:id`
- `GET /api/etl/imports/:id/file`
- `POST /api/etl/imports/:id/retry`

Особенности:

- требуется роль `ADMIN`
- при file import используется `FileInterceptor`
- максимальный размер файла: `20 MB`
- проксируются `x-request-id`, `x-user-id`, `x-user-role` и входящий `Authorization`

## Интеграции

### RabbitMQ

`AuthProxyService`, `PersonnelProxyService` и `ProductionProxyService` отправляют RPC-запросы через `amqpConnection.request(...)`.

Используемые exchanges по коду:

- `efko.auth.commands`
- `efko.auth.queries`
- `efko.auth.events`
- `efko.personnel.commands`
- `efko.personnel.queries`
- `efko.production.commands`
- `efko.production.queries`

Ключевые auth RPC topics:

- `AuthRegisterUserCommand.topic`
- `AuthLoginUserCommand.topic`
- `AuthRefreshSessionCommand.topic`
- `AuthGetCurrentUserQuery.topic`
- `AuthGetUsersQuery.topic`
- `AuthUpdateUserCommand.topic`
- `AuthDeactivateUserCommand.topic`

Personnel и Production используют аналогичную схему: отдельные command/query topics из `@efko-kernel/contracts`.

Каждый proxy:

- пробрасывает request metadata через `buildRpcHeadersFromRequest`
- логирует начало, завершение, rejected и failed исхода
- ставит timeout на RPC через `requestWithTimeout(...)`

### HTTP-интеграция с ETL

`EtlProxyService` обращается к `ETL_SERVICE_URL` и по умолчанию использует внутренний адрес сервиса. Внешний маршрут всегда собирается как `/api/v1/...`. Ошибки downstream HTTP разворачиваются в `HttpException`, при недоступности возвращается `503`.

## Обработка ошибок

### HTTP слой

- глобально подключен `HttpExceptionFilter` в `main.ts`
- в `AppModule` дополнительно зарегистрирован `AllExceptionsFilter`
- валидация DTO выполняется глобальным `ValidationPipe` с `transform`, `whitelist`, `forbidNonWhitelisted`

### Нормализация RPC ошибок

Proxy-сервисы ожидают либо успешный payload, либо `RpcErrorResponse`. Для auth-кодов есть явное сопоставление:

- `USER_ALREADY_EXISTS` -> `409`
- `USER_NOT_FOUND` -> `404`
- `INVALID_CREDENTIALS` -> `401`
- `REFRESH_TOKEN_*` -> `401`/`404`
- неизвестные коды падают в `HttpException` через общий mapper

Если RPC не отвечает, `requestWithTimeout(...)` выбрасывает `GatewayTimeoutException`.

### ETL ошибки

ETL proxy:

- возвращает downstream status/code, если тот пришел от ETL
- возвращает `503 ETL service unavailable`, если соединение не удалось

## Observability и logging

- `nestjs-pino` используется как основной HTTP logger
- в dev-режиме пишется файл `logs/gateway.log`
- `RequestIdMiddleware` присваивает `requestId`
- `LoggingInterceptor` логирует HTTP-запросы и latency
- `AuthProxyService` и другие proxy-сервисы дополнительно логируют RPC lifecycle (`started`, `completed`, `rejected`, `failed`)
- Swagger поднимается на `/api`, JSON — на `/api/swagger/json`

## Хранение данных

Собственного persistence слоя в `gateway` нет:

- нет Prisma/TypeORM/Mongoose модулей
- кэш используется только как инфраструктурный слой для resolved user в `AuthGuard`
- stateful часть сведена к cookie `refreshToken` на HTTP-ответе и краткоживущему cache entry

## Роль в системе

`gateway` связывает пользовательский HTTP-интерфейс и внутреннюю микросервисную шину:

- проводит аутентификацию по access token
- выполняет coarse-grained авторизацию по ролям
- унифицирует контракты и ошибки для внешних клиентов
- консолидирует доступ к нескольким backend-сервисам через единый REST API

## Допущения и пробелы по коду

- `gateway` явно зависит от `production-service`, но `getRMQConfig()` в текущем коде декларирует exchanges/queues только для `auth` и `personnel`; production exchanges в конфиге не зарегистрированы.
- `GET /api/users` описан как admin-only, но защита роли сейчас отключена комментарием.
- В сервисе нет собственного health endpoint; доступность downstream определяется только по факту proxy-вызова.
