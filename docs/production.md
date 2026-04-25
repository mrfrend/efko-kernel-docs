# Production Service

## Назначение

`production` обслуживает производственный домен: справочник продукции, производственные заказы, выпуск, качество, складские остатки, продажи, показания датчиков и агрегированные KPI. Сервис реализован как NestJS-приложение с RabbitMQ RPC-интерфейсом, PostgreSQL через Prisma и событийной интеграцией через RabbitMQ events/outbox.

## Как сервис встроен в систему

- Команды принимает через exchange `efko.production.commands`.
- Запросы принимает через exchange `efko.production.queries`.
- Доменные события публикует в exchange `efko.production.events`.
- Очереди команд и запросов разделены: `production-service.commands.queue` и `production-service.queries.queue`.
- Внешний HTTP есть только у bootstrap c префиксом `api`; бизнес-операции в коде экспонируются как RabbitRPC, а не как REST-контроллеры.

## Основные модули

- `ProductsModule`: создание и выборка продуктов.
- `OrdersModule`: создание производственных заказов, смена статуса, чтение одного заказа и списка.
- `OutputModule`: фиксация выпуска по партиям и выборка выпуска.
- `QualityModule`: запись лабораторных результатов и выборка качества.
- `InventoryModule`: upsert складских остатков и выборка остатков.
- `SalesModule`: запись продаж и агрегированная/детальная аналитика по продажам.
- `SensorsModule`: запись телеметрии и выборка показаний.
- `KpiModule`: расчёт агрегированных производственных KPI.
- `ProductionInfrastructureModule`: wiring Prisma-репозиториев, use case-ов и `RmqEventEmitterService`.
- `OutboxModule`: интеграция общего outbox поверх Prisma с публикацией в `efko.production.events`.

## API, команды и queries

### Commands

- `ProductionCreateProductCommand`: создать продукт; при наличии `sourceSystemId` use case сначала пытается сделать upsert по внешнему идентификатору.
- `ProductionCreateOrderCommand`: создать производственный заказ по продукту.
- `ProductionUpdateOrderStatusCommand`: перевести заказ в `start`, `complete` или `cancel`.
- `ProductionRecordOutputCommand`: записать выпуск партии.
- `ProductionRecordQualityResultCommand`: записать результат контроля качества по партии.
- `ProductionUpsertInventoryCommand`: создать или обновить остаток.
- `ProductionRecordSaleCommand`: записать продажу.
- `ProductionRecordSensorReadingCommand`: записать показание датчика.

### Queries

- `ProductionGetProductsQuery`
- `ProductionGetOrdersQuery`
- `ProductionGetOrderQuery`
- `ProductionGetOutputQuery`
- `ProductionGetQualityQuery`
- `ProductionGetInventoryQuery`
- `ProductionGetSalesQuery`
- `ProductionGetSalesSummaryQuery`
- `ProductionGetSensorsQuery`
- `ProductionGetKpiQuery`

Все RPC handlers используют `ValidationPipe` с `transform`, `whitelist`, `forbidNonWhitelisted`, читают correlation/user metadata из Rabbit headers и обёрнуты в `productionRpcErrorInterceptor`.

## Основная бизнес-логика

- Продукты создаются через доменную модель `ProductEntity`; при ETL-импортах возможен update существующей записи по `sourceSystemId`, а не только insert.
- Заказы ссылаются на продукт; создание и смена статуса идут через `ProductionOrderEntity`, которая валидирует допустимые переходы статусов.
- Выпуск хранится по заказу, продукту и номеру партии; номер партии валидируется через `LotNumber`.
- Качество хранится как набор результатов по параметрам с расчётом `inSpec` и доменным `decision`.
- Показания датчиков после записи прогоняются через `SensorAnomalyDetector`; при выходе за пределы публикуется отдельное событие аномалии.
- KPI считаются на чтении: `totalOutput`, `defectRate`, `completedOrders`, `totalOrders`, `oeeEstimate`. В текущем коде `oeeEstimate` фактически равен доле завершённых заказов, а не полноценному OEE.

## Хранение данных

PostgreSQL/Prisma, основные таблицы:

- `products`: код, категория, бренд, единица измерения, срок годности, признак обязательного контроля качества, `source_system_id`.
- `production_orders`: внешний номер заказа, продукт, целевое/фактическое количество, линия, плановые и фактические даты, статус.
- `production_output`: заказ, продукт, номер партии, количество, статус качества, дата выпуска, смена.
- `sales`: внешний идентификатор продажи, продукт, клиент, количество, сумма, дата, регион, канал.
- `inventory`: продукт, склад, партия, количество, единица измерения, время последнего обновления.
- `quality_results`: партия, продукт, параметр, значение, пределы, `in_spec`, решение, дата теста.
- `sensor_readings`: устройство, линия, параметр, значение, единица, качество, время измерения.
- `outbox_messages`: event type, payload, correlation id, статус отправки, retry counters, error message.

## Интеграции

- RabbitMQ RPC для всех команд и запросов production-домена.
- RabbitMQ events для доменных событий:
  - через `EventEmitterService` публикуются события заказов, выпуска, качества, продаж, датчиков и аномалий;
  - через `OutboxMessageRepository` записываются события по продуктам в `outbox_messages`, а затем доставляются общим outbox-механизмом.
- ETL ожидаемо является важным upstream: его mapper-ы бьют в `ProductionCreateProductCommand`, `ProductionCreateOrderCommand`, `ProductionRecordOutputCommand`, `ProductionRecordQualityResultCommand`, `ProductionUpsertInventoryCommand`, `ProductionRecordSaleCommand`, `ProductionRecordSensorReadingCommand`.

## Обработка ошибок

- Доменные ошибки наследуются от `ProductionError` и мапятся в transport-safe ответ через `productionRpcErrorInterceptor`.
- Явные маппинги:
  - `INVALID_*` -> `400`
  - `*_NOT_FOUND` -> `404`
  - конфликтные состояния (`PRODUCT_CODE_ALREADY_EXISTS`, `INVALID_ORDER_STATUS_TRANSITION`) -> `409`
- Валидационные ошибки Nest `ValidationPipe` тоже упаковываются в RPC error response с HTTP-like `statusCode`.

## Observability и logging

- Логирование через `nestjs-pino`.
- В dev-режиме лог дублируется в `logs/production.log` и очищается на старте процесса.
- Контроллеры пишут topic, `correlationId`, `userId`, `userRole`.
- Use case-ы логируют ключевые бизнес-операции через `buildLogContext(...)`.
- Сигнал об аномалиях датчиков логируется отдельным `warn`.

## Зависимости

- NestJS
- Prisma + PostgreSQL
- `@golevelup/nestjs-rabbitmq`
- `nestjs-pino`
- `@efko-kernel/contracts`
- `@efko-kernel/interfaces`
- `@efko-kernel/nest-utils`

## Наблюдения и пробелы по коду

- В коде сервиса нет полноценного HTTP API для бизнес-операций, несмотря на запуск HTTP-сервера.
- Для событий используется смешанная модель: часть use case-ов публикует события сразу через emitter, а часть пишет в outbox.
- В `GetKpiUseCase` выход для `rejected` определяется по строке `qualityStatus === 'rejected'`; это стоит учитывать как зависимость от формата маппинга enum/репозитория.
