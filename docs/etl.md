# ETL Service

## Назначение

`etl` принимает сырые данные из внешних систем, валидирует и нормализует их, преобразует в canonical-команды доменной системы, диспатчит их в downstream сервисы через RabbitMQ RPC и сохраняет журнал импорта. Это интеграционный сервис между внешними системами (`ZUP`, `ERP`, `MES`, `SCADA`, `LIMS`) и внутренними сервисами `production` и `personnel`.

## Как сервис встроен в систему

- Поднимает HTTP API с глобальным префиксом `api/v1`.
- Основной контроллер расположен по маршруту `/etl`.
- Для импорта и просмотра истории использует JWT/authz (`@Auth(UserRole.ADMIN)`).
- Для доставки в downstream сервисы использует RabbitMQ request/reply.
- Собственные события об импорте публикует в `efko.etl.events`.

## Основные модули

- `IngestionModule`: HTTP-вход, auth, приём JSON и файлов, запуск pipeline.
- `TransformModule`: реестр transformer-ов по source system.
- `ImportsModule`: журнал импортов и логов трансформации в Mongo.
- `DispatchModule`: RabbitMQ dispatch с retry/backoff.
- `RabbitModule`: Rabbit transport и `EventEmitterService`.
- `MongoModule` / Mongoose infrastructure: схемы `RawImport`, `TransformationLog`, GridFS-хранилище исходных файлов.

## HTTP API

- `POST /api/v1/etl/import`
  - импорт массива записей в JSON;
  - тело: `source_system`, `import_type`, `data`.
- `POST /api/v1/etl/import/file`
  - импорт файла (`xlsx` или `json`) через multipart `file`;
  - ограничение размера файла: 20 MB.
- `GET /api/v1/etl/imports`
  - список импортов с фильтрами `source_system`, `status`, `limit`.
- `GET /api/v1/etl/imports/:id`
  - детали импорта плюс статистика `success/error/skipped`.
- `GET /api/v1/etl/imports/:id/file`
  - скачать исходный файл из GridFS.
- `POST /api/v1/etl/imports/:id/retry`
  - повторный запуск только для импорта со статусом `FAILED`.

Глобально включены `ValidationPipe`, `LoggingInterceptor`, `HttpExceptionFilter` и `RequestIdMiddleware`.

## Ingestion

- `IngestionController` извлекает request metadata из HTTP headers и передаёт их дальше в pipeline.
- `IngestionService.processImport(...)`:
  - проверяет корректность `sourceSystem`;
  - создаёт новую запись импорта или переиспользует существующую при retry;
  - поднимает статус `PROCESSING`;
  - получает import schema по паре `source_system` + `import_type`;
  - нормализует и валидирует входные записи через `validateRecords`.
- Поддерживаемые source system и import types по коду:
  - `ZUP`: `employees`, `departments`, `positions`
  - `ERP`: `products`
  - `MES`: `orders`
  - `SCADA`: `sensors`
  - `LIMS`: `quality`
- Схемы поддерживают alias-ы входных полей, включая 1C-ключи на русском, и coercion типов (`string`, `number`, `date-string`, `boolean`).

## Transform

- `TransformerRegistry` выбирает transformer по `SourceSystem`.
- Реализованы transformer-ы:
  - `ZupTransformer`
  - `ErpTransformer`
  - `MesTransformer`
  - `ScadaTransformer`
  - `LimsTransformer`
- Трансформация идёт в canonical records вида:
  - `entityType`
  - `sourceId`
  - `canonicalId`
  - `payload`
  - `exchange`
  - `routingKey`
- Важные маршруты downstream:
  - `ZUP` -> команды `personnel`
  - `ERP`, `MES`, `SCADA`, `LIMS` -> команды `production`
- Mapper-ы в коде переводят внешние enum-ы в внутренние доменные enum-ы и выставляют routing key из `@efko-kernel/contracts`.
- Особый случай `SCADA`: alarms распознаются на уровне transformer-а, но в комментарии явно указано, что alarms только логируются и не диспатчатся как сущности.

## Imports

- `ImportsService` хранит запись импорта в коллекции `RawImport`.
- `RawImport` содержит:
  - `source_system`
  - `import_type`
  - `raw_payload`
  - `status`
  - `records_count`
  - массив `errors`
  - `processed_at`
  - ссылку на исходный файл и его формат, если импорт шёл из файла.
- Каждый dispatch логируется в `TransformationLog`:
  - `import_id`
  - `entity_type`
  - `source_id`
  - `canonical_id`
  - `transformation_result` (`success` / `error` / `skipped`)
  - `error_message`
- Для retry старые transformation logs удаляются, а импорт переводится обратно в `PROCESSING`.

## Dispatch

- `DispatchService` использует `amqpConnection.request(...)`.
- Доставка идёт с exponential backoff:
  - `maxRetries: 3`
  - `baseDelayMs: 1000`
  - `maxDelayMs: 30000`
  - `backoffMultiplier: 2`
- В headers передаётся `correlationId`, если он есть в request metadata.
- Если dispatch конкретной canonical-записи падает, сервис:
  - фиксирует ошибку в `TransformationLog`;
  - добавляет запись в `errors` импорта;
  - продолжает обработку остальных записей.
- Итоговый статус импорта:
  - `FAILED`, если transform не дал ни одной canonical-записи;
  - `FAILED`, если все dispatch-операции упали;
  - `COMPLETED`, если есть хотя бы частичный успех.

## Хранение данных

MongoDB / Mongoose:

- `RawImport`: журнал сырых импортов и их статусов.
- `TransformationLog`: построчный лог трансформации и dispatch результата.
- GridFS bucket `etl_source_files`: хранение исходных файлов импорта.

GridFS metadata включает:

- `sourceSystem`
- `importType`
- `format`
- `uploadedBy`
- `mime`
- `uploadedAt`

## Интеграции

- Входящие системы:
  - `ZUP`
  - `ERP`
  - `MES`
  - `SCADA`
  - `LIMS`
- Исходящие сервисы:
  - `personnel` через `efko.personnel.commands`
  - `production` через `efko.production.commands`
- Собственные события ETL:
  - `EtlImportCompletedEvent`
  - `EtlImportFailedEvent`
  - публикуются в `efko.etl.events`

### Примеры бизнес-маршрутизации

- `ZUP employees` -> `PersonnelCreateEmployeeCommand`
- `ZUP departments` -> `PersonnelCreateDepartmentCommand`
- `ZUP positions` -> `PersonnelCreatePositionCommand`
- `ZUP shift templates` поддерживаются mapper-ом, но отдельная schema для такого `import_type` в `IMPORT_SCHEMAS` в текущем файле не описана
- `ERP products` -> `ProductionCreateProductCommand`
- `ERP sales` и `inventory` поддерживаются mapper-ом, но в `IMPORT_SCHEMAS` для них сейчас нет отдельных схем
- `MES orders` -> `ProductionCreateOrderCommand`
- `MES output` поддерживается mapper-ом, но отдельная schema/import type в `IMPORT_SCHEMAS` сейчас не описаны
- `SCADA sensors` -> `ProductionRecordSensorReadingCommand`
- `LIMS quality` -> `ProductionRecordQualityResultCommand`

## Обработка ошибок

- HTTP ошибки идут через глобальный `HttpExceptionFilter`.
- Пустой upload-файл, отсутствие import schema и невалидный retry-status дают `BadRequestException`/`NotFoundException`.
- Ошибки transform и dispatch не обязательно валят весь импорт немедленно: сервис стремится обработать максимум записей и сохраняет частичные ошибки в журнал.
- Если файл уже сохранён в GridFS, но импорт дальше не создался, `FileIngestionService` выполняет compensating delete.

## Observability и logging

- Логирование через `nestjs-pino`, dev-лог в `logs/etl.log`.
- `RequestIdMiddleware` навешивается на все маршруты.
- `LoggingInterceptor` пишет HTTP request metadata и duration.
- Сервис насыщенно использует `buildLogContext(...)` для связи логов по `correlationId`/request metadata.
- Логируются:
  - старт импорта;
  - результат трансформации;
  - ошибки dispatch конкретных записей;
  - финальный статус импорта;
  - сохранение/получение/удаление файлов в GridFS.

## Зависимости

- NestJS
- Mongoose + MongoDB + GridFS
- RabbitMQ
- JWT auth из `@efko-kernel/nest-utils`
- `xlsx` для Excel parsing
- `@efko-kernel/contracts`
- `@efko-kernel/interfaces`

## Наблюдения и пробелы по коду

- `IMPORT_SCHEMAS` и mapper-ы покрывают разные множества import types: mapper-ы уже умеют больше, чем разрешает текущая схема в ingestion.
- В документации по supported imports выше отражено именно то, что реально следует из `IMPORT_SCHEMAS` и mapper-ов на текущий момент.
- ETL не хранит доменные сущности downstream; его персистентность ограничена журналом импортов, логом трансформации и исходными файлами.
