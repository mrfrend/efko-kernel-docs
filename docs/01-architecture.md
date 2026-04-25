# Архитектура системы EFKO Kernel

Полное описание архитектуры микросервисной системы EFKO Kernel, включая топологию сервисов, коммуникационные паттерны и инфраструктурные решения.

## Обзор системы

EFKO Kernel — Nx-монорепозиторий с микросервисной архитектурой на NestJS. Система состоит из 5 доменных сервисов, разделенных по предметным областям, и 3 общих библиотек.

### Доменные сервисы

- **gateway** — публичный HTTP API Gateway, единая точка входа для внешних клиентов
- **auth-service** — идентификация, аутентификация, управление пользователями и сессиями
- **personnel** — кадровый домен: подразделения, должности, сотрудники, шаблоны смен
- **production** — производственный домен: продукты, заказы, выпуск, качество, остатки, продажи, датчики, KPI
- **etl** — интеграция с внешними системами (1C-ZUP, 1C-ERP, MES, SCADA, LIMS)

### Общие библиотеки

- **libs/contracts** — типизированные контракты для межсервисного взаимодействия (commands, queries, events)
- **libs/interfaces** — общие TypeScript интерфейсы и enum-ы
- **libs/nest-utils** — инфраструктурные утилиты (logging, metrics, tracing, auth guards, RPC helpers)

## Топология рантайма

### Внешние точки входа

Система имеет следующие внешние точки входа:

1. **Gateway HTTP API** (`/api`)
   - Единая точка входа для всех внешних клиентов
   - Публикует Swagger документацию
   - Проксирует запросы в доменные сервисы через RabbitMQ RPC или HTTP

2. **Auth Service HTTP API** (опционально)
   - Может использоваться напрямую для аутентификации
   - Публикует Swagger документацию
   - Основной интерфейс — RabbitMQ RPC

3. **ETL HTTP API** (`/api/v1/etl`)
   - Специализированный endpoint для импорта данных
   - Поддерживает JSON и multipart file upload
   - Требует роль ADMIN

### Шина интеграции (RabbitMQ)

Основной транспорт для межсервисной коммуникации — RabbitMQ.

#### Exchanges

Система использует следующие exchanges:

- `efko.auth.commands` — команды auth-service
- `efko.auth.queries` — запросы к auth-service
- `efko.auth.events` — события auth-service
- `efko.personnel.commands` — команды personnel-service
- `efko.personnel.queries` — запросы к personnel-service
- `efko.personnel.events` — события personnel-service
- `efko.production.commands` — команды production-service
- `efko.production.queries` — запросы к production-service
- `efko.production.events` — события production-service
- `efko.etl.commands` — команды etl-service
- `efko.etl.events` — события etl-service

#### Queues

Каждый сервис имеет свои очереди:

- `auth-service.commands.queue`
- `auth-service.queries.queue`
- `auth-service.events.queue`
- `personnel-service.commands.queue`
- `personnel-service.queries.queue`
- `personnel-service.events.queue`
- `production-service.commands.queue`
- `production-service.queries.queue`
- `production-service.events.queue`
- `etl-service.commands.queue` (если используется)

#### Настройки очередей

- **Quorum queues** — все очереди объявлены как quorum для надежности
- **Prefetch count** — 32 сообщений на потребителя
- **Persistent publish** — сообщения сохраняются на диск
- **Connection init** — `wait = false` для быстрого подключения

## Коммуникационные паттерны

### RPC (Request/Reply)

Gateway использует RabbitMQ RPC для синхронного вызова доменных сервисов:

```
Client HTTP Request
    ↓
Gateway (валидация, auth)
    ↓
RabbitMQ RPC (command/query exchange)
    ↓
Domain Service (обработка)
    ↓
RabbitMQ RPC (response)
    ↓
Gateway (нормализация ответа)
    ↓
Client HTTP Response
```

**Используется для:**
- Auth операций (register, login, refresh, get user)
- Personnel CRUD операций
- Production CRUD операций
- Query операций (чтение данных)

### Events (Fire-and-Forget)

Доменные сервисы публикуют события для асинхронной интеграции:

```
Domain Service (изменение состояния)
    ↓
Transactional Outbox (запись события в БД)
    ↓
Periodic Publisher (cron)
    ↓
RabbitMQ Event Exchange
    ↓
Downstream Consumers (подписчики)
```

**Используется для:**
- Уведомлений о создании/обновлении сущностей
- Синхронизации данных между сервисами
- Триггеров бизнес-процессов

### HTTP Proxy

Gateway использует прямой HTTP proxy для ETL сервиса:

```
Client HTTP Request
    ↓
Gateway (валидация, auth)
    ↓
HTTP Request to ETL Service
    ↓
ETL Service (обработка)
    ↓
HTTP Response
    ↓
Gateway (проксирование ответа)
    ↓
Client HTTP Response
```

**Используется для:**
- ETL операций (file upload, import status)
- Ситуаций, когда RPC не подходит

## Архитектурные паттерны

### CQRS (Command Query Responsibility Segregation)

Система разделяет операции на команды (write) и запросы (read):

- **Commands** — изменяют состояние системы
  - `efko.*.commands` exchanges
  - Примеры: `AuthRegisterUserCommand`, `PersonnelCreateEmployeeCommand`

- **Queries** — читают данные без изменений
  - `efko.*.queries` exchanges
  - Примеры: `AuthGetCurrentUserQuery`, `PersonnelGetEmployeesQuery`

- **Events** — уведомляют об изменениях
  - `efko.*.events` exchanges
  - Примеры: `AuthUserCreatedEvent`, `PersonnelEmployeeCreatedEvent`

### Transactional Outbox

Для надежной публикации событий используется паттерн outbox:

```
1. Начало транзакции
2. Изменение доменных данных
3. Запись события в OutboxMessage (в той же транзакции)
4. Коммит транзакции
5. Периодический publisher читает PENDING события
6. Публикация в RabbitMQ
7. Обновление статуса на SENT
```

**Преимущества:**
- Атомарность записи данных и события
- Повторная публикация при сбоях
- Отслеживание статуса доставки

**Реализация:**
- Таблица `outbox_messages` в PostgreSQL (personnel, production)
- `OutboxPeriodicPublisher` — cron задача
- Поля: eventType, payload, correlationId, status, retryCount, errorMessage

### Contracts-First

Все контракты между сервисами определены в `libs/contracts`:

- Команды и запросы — типизированные DTO
- События — типизированные payload
- Общие интерфейсы — в `libs/interfaces`

**Преимущества:**
- Типобезопасность на этапе компиляции
- Единый источник правды для контрактов
- Легкая генерация документации

### Polyglot Persistence

Система использует разные базы данных для разных задач:

- **PostgreSQL (Prisma)**
  - Auth Service: User, RefreshToken
  - Personnel Service: Department, Position, Employee, ShiftScheduleTemplate
  - Production Service: Product, ProductionOrder, ProductionOutput, Sale, Inventory, QualityResult, SensorReading

- **MongoDB (Mongoose)**
  - ETL Service: RawImport, TransformationLog, GridFS для файлов

## Хранилища данных

### PostgreSQL (Prisma)

Каждый сервис с PostgreSQL имеет свой Prisma schema:

- **Auth Service** — `apps/auth-service/prisma/schema.prisma`
- **Personnel Service** — `apps/personnel/prisma/schema.prisma`
- **Production Service** — `apps/production/prisma/schema.prisma`

Клиент генерируется в `apps/<service>/src/generated/prisma`.

### MongoDB (Mongoose)

ETL сервис использует MongoDB:

- **RawImport** — журнал импортов
- **TransformationLog** — лог трансформации
- **GridFS** — хранение исходных файлов

## Observability Stack

### Логирование

- **Logger:** nestjs-pino (structured logging)
- **Dev mode:** запись в `logs/<service>.log`
- **Prod mode:** отправка в Loki через pino-loki
- **Корреляция:** requestId propagation через все сервисы

### Трассировка

- **Instrumentation:** OpenTelemetry
- **Exporter:** OTLP HTTP
- **Auto-instrumentations:** Node.js стандартные библиотеки
- **RabbitMQ:** отдельный instrumentation

### Метрики

- **Metrics:** Prometheus (@willsoto/nestjs-prometheus)
- **Endpoint:** `/metrics`
- **Custom metrics:** бизнес-метрики через Prometheus client

### Мониторинг

- **Grafana** — визуализация метрик и логов
- **Loki** — агрегированное логирование
- **Tempo** — распределенная трассировка
- **Prometheus** — сбор метрик

## Инфраструктурные модули

### nest-utils библиотека

Ключевые экспорты из `@efko-kernel/nest-utils`:

- `createLoggerModuleOptions(name)` — конфигурация Pino logger
- `MetricsModule` — Prometheus metrics endpoint
- `initTracing / shutdownTracing` — OpenTelemetry setup
- `OutboxModule` — transactional outbox
- `RmqEventEmitterModule / RmqEventEmitterService` — typed RMQ publishing
- `BaseProxyService / HttpProxyService` — base classes for gateway proxies
- `AuthGuard, RoleGuard, AUTH_USER_RESOLVER` — JWT auth guards
- `AllExceptionsFilter, HttpExceptionFilter, LoggingInterceptor, RequestIdMiddleware`
- `buildLogContext` — добавление correlation/request ID в логи
- RPC helpers: `requestWithTimeout`, `runRpcSafely`, `rpcErrorMapper`

## Сквозной поток данных

### Типичный запрос клиента

```
1. Клиент отправляет HTTP запрос в Gateway
2. Gateway валидирует JWT токен (если требуется)
3. Gateway проверяет роль пользователя (если требуется)
4. Gateway формирует RabbitMQ command/query
5. Domain Service обрабатывает команду/запрос
6. Domain Service использует Prisma для работы с БД
7. Domain Service пишет события в outbox (если нужно)
8. Domain Service возвращает ответ
9. Gateway нормализует ответ
10. Клиент получает HTTP ответ
```

### ETL поток данных

```
1. Клиент загружает файл в ETL Service
2. ETL сохраняет файл в MongoDB GridFS
3. ETL создает запись RawImport
4. Ingestion: парсинг файла, валидация
5. Transform: применение source-specific mapper-а
6. Dispatch: отправка canonical команд в downstream сервисы
7. Downstream сервисы обрабатывают команды
8. ETL обновляет статус RawImport
9. ETL публикует событие об окончании импорта
```

## Роли сервисов

### Gateway

- Единая точка входа для внешних клиентов
- Аутентификация и авторизация на краю системы
- Валидация DTO на границах
- Нормализация ошибок
- Rate limiting
- Корреляция запросов (requestId)
- Проксирование в доменные сервисы

### Auth Service

- Источник истины для идентичности пользователя
- Регистрация и вход пользователей
- Выпуск и rotation JWT токенов
- Управление refresh токенами
- Профили пользователей
- Деактивация пользователей
- Публикация событий об изменениях пользователей

### Personnel Service

- Владеет кадровыми агрегатами
- Управление оргструктурой (подразделения)
- Управление должностями
- Управление сотрудниками
- Управление шаблонами смен
- Публикация кадровых событий через outbox

### Production Service

- Владеет производственными данными
- Управление продуктами
- Управление производственными заказами
- Фиксация выпуска продукции
- Управление продажами
- Управление складскими остатками
- Контроль качества
- Сбор показаний датчиков
- Расчет KPI
- Публикация производственных событий

### ETL Service

- Интеграционная граница для внешних систем
- Прием данных из 1C-ZUP, 1C-ERP, MES, SCADA, LIMS
- Нормализация и трансформация данных
- Доставка в downstream сервисы
- Журналирование импортов
- Повторная попытка при ошибках (retry)

## Безопасность

### Аутентификация

- JWT access token (короткий TTL)
- Refresh token (длинный TTL, httpOnly cookie)
- Rotation refresh токенов
- Password hashing (bcrypt)

### Авторизация

- Ролевая модель: ADMIN, MANAGER, SHIFT_MANAGER, ANALYST, EMPLOYEE
- RoleGuard на уровне контроллеров
- Проверка ролей в downstream сервисах

### CSRF Защита

- Double Submit Cookie паттерн для браузерных клиентов
- XSRF-TOKEN cookie (читаемый JS)
- X-CSRF-Token header для мутирующих запросов
- Автоматический пропуск для мобильных клиентов (без cookies)

### Rate Limiting

- Три профиля: short (20 req/1s), medium (100 req/10s), long (500 req/60s)
- Отдельные строгие лимиты для auth endpoints

## Развертывание

### Docker

Каждый сервис собирается в Docker image:

```bash
npm run docker:build:<service>
```

### Docker Compose

- `docker-compose.yml` — базовая инфраструктура (PostgreSQL, RabbitMQ, MongoDB)
- `docker-compose.prod.yml` — production конфигурация сервисов
- `docker-compose.observability.yml` — observability stack (Grafana, Loki, Tempo)

### Команды

```bash
# Запуск инфраструктуры
npm run infrastructure:up

# Запуск production стека
npm run prod:up

# Запуск с observability
npm run obs:up

# Логи production
npm run prod:logs
```

## Допущения и ограничения

- Gateway явно зависит от production-service, но RabbitMQ конфиг может не содержать production exchanges (архитектурная несогласованность)
- HTTP сервер поднимается во всех сервисах, но бизнес-операции экспонированы как RabbitRPC
- Отдельного health endpoint нет в некоторых сервисах
- Секреты и реальные env-значения не включены в документацию
