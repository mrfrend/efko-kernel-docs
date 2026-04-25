# EFKO Kernel: обзор проекта

## Назначение

`efko-kernel` — Nx-монорепозиторий с несколькими NestJS-сервисами, разделенными по доменам:

- `gateway` — публичная HTTP-точка входа и оркестратор запросов.
- `auth-service` — идентификация, аутентификация, refresh-сессии и жизненный цикл пользователей.
- `personnel` — кадровый домен: подразделения, должности, сотрудники, шаблоны смен.
- `production` — производственный домен: продукты, заказы, выпуск, качество, остатки, продажи, датчики, KPI.
- `etl` — прием данных из внешних систем, нормализация, трансформация и доставка во внутренние домены.

Кроме сервисов, в репозитории есть общие библиотеки с контрактами, интерфейсами и инфраструктурными NestJS-утилитами.

## Структура монорепозитория

- `apps/*` — deployable-сервисы.
- `libs/contracts` — общие команды, queries и события для межсервисного взаимодействия.
- `libs/interfaces` — общие TypeScript-интерфейсы, enum-ы и RPC-структуры.
- `libs/nest-utils` — переиспользуемая инфраструктура: auth guards/decorators, HTTP logging и exception filters, RPC helper-ы, RabbitMQ event emitter и shared transactional outbox.

Все сервисы оформлены как Nx applications с локальными `project.json`. Сборка идет через `webpack-cli`, а на уровне workspace подключены Nx plugins для webpack, ESLint и Jest.

## Топология рантайма

### Внешние точки входа

- `gateway` поднимает HTTP API под `/api` и публикует Swagger.
- `auth-service` тоже поднимает HTTP API и Swagger, поэтому может использоваться как напрямую, так и за gateway.
- `personnel`, `production` и `etl` также стартуют как Nest HTTP-приложения, но их основная прикладная интеграция построена вокруг сервисных вызовов и очередей.

### Шина интеграции

Основной межсервисный транспорт — RabbitMQ.

- `auth-service` использует `efko.auth.commands`, `efko.auth.queries`, `efko.auth.events`.
- `personnel` использует `efko.personnel.commands`, `efko.personnel.queries`, `efko.personnel.events`.
- `production` использует `efko.production.commands`, `efko.production.queries`, `efko.production.events`.
- `etl` определяет `efko.etl.commands` и `efko.etl.events`.
- `gateway` выступает RPC-клиентом для доменных сервисов и проксирует туда команды и queries.

Очереди объявляются явно и используют quorum queue options.

Важно: в коде `gateway` есть proxy для `production-service`, но текущий `getRMQConfig()` явно декларирует только `auth` и `personnel` exchanges/queues. Это стоит рассматривать как текущую архитектурную несогласованность между wiring и ожидаемым поведением.

## Роли сервисов

### Gateway

`gateway` агрегирует HTTP-модули для auth, personnel, production и ETL. На краю системы он применяет request ID middleware, логирование, обработку ошибок, cache и rate limiting. Дальше запросы отправляются в RabbitMQ command/query exchanges или, в случае ETL, проксируются в HTTP API ETL-сервиса.

### Auth Service

`auth-service` отвечает за регистрацию, логин, выпуск и refresh токенов, чтение/обновление пользователя и деактивацию. Хранение реализовано через Prisma, а доменные события публикуются в RabbitMQ.

### Personnel

`personnel` владеет кадровыми агрегатами и использует Prisma-репозитории плюс shared outbox для надежной публикации доменных событий после записи состояния.

### Production

`production` владеет операционными производственными данными. Feature-модули покрывают продукты, заказы, выпуск, продажи, остатки, качество, датчики и KPI. Для событийного взаимодействия используется shared outbox поверх Prisma.

### ETL

`etl` — интеграционная граница для внешних систем вроде `1C:ZUP`, `1C:ERP`, `MES`, `SCADA`, `LIMS`. Его pipeline разделен на:

- `ingestion` — прием данных, auth/role checks, парсинг файлов и первичная валидация;
- `transform` — source-specific transformer-ы и mapper-ы в канонические payload-ы;
- `imports` — хранение raw imports и transformation logs;
- `dispatch` — доставка во внутренние сервисы по HTTP/RabbitMQ.

## Хранилища данных

Проект использует polyglot persistence.

- `auth-service` использует Prisma с моделями `User` и `RefreshToken`.
- `personnel` использует Prisma с моделями `Department`, `Position`, `Employee`, `ShiftScheduleTemplate`, `OutboxMessage`.
- `production` использует Prisma с моделями `Product`, `ProductionOrder`, `ProductionOutput`, `Sale`, `Inventory`, `QualityResult`, `SensorReading`, `OutboxMessage`.
- `etl` использует MongoDB через Mongoose как минимум для `RawImport` и `TransformationLog`, а также GridFS-подобное файловое хранение для импортируемых файлов.

Prisma-сервисы получают datasource URLs из env через `prisma.config.ts`.

## Общие архитектурные паттерны

### Contracts-first границы

`libs/contracts` задает команды, queries и события для gateway и доменных сервисов. За счет этого proxy-слой и обработчики внутри сервисов опираются на одни и те же message shapes и topic names.

### Корреляция запросов и логирование

Во всем workspace стандартизировано structured logging через `nestjs-pino`. Для трассировки используются `RequestIdMiddleware`, HTTP logging interceptors и service-specific exception filters либо shared HTTP filters.

### Валидация на границах

Контроллеры и bootstrap-слои активно используют Nest `ValidationPipe` с `transform`, `whitelist` и `forbidNonWhitelisted`. Это показывает намерение отсекать невалидные payload еще до входа в application use case.

### Transactional outbox

`libs/nest-utils` содержит общий outbox module, repository abstraction, Prisma-backed implementation и periodic publisher. `personnel` и `production` подключают этот модуль, чтобы сохранять события транзакционно и публиковать их асинхронно.

### Разделение commands, queries и events

Именование exchange-ей и структура контроллеров отражают CQRS-подобный подход:

- commands меняют состояние;
- queries читают данные;
- events уведомляют другие сервисы о завершившихся доменных изменениях.

Этот подход виден и в раскладке shared contracts, и в RabbitMQ wiring.

## Сквозной поток данных

Упрощенно система работает так:

1. Клиент приходит в `gateway` по HTTP, либо внешние данные заходят через `etl`.
2. `gateway` валидирует запрос и пересылает его в доменный сервис через RabbitMQ commands/queries.
3. Доменные сервисы исполняют use case-ы поверх Prisma-репозиториев и доменных сущностей.
4. Для событийных сценариев `personnel` и `production` сохраняют outbox records и публикуют события асинхронно.
5. `etl` принимает внешние записи, превращает их в canonical payload-ы и отправляет в downstream-домены.

## Карта документации

Подробная документация по сервисам лежит в:

- `docs/gateway.md`
- `docs/auth-service.md`
- `docs/personnel.md`
- `docs/production.md`
- `docs/etl.md`

Этот файл описывает систему на уровне композиции и сквозных механизмов, а service-level файлы фиксируют конкретные API, модули, обработчики и операционные детали.

## Допущения и ограничения

- Обзор собран по структуре репозитория, Nest-модулям, контрактам, схемам и инфраструктурному коду, без доступа к deployment manifests и runtime-окружениям.
- В репозитории видны HTTP bootstrap-ы всех сервисов, но основная интеграционная модель доменных сервисов выглядит как RabbitMQ RPC + event publishing.
- Секреты, реальные env-значения и внутренние URL сознательно не включались в документацию.
