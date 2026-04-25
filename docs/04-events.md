# Events Catalog

Полный каталог всех доменных событий в системе EFKO Kernel.

## Обзор

Система использует событийную архитектуру для асинхронной коммуникации между сервисами. События публикуются в RabbitMQ exchanges и потребляются downstream сервисами.

### Exchanges событий

- `efko.auth.events` — события auth-service
- `efko.personnel.events` — события personnel-service
- `efko.production.events` — события production-service
- `efko.etl.events` — события etl-service

### Публикация событий

События публикуются двумя способами:

1. **Transactional Outbox** — для personnel и production сервисов
   - Событие записывается в таблицу `outbox_messages` в той же транзакции с доменными данными
   - Периодический publisher (`OutboxPeriodicPublisher`) читает PENDING события и публикует в RabbitMQ
   - Статус обновляется на SENT при успешной публикации
   - Повторная публикация при ошибках (retry)

2. **Direct Publish** — для auth-service и некоторых сценариев
   - Событие публикуется сразу через `RmqEventEmitterService`
   - Используется для критически важных событий, требующих немедленной доставки

### Потребление событий

Downstream сервисы подписываются на соответствующие exchanges и обрабатывают события:
- Для синхронизации данных
- Для триггера бизнес-процессов
- Для уведомлений и аналитики

---

## Auth Events

События аутентификации и управления пользователями.

### AuthUserCreatedEvent

Публикуется при регистрации нового пользователя.

**Exchange:** `efko.auth.events`  
**Routing Key:** `auth.user.created.event`  
**Когда публикуется:** После успешной регистрации пользователя в `RegisterUserUseCase`

#### Payload

```typescript
{
  id: string;           // UUID пользователя
  email: string;        // Email пользователя
  fullName: string;     // Полное имя
  role: UserRole;       // Роль пользователя
  isActive: boolean;    // Статус активности
  employeeId: string | null; // ID сотрудника (если привязан)
}
```

#### Пример

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "email": "ivan@example.com",
  "fullName": "Иванов Иван",
  "role": "ADMIN",
  "isActive": true,
  "employeeId": null
}
```

#### Кто может потреблять

- Personnel Service — для синхронизации с кадровыми данными
- Analytics Service — для аналитики по пользователям

---

### AuthUserDeactivatedEvent

Публикуется при деактивации пользователя.

**Exchange:** `efko.auth.events`  
**Routing Key:** `auth.user.deactivated.event`  
**Когда публикуется:** После успешной деактивации в `DeactivateUserUseCase`

#### Payload

```typescript
{
  id: string;           // UUID пользователя
  email: string;        // Email пользователя
  deactivatedAt: string; // ISO datetime деактивации
}
```

#### Пример

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "email": "ivan@example.com",
  "deactivatedAt": "2025-01-15T10:30:00Z"
}
```

#### Кто может потреблять

- Personnel Service — для увольнения сотрудника
- Production Service — для отзыва прав доступа
- Gateway — для инвалидации сессий в кэше

---

## Personnel Events

События кадрового домена: подразделения, должности, сотрудники, смены.

### PersonnelEmployeeCreatedEvent

Публикуется при приеме сотрудника на работу.

**Exchange:** `efko.personnel.events`  
**Routing Key:** `personnel.employee.created.event`  
**Когда публикуется:** После успешного создания в `CreateEmployeeUseCase`

#### Payload

```typescript
{
  id: string;              // UUID сотрудника
  personnelNumber: string; // Табельный номер
  fullName: string;        // Полное имя
  departmentId: string;    // UUID подразделения
  positionId: string;      // UUID должности
  status: EmployeeStatus;  // Статус сотрудника
}
```

#### Пример

```json
{
  "id": "d4e5f6a7-b8c9-0123-defa-234567890123",
  "personnelNumber": "EMP-0001",
  "fullName": "Иванов Иван Иванович",
  "departmentId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "positionId": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "status": "ACTIVE"
}
```

#### Кто может потреблять

- Auth Service — для создания учетной записи сотрудника
- Access Control Service — для выдачи прав доступа

---

### PersonnelEmployeeUpdatedEvent

Публикуется при обновлении данных сотрудника.

**Exchange:** `efko.personnel.events`  
**Routing Key:** `personnel.employee.updated.event`  
**Когда публикуется:** После успешного обновления в `UpdateEmployeeUseCase`

#### Payload

```typescript
{
  id: string;              // UUID сотрудника
  fullName: string;        // Полное имя
  departmentId: string;    // UUID подразделения
  positionId: string;      // UUID должности
  employmentType: EmploymentType; // Тип занятости
  status: EmployeeStatus;  // Статус сотрудника
}
```

#### Пример

```json
{
  "id": "d4e5f6a7-b8c9-0123-defa-234567890123",
  "fullName": "Иванов Иван Петрович",
  "departmentId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "positionId": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "employmentType": "FULL_TIME",
  "status": "ACTIVE"
}
```

#### Кто может потреблять

- Auth Service — для обновления профиля пользователя
- Access Control Service — для обновления прав доступа

---

### PersonnelEmployeeTerminatedEvent

Публикуется при увольнении сотрудника.

**Exchange:** `efko.personnel.events`  
**Routing Key:** `personnel.employee.terminated.event`  
**Когда публикуется:** После успешного увольнения в `TerminateEmployeeUseCase`

#### Payload

```typescript
{
  id: string;               // UUID сотрудника
  terminationDate: string;  // Дата увольнения (ISO date)
  status: EmployeeStatus;    // Статус (TERMINATED)
}
```

#### Пример

```json
{
  "id": "d4e5f6a7-b8c9-0123-defa-234567890123",
  "terminationDate": "2025-06-30",
  "status": "TERMINATED"
}
```

#### Кто может потреблять

- Auth Service — для деактивации учетной записи
- Production Service — для отзыва прав доступа
- Access Control Service — для отзыва всех разрешений

---

### PersonnelDepartmentCreatedEvent

Публикуется при создании подразделения.

**Exchange:** `efko.personnel.events`  
**Routing Key:** `personnel.department.created.event`  
**Когда публикуется:** После успешного создания в `CreateDepartmentUseCase`

#### Payload

```typescript
{
  id: string;           // UUID подразделения
  name: string;         // Название подразделения
  code: string;         // Код подразделения
  type: DepartmentType; // Тип подразделения
  parentId: string | null | undefined; // UUID родительского подразделения
}
```

#### Пример

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "Производственный цех №1",
  "code": "PROD-001",
  "type": "DIVISION",
  "parentId": null
}
```

#### Кто может потреблять

- Analytics Service — для аналитики по оргструктуре
- Reporting Service — для отчетов по подразделениям

---

### PersonnelDepartmentUpdatedEvent

Публикуется при обновлении подразделения.

**Exchange:** `efko.personnel.events`  
**Routing Key:** `personnel.department.updated.event`  
**Когда публикуется:** После успешного обновления в `UpdateDepartmentUseCase`

#### Payload

```typescript
{
  id: string;           // UUID подразделения
  name: string;         // Название подразделения
  code: string;         // Код подразделения
  type: DepartmentType; // Тип подразделения
  headEmployeeId: string | null | undefined; // UUID руководителя
}
```

#### Пример

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "Производственный цех №2",
  "code": "PROD-001",
  "type": "DIVISION",
  "headEmployeeId": "d4e5f6a7-b8c9-0123-defa-234567890123"
}
```

#### Кто может потреблять

- Analytics Service — для обновления аналитики
- Reporting Service — для обновления отчетов

---

### PersonnelPositionCreatedEvent

Публикуется при создании должности.

**Exchange:** `efko.personnel.events`  
**Routing Key:** `personnel.position.created.event`  
**Когда публикуется:** После успешного создания в `CreatePositionUseCase`

#### Payload

```typescript
{
  id: string;           // UUID должности
  title: string;        // Название должности
  code: string;         // Код должности
  departmentId: string; // UUID подразделения
}
```

#### Пример

```json
{
  "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "title": "Оператор станка",
  "code": "OP-001",
  "departmentId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

#### Кто может потреблять

- Analytics Service — для аналитики по должностям
- Access Control Service — для создания ролей по должностям

---

### PersonnelPositionUpdatedEvent

Публикуется при обновлении должности.

**Exchange:** `efko.personnel.events`  
**Routing Key:** `personnel.position.updated.event`  
**Когда публикуется:** После успешного обновления в `UpdatePositionUseCase`

#### Payload

```typescript
{
  id: string;           // UUID должности
  title: string;        // Название должности
  code: string;         // Код должности
  departmentId: string; // UUID подразделения
}
```

#### Пример

```json
{
  "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "title": "Старший оператор станка",
  "code": "OP-001",
  "departmentId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

#### Кто может потреблять

- Analytics Service — для обновления аналитики
- Access Control Service — для обновления ролей

---

### PersonnelShiftTemplateCreatedEvent

Публикуется при создании шаблона смены.

**Exchange:** `efko.personnel.events`  
**Routing Key:** `personnel.shift-template.created.event`  
**Когда публикуется:** После успешного создания в `CreateShiftTemplateUseCase`

#### Payload

```typescript
{
  id: string;              // UUID шаблона
  name: string;            // Название шаблона
  shiftType: ShiftType;    // Тип смены
  startTime: string;       // Время начала (HH:MM)
  endTime: string;         // Время окончания (HH:MM)
  workDaysPattern: string; // Паттерн рабочих дней (бинарная строка)
}
```

#### Пример

```json
{
  "id": "e5f6a7b8-c9d0-1234-efab-345678901234",
  "name": "Дневная смена",
  "shiftType": "DAY",
  "startTime": "08:00",
  "endTime": "20:00",
  "workDaysPattern": "1111100"
}
```

#### Кто может потреблять

- Shift Service — для создания графиков смен
- Production Service — для планирования производства

---

### PersonnelShiftTemplateUpdatedEvent

Публикуется при обновлении шаблона смены.

**Exchange:** `efko.personnel.events`  
**Routing Key:** `personnel.shift-template.updated.event`  
**Когда публикуется:** После успешного обновления в `UpdateShiftTemplateUseCase`

#### Payload

```typescript
{
  id: string;              // UUID шаблона
  name: string;            // Название шаблона
  shiftType: ShiftType;    // Тип смены
  startTime: string;       // Время начала (HH:MM)
  endTime: string;         // Время окончания (HH:MM)
  workDaysPattern: string; // Паттерн рабочих дней
}
```

#### Пример

```json
{
  "id": "e5f6a7b8-c9d0-1234-efab-345678901234",
  "name": "Ночная смена",
  "shiftType": "NIGHT",
  "startTime": "20:00",
  "endTime": "08:00",
  "workDaysPattern": "1111100"
}
```

#### Кто может потреблять

- Shift Service — для обновления графиков смен
- Production Service — для обновления планирования

---

### PersonnelShiftAssignedEvent

Публикуется при назначении сотрудника на смену.

**Exchange:** `efko.personnel.events`  
**Routing Key:** `personnel.shift.assigned.event`  
**Когда публикуется:** При назначении сотрудника на конкретную смену

#### Payload

```typescript
{
  assignmentId: string;      // UUID назначения
  employeeId: string;        // UUID сотрудника
  personnelNumber: string;    // Табельный номер
  shiftTemplateId: string;   // UUID шаблона смены
  shiftType: ShiftType;       // Тип смены
  shiftDate: string;          // Дата смены (ISO date)
  startTime: string;           // Время начала (ISO datetime)
  endTime: string;            // Время окончания (ISO datetime)
  assignedAt: string;         // Время назначения (ISO datetime)
  assignedByUserId?: string;  // UUID пользователя, назначившего смену
}
```

#### Пример

```json
{
  "assignmentId": "f6a7b8c9-d0e1-2345-fabc-456789012345",
  "employeeId": "d4e5f6a7-b8c9-0123-defa-234567890123",
  "personnelNumber": "EMP-0001",
  "shiftTemplateId": "e5f6a7b8-c9d0-1234-efab-345678901234",
  "shiftType": "DAY",
  "shiftDate": "2025-01-20",
  "startTime": "2025-01-20T08:00:00Z",
  "endTime": "2025-01-20T20:00:00Z",
  "assignedAt": "2025-01-15T10:00:00Z",
  "assignedByUserId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

#### Кто может потреблять

- Access Service — для выдачи пропусков в определенные периоды
- Production Service — для планирования персонала на линиях

---

## Production Events

События производственного домена: продукты, заказы, выпуск, качество, датчики.

### ProductionProductCreatedEvent

Публикуется при создании продукта.

**Exchange:** `efko.production.events`  
**Routing Key:** `production.product.created.event`  
**Когда публикуется:** После успешного создания в `CreateProductUseCase`

#### Payload

```typescript
{
  id: string;              // UUID продукта
  code: string;            // Код продукта
  name: string;            // Название продукта
  category: ProductCategory; // Категория продукта
}
```

#### Пример

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "code": "PROD-001",
  "name": "Творог 5%",
  "category": "FINISHED_PRODUCT"
}
```

#### Кто может потреблять

- ETL Service — для синхронизации с внешними системами
- Analytics Service — для аналитики по продуктам

---

### ProductionProductUpdatedEvent

Публикуется при обновлении продукта.

**Exchange:** `efko.production.events`  
**Routing Key:** `production.product.updated.event`  
**Когда публикуется:** После успешного обновления продукта

#### Payload

```typescript
{
  id: string;              // UUID продукта
  code: string;            // Код продукта
  name: string;            // Название продукта
  category: ProductCategory; // Категория продукта
}
```

#### Пример

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "code": "PROD-001",
  "name": "Творог 5% (обновленный)",
  "category": "FINISHED_PRODUCT"
}
```

#### Кто может потреблять

- ETL Service — для синхронизации с внешними системами
- Analytics Service — для обновления аналитики

---

### ProductionOrderCreatedEvent

Публикуется при создании производственного заказа.

**Exchange:** `efko.production.events`  
**Routing Key:** `production.order.created.event`  
**Когда публикуется:** После успешного создания в `CreateOrderUseCase`

#### Payload

```typescript
{
  id: string;              // UUID заказа
  externalOrderId: string;  // Внешний номер заказа
  productId: string;       // UUID продукта
  status: OrderStatus;     // Статус заказа
}
```

#### Пример

```json
{
  "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "externalOrderId": "EXT-ORDER-001",
  "productId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "PLANNED"
}
```

#### Кто может потреблять

- Personnel Service — для планирования персонала
- Analytics Service — для аналитики по заказам

---

### ProductionOrderStatusUpdatedEvent

Публикуется при обновлении статуса заказа.

**Exchange:** `efko.production.events`  
**Routing Key:** `production.order.status-updated.event`  
**Когда публикуется:** После успешного обновления статуса в `UpdateOrderStatusUseCase`

#### Payload

```typescript
{
  id: string;              // UUID заказа
  status: OrderStatus;     // Новый статус
  actualQuantity: number | null; // Фактическое количество
  actualStart: string | null; // Фактическое начало (ISO datetime)
  actualEnd: string | null;   // Фактическое окончание (ISO datetime)
}
```

#### Пример

```json
{
  "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "status": "COMPLETED",
  "actualQuantity": 950,
  "actualStart": "2025-01-02T06:00:00Z",
  "actualEnd": "2025-01-09T18:00:00Z"
}
```

#### Кто может потреблять

- Personnel Service — для освобождения/назначения персонала
- Analytics Service — для аналитики выполнения заказов
- Inventory Service — для обновления остатков

---

### ProductionOutputRecordedEvent

Публикуется при регистрации выпуска продукции.

**Exchange:** `efko.production.events`  
**Routing Key:** `production.output.recorded.event`  
**Когда публикуется:** После успешной записи в `RecordOutputUseCase`

#### Payload

```typescript
{
  id: string;         // UUID выпуска
  orderId: string;    // UUID заказа
  lotNumber: string;  // Номер партии
  quantity: number;   // Количество
}
```

#### Пример

```json
{
  "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "orderId": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "lotNumber": "LOT-2025-001",
  "quantity": 500
}
```

#### Кто может потреблять

- Quality Service — для инициирования контроля качества
- Inventory Service — для обновления остатков
- Analytics Service — для аналитики выпуска

---

### ProductionSaleRecordedEvent

Публикуется при регистрации продажи.

**Exchange:** `efko.production.events`  
**Routing Key:** `production.sale.recorded.event`  
**Когда публикуется:** После успешной записи в `RecordSaleUseCase`

#### Payload

```typescript
{
  id: string;         // UUID продажи
  externalId: string; // Внешний ID продажи
  productId: string;  // UUID продукта
  amount: number;     // Сумма продажи
  channel: SaleChannel; // Канал продаж
}
```

#### Пример

```json
{
  "id": "d4e5f6a7-b8c9-0123-defa-234567890123",
  "externalId": "SALE-001",
  "productId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "amount": 50000,
  "channel": "RETAIL"
}
```

#### Кто может потреблять

- Inventory Service — для обновления остатков
- Analytics Service — для аналитики продаж
- Finance Service — для финансового учета

---

### ProductionInventoryUpdatedEvent

Публикуется при обновлении остатков на складе.

**Exchange:** `efko.production.events`  
**Routing Key:** `production.inventory.updated.event`  
**Когда публикуется:** После успешного upsert в `UpsertInventoryUseCase`

#### Payload

```typescript
{
  id: string;           // UUID остатка
  productId: string;    // UUID продукта
  warehouseCode: string; // Код склада
  quantity: number;     // Количество
}
```

#### Пример

```json
{
  "id": "e5f6a7b8-c9d0-1234-efab-345678901234",
  "productId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "warehouseCode": "WH-01",
  "quantity": 200
}
```

#### Кто может потреблять

- Analytics Service — для аналитики остатков
- Alert Service — для уведомлений о низких остатках

---

### ProductionQualityResultRecordedEvent

Публикуется при регистрации результата контроля качества.

**Exchange:** `efko.production.events`  
**Routing Key:** `production.quality-result.recorded.event`  
**Когда публикуется:** После успешной записи в `RecordQualityResultUseCase`

#### Payload

```typescript
{
  id: string;         // UUID результата
  lotNumber: string;  // Номер партии
  productId: string;  // UUID продукта
  inSpec: boolean;    // Соответствует норме
  decision: QualityDecision; // Решение
}
```

#### Пример

```json
{
  "id": "f6a7b8c9-d0e1-2345-fabc-456789012345",
  "lotNumber": "LOT-2025-001",
  "productId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "inSpec": true,
  "decision": "APPROVED"
}
```

#### Кто может потреблять

- Analytics Service — для аналитики качества
- Alert Service — для уведомлений о браке
- Production Service — для блокировки выпуска бракованной продукции

---

### ProductionSensorReadingRecordedEvent

Публикуется при записи показания датчика.

**Exchange:** `efko.production.events`  
**Routing Key:** `production.sensor-reading.recorded.event`  
**Когда публикуется:** После успешной записи в `RecordSensorReadingUseCase`

#### Payload

```typescript
{
  id: string;              // UUID показания
  deviceId: string;         // ID устройства
  productionLine: string;  // Производственная линия
  parameterName: string;   // Название параметра
  quality: SensorQuality;  // Качество сигнала
}
```

#### Пример

```json
{
  "id": "a7b8c9d0-e1f2-3456-abcd-567890123456",
  "deviceId": "SENSOR-01",
  "productionLine": "Line-1",
  "parameterName": "temperature",
  "quality": "GOOD"
}
```

#### Кто может потреблять

- Analytics Service — для аналитики показаний
- Alert Service — для уведомлений об отклонениях

---

### ProductionSensorAnomalyDetectedEvent

Публикуется при обнаружении аномалии в показаниях датчика.

**Exchange:** `efko.production.events`  
**Routing Key:** `production.sensor.anomaly.event`  
**Когда публикуется:** При детекции аномалии в `SensorAnomalyDetector`

#### Payload

```typescript
{
  readingId: string;          // UUID показания
  deviceId: string;            // ID устройства
  productionLine: string;      // Производственная линия
  parameterName: string;       // Название параметра
  value: number;               // Значение
  unit: string;                // Единица измерения
  quality: SensorQuality;      // Качество сигнала
  anomalyType: SensorAnomalyType; // Тип аномалии
  severity: SensorAnomalySeverity; // Тяжесть аномалии
  reason: string;              // Причина
  lowerLimit?: number;         // Нижний предел
  upperLimit?: number;         // Верхний предел
  detectedAt: string;          // Время обнаружения (ISO datetime)
}
```

#### Пример

```json
{
  "readingId": "a7b8c9d0-e1f2-3456-abcd-567890123456",
  "deviceId": "SENSOR-01",
  "productionLine": "Line-1",
  "parameterName": "temperature",
  "value": 95.5,
  "unit": "°C",
  "quality": "GOOD",
  "anomalyType": "VALUE_OUT_OF_RANGE",
  "severity": "HIGH",
  "reason": "Temperature exceeds upper limit of 85°C",
  "lowerLimit": 60,
  "upperLimit": 85,
  "detectedAt": "2025-01-05T10:30:00Z"
}
```

#### Кто может потреблять

- Alert Service — для немедленных уведомлений
- Analytics Service — для анализа аномалий
- Production Service — для автоматической остановки линии

#### SensorAnomalyType

- `VALUE_OUT_OF_RANGE` — Значение вне допустимого диапазона
- `BAD_QUALITY` — Плохое качество сигнала
- `MISSING_DATA` — Отсутствующие данные
- `DEVIATION_SPIKE` — Резкое отклонение

#### SensorAnomalySeverity

- `LOW` — Низкая
- `MEDIUM` — Средняя
- `HIGH` — Высокая
- `CRITICAL` — Критическая

---

## ETL Events

События интеграции с внешними системами.

### EtlImportCompletedEvent

Публикуется при успешном завершении импорта.

**Exchange:** `efko.etl.events`  
**Routing Key:** `etl.import.completed.event`  
**Когда публикуется:** После успешного завершения ETL pipeline

#### Payload

```typescript
{
  importId: string;      // ID импорта (MongoDB ObjectId)
  sourceSystem: string;  // Источник системы
  importType: string;    // Тип импорта
  recordsCount: number; // Количество записей
  successCount: number; // Количество успешных
  errorCount: number;    // Количество ошибок
  completedAt: string;   // Время завершения (ISO datetime)
}
```

#### Пример

```json
{
  "importId": "507f1f77bcf86cd799439011",
  "sourceSystem": "ZUP",
  "importType": "employees",
  "recordsCount": 150,
  "successCount": 145,
  "errorCount": 5,
  "completedAt": "2025-01-15T14:30:00Z"
}
```

#### Кто может потреблять

- Analytics Service — для аналитики импортов
- Notification Service — для уведомлений об успешном импорте

---

### EtlImportFailedEvent

Публикуется при неудачном завершении импорта.

**Exchange:** `efko.etl.events`  
**Routing Key:** `etl.import.failed.event`  
**Когда публикуется:** После неудачного завершения ETL pipeline

#### Payload

```typescript
{
  importId: string;      // ID импорта (MongoDB ObjectId)
  sourceSystem: string;  // Источник системы
  importType: string;    // Тип импорта
  recordsCount: number; // Количество записей
  errorMessage: string;  // Сообщение об ошибке
  failedAt: string;      // Время неудачи (ISO datetime)
}
```

#### Пример

```json
{
  "importId": "507f1f77bcf86cd799439011",
  "sourceSystem": "ZUP",
  "importType": "employees",
  "recordsCount": 150,
  "errorMessage": "Failed to dispatch to personnel-service: timeout",
  "failedAt": "2025-01-15T14:30:00Z"
}
```

#### Кто может потреблять

- Alert Service — для немедленных уведомлений
- Analytics Service — для анализа проблем импорта
- Notification Service — для уведомлений об ошибке

---

## Потребление событий

### Подписка на события

Для потребления событий из RabbitMQ:

```typescript
@RabbitSubscribe({
  exchange: 'efko.personnel.events',
  routingKey: 'personnel.employee.created.event',
  queue: 'my-service.personnel.events.queue',
})
async handleEmployeeCreatedEvent(payload: PersonnelEmployeeCreatedEvent) {
  // Обработка события
}
```

### Обработка ошибок

При ошибке обработки события:
- Сообщение возвращается в очередь с `reject(false)` для повторной попытки
- После N неудачных попыток сообщение перемещается в DLQ
- Статус outbox записи обновляется на FAILED

### Корреляция

Все события содержат метаданные для корреляции:
- `correlationId` — связывает с исходным запросом
- `timestamp` — время публикации
- `sourceService` — сервис-источник

---

## Мониторинг событий

### RabbitMQ Management UI

Отслеживайте события через RabbitMQ Management UI:
- Проверьте наличие сообщений в очередях
- Мониторьте rate публикации
- Проверьте DLQ (Dead Letter Queue) для неудачных сообщений

### Outbox таблица

Мониторинг через SQL:
```sql
SELECT * FROM outbox_messages 
WHERE status = 'FAILED' 
ORDER BY created_at DESC 
LIMIT 100;
```

### Логи

ETL и domain сервисы логируют:
- Публикацию событий
- Ошибки публикации
- Retry попытки
