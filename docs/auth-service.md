# Auth Service

## Назначение

`auth-service` — сервис идентификации и управления пользователями. По коду он отвечает за:

- регистрацию пользователя
- вход по email/паролю
- выпуск access token
- выпуск и rotation refresh token
- получение текущего пользователя
- получение списка пользователей
- обновление пользователя
- деактивацию пользователя
- публикацию доменных событий об изменениях пользователей

Основной транспорт сервиса — RabbitMQ RPC. HTTP-приложение поднимается для Nest runtime, cookie parser, глобального фильтра ошибок и Swagger, но бизнес-операции реализованы RabbitRPC handlers, а не публичными REST endpoint'ами.

## Архитектура

Сервис организован слоями.

### Application layer

Use case'ы:

- `RegisterUserUseCase`
- `LoginUserUseCase`
- `RefreshSessionUseCase`
- `GetCurrentUserUseCase`
- `GetUsersUseCase`
- `UpdateUserUseCase`
- `DeactivateUserUseCase`

Порты (`application/ports`):

- `UserRepository`
- `RefreshTokenRepository`
- `PasswordHasher`
- `RefreshTokenHasher`
- `AccessTokenService`
- `RefreshTokenService`

### Domain layer

Содержит:

- `UserEntity`
- `RefreshTokenEntity`
- value objects: `Email`, `FullName`, `PasswordHash`, `RefreshTokenHash`
- доменные ошибки (`AuthError` и конкретные наследники)

Доменные инварианты проверяются именно через value objects и entity-методы, например:

- валидация email
- валидация полного имени
- контроль валидности хэшей
- деактивация пользователя через поведение сущности

### Infrastructure layer

Реализации портов:

- `PrismaUserRepository`
- `PrismaRefreshTokenRepository`
- `BcryptPasswordHasher`
- `HmacRefreshTokenHasher`
- `NestAccessTokenService`
- `NestRefreshTokenService`

Инфраструктурные модули:

- `PrismaModule`
- `RabbitModule`

## Модули сервиса

### `AuthModule`

Содержит RabbitRPC handlers для:

- register
- login
- get current user
- refresh session
- deactivate user

Поднимает:

- `JwtModule` через `getJWTConfig()`
- `PrismaModule`
- `RabbitModule`
- `RmqEventEmitterModule` с `sourceService = auth-service` и default exchange `efko.auth.events`

### `UserModule`

Содержит handlers для:

- `AuthGetUsersQuery`
- `AuthUpdateUserCommand`

### `AppModule`

Включает:

- `ConfigModule` global
- `LoggerModule` (`nestjs-pino`)
- глобальный `AllExceptionsFilter`
- `AuthModule`
- `UserModule`
- `PrismaModule`
- `RabbitModule`

## Команды и queries

### RabbitMQ commands

Контроллер `AuthController` принимает:

- `AuthRegisterUserCommand`
- `AuthLoginUserCommand`
- `AuthRefreshSessionCommand`
- `AuthDeactivateUserCommand`

Контроллер `UserController` принимает:

- `AuthUpdateUserCommand`

### RabbitMQ queries

`AuthController`:

- `AuthGetCurrentUserQuery`

`UserController`:

- `AuthGetUsersQuery`

Общие свойства обработчиков:

- очереди `auth-service.commands.queue` и `auth-service.queries.queue`
- exchanges `efko.auth.commands` и `efko.auth.queries`
- quorum queues
- `ValidationPipe` на command handlers с `transform`, `whitelist`, `forbidNonWhitelisted`
- корреляция берется из заголовков через `getRpcCorrelationId(...)`

## Бизнес-поведение по use case'ам

### Регистрация

`RegisterUserUseCase`:

- проверяет уникальность email через `UserRepository.findByEmail`
- хэширует пароль через `PasswordHasher`
- создает `UserEntity`
- сохраняет пользователя в Postgres через Prisma repository
- публикует событие `AuthUserCreatedEvent` в `efko.auth.events`

### Вход

`LoginUserUseCase`:

- ищет пользователя по email
- отклоняет вход, если пользователь не найден или деактивирован
- сверяет пароль через `PasswordHasher.compare`
- генерирует access token и refresh token параллельно
- сохраняет refresh token через `RefreshTokenService.saveRefreshToken`

### Обновление сессии

`RefreshSessionUseCase`:

- вычисляет HMAC/hash от входящего refresh token
- ищет сессию по хэшу
- отклоняет revoked/expired/not found токены
- повторно проверяет активность пользователя
- удаляет старую запись refresh token
- генерирует новую пару токенов
- сохраняет новый refresh token

Это rotation-модель: refresh token одноразовый, старая запись удаляется при успешном refresh.

### Текущий пользователь

`GetCurrentUserUseCase`:

- читает пользователя по `userId`
- возвращает только активного пользователя
- деактивированный пользователь трактуется как `USER_NOT_FOUND`

### Список пользователей

`GetUsersUseCase`:

- читает всех пользователей через `findAll()`
- маппит сущности в контрактную схему

### Обновление пользователя

`UpdateUserUseCase`:

- загружает текущую сущность
- пересобирает `UserEntity` через `hydrate(...)`
- применяет частичное обновление email, fullName, role, employeeId
- сохраняет изменения через `UserRepository.update`

### Деактивация

`DeactivateUserUseCase`:

- загружает пользователя
- деактивирует сущность
- параллельно:
  - обновляет пользователя
  - удаляет все refresh token пользователя
- публикует событие `AuthUserDeactivatedEvent`

## Хранение данных

Сервис использует PostgreSQL через Prisma.

### Таблица `users`

Поля по `schema.prisma`:

- `id` UUID
- `email` unique
- `password_hash`
- `full_name`
- `role`
- `is_active`
- `employee_id` nullable
- `created_at`
- `updated_at`

Роли хранятся как enum `user_role`:

- `admin`
- `manager`
- `analyst`
- `shift_manager`
- `employee`

### Таблица `refresh_tokens`

Поля:

- `id` UUID
- `user_id`
- `token_hash`
- `expires_at`
- `is_revoked`
- `created_at`

Связи и индексы:

- `RefreshToken.userId -> User.id`
- `onDelete: Cascade`
- индексы по `userId` и `expiresAt`

### Что именно хранится

- access token в БД не хранится
- refresh token хранится только в виде hash
- пароль хранится только в виде bcrypt hash

## Интеграции

### RabbitMQ

`getRMQConfig()` объявляет:

- exchanges:
  - `efko.auth.commands`
  - `efko.auth.queries`
  - `efko.auth.events`
- queues:
  - `auth-service.commands.queue`
  - `auth-service.queries.queue`
  - `auth-service.events.queue`

Настройки:

- quorum queues
- `prefetchCount = 32`
- `persistent` publish
- `connectionInitOptions.wait = false`

### JWT

`NestAccessTokenService` использует `JwtService.signAsync/verifyAsync`. Конфигурация берется из:

- `JWT_ACCESS_SECRET`
- `JWT_ACCESS_TTL`
- `JWT_ACCESS_ISSUER`

Payload access token по коду включает:

- `sub`
- `email`
- `role`

### Хэширование и криптография

- password hashing вынесен в `BcryptPasswordHasher`
- refresh token генерируется как `crypto.randomBytes(32).toString('base64url')`
- перед сохранением refresh token хэшируется через `RefreshTokenHasher`
- TTL refresh token вычисляется из `JWT_REFRESH_TTL`

### Внешние контракты и события

Сервис зависит от общих контрактов в `@efko-kernel/contracts` и `@efko-kernel/interfaces`.

Публикуемые события:

- `AuthUserCreatedEvent`
- `AuthUserDeactivatedEvent`

## Обработка ошибок

### Доменные ошибки

`AUTH_ERROR_HTTP_STATUS_MAP` задает соответствия:

- `INVALID_EMAIL` -> `400`
- `INVALID_FULL_NAME` -> `400`
- `USER_ALREADY_EXISTS` -> `409`
- `USER_NOT_FOUND` -> `404`
- `INVALID_CREDENTIALS` -> `401`
- `USER_ALREADY_DEACTIVATED` -> `409`
- `REFRESH_TOKEN_REVOKED` -> `401`
- `REFRESH_TOKEN_EXPIRED` -> `401`
- `INVALID_REFRESH_TOKEN` -> `401`

### RPC-ошибки

`authRpcErrorInterceptor` преобразует `AuthError` и `HttpException` в `RpcErrorResponse` с полями:

- `error.code`
- `error.message`
- `error.statusCode`

Это позволяет `gateway` и другим клиентам стабильно маппить ошибки в HTTP/consumer semantics.

### HTTP-ошибки

`AllExceptionsFilter`:

- в HTTP-контексте возвращает JSON с `statusCode` и `message`
- в non-HTTP контексте формирует `RpcErrorResponse`
- неизвестные исключения отдает как internal error через базовый filter

## Observability и logging

- `nestjs-pino` используется как основной logger
- в dev-режиме пишется `logs/auth-service.log`
- все use case'ы логируют ключевые шаги через `Logger`
- в лог-контекст добавляется `correlationId` и доменные атрибуты через `buildLogContext(...)`
- Swagger поднимается на `/api`, JSON — `/api/swagger/json`

Логируются, в частности:

- попытки регистрации и логина
- поиск пользователя/сессии
- генерация и сохранение токенов
- деактивация пользователя

## Встраивание в систему

`auth-service` — источник истины для идентичности пользователя в системе:

- `gateway` использует его как resolver профиля по JWT `sub`
- административные операции по пользователям тоже проходят через него
- другие сервисы могут подписываться на `efko.auth.events`
- `employeeId` связывает auth-пользователя с кадровым контуром

## Допущения и пробелы по коду

- В сервисе нет отдельного health/readiness endpoint.
- В `schema.prisma` datasource не содержит URL; он ожидается из runtime-конфигурации Prisma/Nest окружения.
- HTTP-приложение поднимается, но в коде нет явного публичного REST API для бизнес-операций; основной интерфейс сервиса — RabbitMQ RPC.
