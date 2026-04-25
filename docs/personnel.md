# Personnel Service

## Назначение

`personnel` обслуживает кадровый домен: оргструктуру, должности, сотрудников и шаблоны смен. Сервис построен на NestJS, хранит состояние в PostgreSQL через Prisma, принимает команды и queries через RabbitMQ RPC и публикует кадровые события в RabbitMQ.

## Как сервис встроен в систему

- Команды принимает через `efko.personnel.commands`.
- Запросы принимает через `efko.personnel.queries`.
- События публикует через `efko.personnel.events`.
- Очереди разделены на `personnel-service.commands.queue` и `personnel-service.queries.queue`.
- В `AppModule` подключён `RmqEventEmitterModule` с `sourceService: 'personnel'`; дополнительно подключён Prisma-based outbox.

## Основные модули

- `DepartmentsModule`: подразделения и иерархия оргструктуры.
- `PositionsModule`: должности внутри подразделений.
- `EmployeesModule`: сотрудники, изменение данных и увольнение.
- `ShiftTemplatesModule`: шаблоны сменных графиков.
- `PrismaModule`: доступ к БД и репозиториям.
- `OutboxModule`: публикация событий из `outbox_messages` в `efko.personnel.events`.
- `RabbitModule`: transport-конфигурация RabbitMQ.

## API, команды и queries

### Commands

- `PersonnelCreateDepartmentCommand`
- `PersonnelUpdateDepartmentCommand`
- `PersonnelCreatePositionCommand`
- `PersonnelUpdatePositionCommand`
- `PersonnelCreateEmployeeCommand`
- `PersonnelUpdateEmployeeCommand`
- `PersonnelTerminateEmployeeCommand`
- `PersonnelCreateShiftTemplateCommand`
- `PersonnelUpdateShiftTemplateCommand`

### Queries

- `PersonnelGetDepartmentsQuery`
- `PersonnelGetPositionsQuery`
- `PersonnelGetEmployeesQuery`
- `PersonnelGetShiftTemplatesQuery`

Все RabbitRPC handlers работают через `ValidationPipe` и `personnelRpcErrorInterceptor`, логируют topic и request metadata (`correlationId`, `userId`, `userRole`).

## Основная бизнес-логика

- Подразделения поддерживают иерархию `parent -> children`; при создании/обновлении `parentId` и `headEmployeeId` можно передавать не только UUID, но и бизнес-идентификаторы, которые резолвятся через `resolveEntityId(...)`.
- Должность жёстко привязана к подразделению; create flow валидирует уникальность `code` и существование подразделения.
- Сотрудник связан и с подразделением, и с должностью; `CreateEmployeeUseCase` валидирует оба reference и использует value objects `PersonnelNumber` и `FullName`.
- Увольнение реализовано отдельным use case: меняет статус сотрудника и ставит дату увольнения.
- Шаблоны смен содержат тип смены, время начала/окончания и `workDaysPattern`; время и паттерн валидируются value object-ами.
- Для ETL-импортов `create` use case-ы по подразделениям, должностям и сотрудникам сначала пытаются делать upsert по `sourceSystemId`.

## Хранение данных

PostgreSQL/Prisma, основные таблицы:

- `departments`: имя, код, тип, `parent_id`, `head_employee_id`, `source_system_id`.
- `positions`: title, code, `department_id`, `source_system_id`.
- `employees`: табельный номер, ФИО, дата рождения, подразделение, должность, даты приёма/увольнения, тип занятости, статус, `source_system_id`.
- `shift_schedule_templates`: имя шаблона, тип смены, время начала/окончания, паттерн рабочих дней.
- `outbox_messages`: события кадрового домена для асинхронной публикации.

## Интеграции

- RabbitMQ RPC для всех кадровых команд и queries.
- RabbitMQ events:
  - подразделения, должности и сотрудники при create/update часто пишут события через outbox;
  - увольнение и часть операций используют `EventEmitterService` напрямую.
- ETL является важным upstream:
  - ZUP mapper направляет данные в `PersonnelCreateDepartmentCommand`, `PersonnelCreatePositionCommand`, `PersonnelCreateEmployeeCommand`, `PersonnelCreateShiftTemplateCommand`;
  - create use case-ы умеют обновлять существующие записи по `sourceSystemId`, что снижает дубли при повторном импорте.

## Обработка ошибок

- Доменные ошибки наследуются от `PersonnelError`.
- Для RPC используется `personnelRpcErrorInterceptor`, который приводит доменные и HTTP ошибки к структуре `{ error: { code, message, statusCode } }`.
- Для HTTP-слоя подключён `AllExceptionsFilter`; в HTTP-контексте он возвращает JSON с `statusCode` и `message`.
- Основные маппинги:
  - ошибки формата (`INVALID_*`) -> `400`
  - ошибки отсутствующих сущностей -> `404`
  - конфликтные состояния (`*_ALREADY_EXISTS`, `EMPLOYEE_ALREADY_TERMINATED`, `EMPLOYEE_NOT_ACTIVE`) -> `409`

## Observability и logging

- Логирование через `nestjs-pino`.
- В dev-режиме лог пишется в `logs/personnel.log` и очищается на старте.
- Bootstrap включает `enableShutdownHooks()` и глобальный exception filter.
- Контроллеры логируют RPC topic и request metadata.
- В `EmployeesController` есть дополнительный debug/error лог для `PersonnelCreateEmployeeCommand`, включая сериализацию payload и ошибки выполнения.

## Зависимости

- NestJS
- Prisma + PostgreSQL
- `@golevelup/nestjs-rabbitmq`
- `nestjs-pino`
- `@efko-kernel/contracts`
- `@efko-kernel/interfaces`
- `@efko-kernel/nest-utils`

## Наблюдения и пробелы по коду

- Use case-ы используют смешанную схему публикации событий: outbox для части create/update операций и direct publish для части команд.
- В `DepartmentsModule`, `EmployeesModule`, `PositionsModule` явно не импортируется `OutboxModule`, хотя create use case-ы зависят от `OutboxMessageRepository`; корректность разрешения зависимости предполагает наличие глобального провайдера в общем composition root.
- Как и в `production`, внешний HTTP-сервер поднимается, но бизнес-операции экспонированы как RabbitRPC, а не REST.
