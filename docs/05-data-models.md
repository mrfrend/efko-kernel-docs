# Модели данных

Полное описание моделей данных из Prisma схем всех сервисов.

## Обзор

Система использует PostgreSQL с Prisma ORM для трех сервисов:
- **Auth Service** — пользователи и refresh токены
- **Personnel Service** — кадровые данные
- **Production Service** — производственные данные

Каждый сервис имеет собственную Prisma schema в `apps/<service>/prisma/schema.prisma`.

Prisma клиент генерируется в `apps/<service>/src/generated/prisma`.

---

## Auth Service Models

### User

Модель пользователя системы.

**Таблица:** `users`  
**Схема:** `apps/auth-service/prisma/schema.prisma`

#### Поля

| Поле | Тип | Описание | Constraints |
|------|-----|----------|-------------|
| `id` | UUID @id | Уникальный идентификатор | `@default(uuid())` |
| `email` | String @unique | Email пользователя | `@db.VarChar(255)` |
| `passwordHash` | String | Хеш пароля (bcrypt) | `@map("password_hash") @db.VarChar(255)` |
| `fullName` | String | Полное имя пользователя | `@map("full_name") @db.VarChar(150)` |
| `role` | UserRole | Роль пользователя | `@default(EMPLOYEE)` |
| `isActive` | Boolean | Статус активности | `@default(true) @map("is_active")` |
| `employeeId` | UUID? | ID связанного сотрудника (nullable) | `@map("employee_id") @db.Uuid` |
| `createdAt` | DateTime | Дата создания | `@default(now()) @map("created_at")` |
| `updatedAt` | DateTime | Дата обновления | `@updatedAt @map("updated_at")` |

#### Связи

- `refreshTokens` — один ко многим с RefreshToken

#### Индексы

- `email` — уникальный индекс

#### Prisma модель

```prisma
model User {
  id            String         @id @default(uuid()) @db.Uuid
  email         String         @unique @db.VarChar(255)
  passwordHash  String         @map("password_hash") @db.VarChar(255)
  fullName      String         @map("full_name") @db.VarChar(150)
  role          UserRole       @default(EMPLOYEE)
  isActive      Boolean        @default(true) @map("is_active")
  employeeId    String?        @map("employee_id") @db.Uuid
  createdAt     DateTime       @default(now()) @map("created_at")
  updatedAt     DateTime       @updatedAt @map("updated_at")
  refreshTokens RefreshToken[]

  @@map("users")
}
```

---

### RefreshToken

Модель refresh токена для обновления сессии.

**Таблица:** `refresh_tokens`  
**Схема:** `apps/auth-service/prisma/schema.prisma`

#### Поля

| Поле | Тип | Описание | Constraints |
|------|-----|----------|-------------|
| `id` | UUID @id | Уникальный идентификатор | `@default(uuid())` |
| `userId` | UUID | ID пользователя | `@map("user_id") @db.Uuid` |
| `tokenHash` | String | Хеш refresh токена | `@map("token_hash") @db.VarChar(255)` |
| `expiresAt` | DateTime | Дата истечения токена | `@map("expires_at")` |
| `isRevoked` | Boolean | Отозван ли токен | `@default(false) @map("is_revoked")` |
| `createdAt` | DateTime | Дата создания | `@default(now()) @map("created_at")` |

#### Связи

- `user` — многие к одному с User

#### Индексы

- `userId` — индекс
- `expiresAt` — индекс

#### Prisma модель

```prisma
model RefreshToken {
  id        String   @id @default(uuid()) @db.Uuid
  userId    String   @map("user_id") @db.Uuid
  tokenHash String   @map("token_hash") @db.VarChar(255)
  expiresAt DateTime @map("expires_at")
  isRevoked Boolean  @default(false) @map("is_revoked")
  createdAt DateTime @default(now()) @map("created_at")
  user      User     @relation(fields: [userId], references: [id], onDelete: Cascade)

  @@index([userId])
  @@index([expiresAt])
  @@map("refresh_tokens")
}
```

---

### UserRole

Enum ролей пользователя.

**Таблица:** `user_role`  
**Значения:**

| Значение | База данных | Описание |
|----------|-------------|----------|
| `ADMIN` | `admin` | Администратор |
| `MANAGER` | `manager` | Менеджер |
| `ANALYST` | `analyst` | Аналитик |
| `SHIFT_MANAGER` | `shift_manager` | Менеджер смены |
| `EMPLOYEE` | `employee` | Сотрудник |

```prisma
enum UserRole {
  ADMIN         @map("admin")
  MANAGER       @map("manager")
  ANALYST       @map("analyst")
  SHIFT_MANAGER @map("shift_manager")
  EMPLOYEE      @map("employee")

  @@map("user_role")
}
```

---

## Personnel Service Models

### Department

Модель подразделения организации.

**Таблица:** `departments`  
**Схема:** `apps/personnel/prisma/schema.prisma`

#### Поля

| Поле | Тип | Описание | Constraints |
|------|-----|----------|-------------|
| `id` | UUID @id | Уникальный идентификатор | `@default(uuid())` |
| `name` | String | Название подразделения | `@db.VarChar(150)` |
| `code` | String @unique | Код подразделения | `@db.VarChar(20)` |
| `type` | DepartmentType | Тип подразделения | |
| `parentId` | UUID? | ID родительского подразделения | `@map("parent_id") @db.Uuid` |
| `headEmployeeId` | UUID? | ID руководителя | `@map("head_employee_id") @db.Uuid` |
| `sourceSystemId` | String? | ID в исходной системе | `@map("source_system_id") @db.VarChar(20)` |
| `createdAt` | DateTime | Дата создания | `@default(now()) @map("created_at")` |
| `updatedAt` | DateTime | Дата обновления | `@updatedAt @map("updated_at")` |

#### Связи

- `parent` — многие к одному с Department (саморекурсия)
- `children` — один ко многим с Department (саморекурсия)
- `positions` — один ко многим с Position
- `employees` — один ко многим с Employee

#### Индексы

- `parentId` — индекс
- `code` — индекс
- `sourceSystemId` — индекс

#### Prisma модель

```prisma
model Department {
  id             String         @id @default(uuid()) @db.Uuid
  name           String         @db.VarChar(150)
  code           String         @unique @db.VarChar(20)
  type           DepartmentType
  parentId       String?        @map("parent_id") @db.Uuid
  headEmployeeId String?        @map("head_employee_id") @db.Uuid
  sourceSystemId String?        @map("source_system_id") @db.VarChar(20)
  createdAt      DateTime       @default(now()) @map("created_at")
  updatedAt      DateTime       @updatedAt @map("updated_at")

  parent   Department?  @relation("DepartmentHierarchy", fields: [parentId], references: [id])
  children Department[] @relation("DepartmentHierarchy")
  positions Position[]
  employees Employee[]

  @@index([parentId])
  @@index([code])
  @@index([sourceSystemId])
  @@map("departments")
}
```

---

### Position

Модель должности.

**Таблица:** `positions`  
**Схема:** `apps/personnel/prisma/schema.prisma`

#### Поля

| Поле | Тип | Описание | Constraints |
|------|-----|----------|-------------|
| `id` | UUID @id | Уникальный идентификатор | `@default(uuid())` |
| `title` | String | Название должности | `@db.VarChar(150)` |
| `code` | String @unique | Код должности | `@db.VarChar(20)` |
| `departmentId` | UUID | ID подразделения | `@map("department_id") @db.Uuid` |
| `sourceSystemId` | String? | ID в исходной системе | `@map("source_system_id") @db.VarChar(20)` |
| `createdAt` | DateTime | Дата создания | `@default(now()) @map("created_at")` |

#### Связи

- `department` — многие к одному с Department
- `employees` — один ко многим с Employee

#### Индексы

- `departmentId` — индекс
- `sourceSystemId` — индекс

#### Prisma модель

```prisma
model Position {
  id           String   @id @default(uuid()) @db.Uuid
  title        String   @db.VarChar(150)
  code         String   @unique @db.VarChar(20)
  departmentId String   @map("department_id") @db.Uuid
  sourceSystemId String? @map("source_system_id") @db.VarChar(20)
  createdAt    DateTime @default(now()) @map("created_at")

  department Department @relation(fields: [departmentId], references: [id])
  employees  Employee[]

  @@index([departmentId])
  @@index([sourceSystemId])
  @@map("positions")
}
```

---

### Employee

Модель сотрудника.

**Таблица:** `employees`  
**Схема:** `apps/personnel/prisma/schema.prisma`

#### Поля

| Поле | Тип | Описание | Constraints |
|------|-----|----------|-------------|
| `id` | UUID @id | Уникальный идентификатор | `@default(uuid())` |
| `personnelNumber` | String @unique | Табельный номер | `@map("personnel_number") @db.VarChar(10)` |
| `fullName` | String | Полное имя | `@map("full_name") @db.VarChar(150)` |
| `dateOfBirth` | DateTime | Дата рождения | `@map("date_of_birth") @db.Date` |
| `departmentId` | UUID | ID подразделения | `@map("department_id") @db.Uuid` |
| `positionId` | UUID | ID должности | `@map("position_id") @db.Uuid` |
| `hireDate` | DateTime | Дата приема | `@map("hire_date") @db.Date` |
| `terminationDate` | DateTime? | Дата увольнения | `@map("termination_date") @db.Date` |
| `employmentType` | EmploymentType | Тип занятости | `@map("employment_type")` |
| `status` | EmployeeStatus | Статус сотрудника | `@default(ACTIVE)` |
| `sourceSystemId` | String? @unique | ID в исходной системе | `@map("source_system_id") @db.VarChar(20)` |
| `createdAt` | DateTime | Дата создания | `@default(now()) @map("created_at")` |
| `updatedAt` | DateTime | Дата обновления | `@updatedAt @map("updated_at")` |

#### Связи

- `department` — многие к одному с Department
- `position` — многие к одному с Position

#### Индексы

- `departmentId` — индекс
- `positionId` — индекс
- `status` — индекс
- `personnelNumber` — индекс
- `sourceSystemId` — уникальный индекс

#### Prisma модель

```prisma
model Employee {
  id               String         @id @default(uuid()) @db.Uuid
  personnelNumber  String         @unique @map("personnel_number") @db.VarChar(10)
  fullName         String         @map("full_name") @db.VarChar(150)
  dateOfBirth      DateTime       @map("date_of_birth") @db.Date
  departmentId     String         @map("department_id") @db.Uuid
  positionId       String         @map("position_id") @db.Uuid
  hireDate         DateTime       @map("hire_date") @db.Date
  terminationDate  DateTime?      @map("termination_date") @db.Date
  employmentType   EmploymentType @map("employment_type")
  status           EmployeeStatus @default(ACTIVE)
  sourceSystemId   String?        @unique @map("source_system_id") @db.VarChar(20)
  createdAt        DateTime       @default(now()) @map("created_at")
  updatedAt        DateTime       @updatedAt @map("updated_at")

  department Department @relation(fields: [departmentId], references: [id])
  position   Position   @relation(fields: [positionId], references: [id])

  @@index([departmentId])
  @@index([positionId])
  @@index([status])
  @@index([personnelNumber])
  @@index([sourceSystemId])
  @@map("employees")
}
```

---

### ShiftScheduleTemplate

Модель шаблона смены.

**Таблица:** `shift_schedule_templates`  
**Схема:** `apps/personnel/prisma/schema.prisma`

#### Поля

| Поле | Тип | Описание | Constraints |
|------|-----|----------|-------------|
| `id` | UUID @id | Уникальный идентификатор | `@default(uuid())` |
| `name` | String | Название шаблона | `@db.VarChar(100)` |
| `shiftType` | ShiftType | Тип смены | `@map("shift_type")` |
| `startTime` | String | Время начала | `@map("start_time") @db.VarChar(5)` |
| `endTime` | String | Время окончания | `@map("end_time") @db.VarChar(5)` |
| `workDaysPattern` | String | Паттерн рабочих дней | `@map("work_days_pattern") @db.VarChar(20)` |
| `createdAt` | DateTime | Дата создания | `@default(now()) @map("created_at")` |

#### Prisma модель

```prisma
model ShiftScheduleTemplate {
  id              String    @id @default(uuid()) @db.Uuid
  name            String    @db.VarChar(100)
  shiftType       ShiftType @map("shift_type")
  startTime       String    @map("start_time") @db.VarChar(5)
  endTime         String    @map("end_time") @db.VarChar(5)
  workDaysPattern String    @map("work_days_pattern") @db.VarChar(20)
  createdAt       DateTime  @default(now()) @map("created_at")

  @@map("shift_schedule_templates")
}
```

---

### OutboxMessage (Personnel)

Модель outbox для надежной публикации событий.

**Таблица:** `outbox_messages`  
**Схема:** `apps/personnel/prisma/schema.prisma`

#### Поля

| Поле | Тип | Описание | Constraints |
|------|-----|----------|-------------|
| `id` | UUID @id | Уникальный идентификатор | `@default(uuid())` |
| `eventType` | String | Тип события | `@map("event_type") @db.VarChar(100)` |
| `payload` | Json | Payload события | |
| `correlationId` | String? | ID корреляции | `@map("correlation_id") @db.VarChar(100)` |
| `status` | OutboxStatus | Статус | `@default(PENDING)` |
| `retryCount` | Int | Количество попыток | `@default(0) @map("retry_count")` |
| `errorMessage` | String? | Сообщение об ошибке | `@map("error_message")` |
| `createdAt` | DateTime | Дата создания | `@default(now()) @map("created_at")` |
| `updatedAt` | DateTime | Дата обновления | `@updatedAt @map("updated_at")` |
| `processedAt` | DateTime? | Дата обработки | `@map("processed_at")` |

#### Индексы

- `status` — индекс
- `createdAt` — индекс
- `status, createdAt` — композитный индекс

#### Prisma модель

```prisma
model OutboxMessage {
  id            String       @id @default(uuid()) @db.Uuid
  eventType     String       @map("event_type") @db.VarChar(100)
  payload       Json
  correlationId String?      @map("correlation_id") @db.VarChar(100)
  status        OutboxStatus @default(PENDING)
  retryCount    Int          @default(0) @map("retry_count")
  errorMessage  String?      @map("error_message")
  createdAt     DateTime     @default(now()) @map("created_at")
  updatedAt     DateTime     @updatedAt @map("updated_at")
  processedAt   DateTime?    @map("processed_at")

  @@index([status])
  @@index([createdAt])
  @@index([status, createdAt])
  @@map("outbox_messages")
}
```

---

### Personnel Enums

#### DepartmentType

**Таблица:** `department_type`

| Значение | База данных | Описание |
|----------|-------------|----------|
| `DIVISION` | `division` | Дивизион |
| `DEPARTMENT` | `department` | Отдел |
| `SECTION` | `section` | Секция |
| `UNIT` | `unit` | Юнит |

#### EmploymentType

**Таблица:** `employment_type`

| Значение | База данных | Описание |
|----------|-------------|----------|
| `MAIN` | `main` | Основной |
| `PART_TIME` | `part_time` | Неполный |

#### EmployeeStatus

**Таблица:** `employee_status`

| Значение | База данных | Описание |
|----------|-------------|----------|
| `ACTIVE` | `active` | Активен |
| `TERMINATED` | `terminated` | Уволен |
| `ON_LEAVE` | `on_leave` | В отпуске |

#### ShiftType

**Таблица:** `shift_type`

| Значение | База данных | Описание |
|----------|-------------|----------|
| `DAY_SHIFT` | `day_shift` | Дневная смена |
| `NIGHT_SHIFT` | `night_shift` | Ночная смена |
| `ROTATING` | `rotating` | Ротирующаяся |

#### OutboxStatus

**Таблица:** `outbox_status`

| Значение | База данных | Описание |
|----------|-------------|----------|
| `PENDING` | `pending` | Ожидает публикации |
| `SENT` | `sent` | Отправлено |
| `FAILED` | `failed` | Ошибка публикации |

---

## Production Service Models

### Product

Модель продукта.

**Таблица:** `products`  
**Схема:** `apps/production/prisma/schema.prisma`

#### Поля

| Поле | Тип | Описание | Constraints |
|------|-----|----------|-------------|
| `id` | UUID @id | Уникальный идентификатор | `@default(uuid())` |
| `code` | String @unique | Код продукта | `@db.VarChar(20)` |
| `name` | String | Название продукта | `@db.VarChar(200)` |
| `category` | ProductCategory | Категория продукта | |
| `brand` | String? | Бренд | `@db.VarChar(50)` |
| `unitOfMeasure` | String | Единица измерения | `@map("unit_of_measure") @db.VarChar(10)` |
| `shelfLifeDays` | Int? | Срок хранения в днях | `@map("shelf_life_days")` |
| `requiresQualityCheck` | Boolean | Требуется контроль качества | `@default(false) @map("requires_quality_check")` |
| `sourceSystemId` | String? @unique | ID в исходной системе | `@map("source_system_id") @db.VarChar(20)` |
| `createdAt` | DateTime | Дата создания | `@default(now()) @map("created_at")` |
| `updatedAt` | DateTime | Дата обновления | `@default(now()) @updatedAt @map("updated_at")` |

#### Связи

- `orders` — один ко многим с ProductionOrder
- `outputs` — один ко многим с ProductionOutput
- `sales` — один ко многим с Sale
- `inventory` — один ко многим с Inventory
- `qualityResults` — один ко многим с QualityResult

#### Индексы

- `category` — индекс
- `code` — индекс
- `sourceSystemId` — уникальный индекс

#### Prisma модель

```prisma
model Product {
  id                   String          @id @default(uuid()) @db.Uuid
  code                 String          @unique @db.VarChar(20)
  name                 String          @db.VarChar(200)
  category             ProductCategory
  brand                String?         @db.VarChar(50)
  unitOfMeasure        String          @map("unit_of_measure") @db.VarChar(10)
  shelfLifeDays        Int?            @map("shelf_life_days")
  requiresQualityCheck Boolean         @default(false) @map("requires_quality_check")
  sourceSystemId       String?         @unique @map("source_system_id") @db.VarChar(20)
  createdAt            DateTime        @default(now()) @map("created_at")
  updatedAt            DateTime        @default(now()) @updatedAt @map("updated_at")

  orders  ProductionOrder[]
  outputs ProductionOutput[]
  sales   Sale[]
  inventory Inventory[]
  qualityResults QualityResult[]

  @@index([category])
  @@index([code])
  @@index([sourceSystemId])
  @@map("products")
}
```

---

### ProductionOrder

Модель производственного заказа.

**Таблица:** `production_orders`  
**Схема:** `apps/production/prisma/schema.prisma`

#### Поля

| Поле | Тип | Описание | Constraints |
|------|-----|----------|-------------|
| `id` | UUID @id | Уникальный идентификатор | `@default(uuid())` |
| `externalOrderId` | String? @unique | Внешний номер заказа | `@map("external_order_id") @db.VarChar(50)` |
| `productId` | UUID | ID продукта | `@map("product_id") @db.Uuid` |
| `targetQuantity` | Decimal | Целевое количество | `@map("target_quantity") @db.Decimal(15, 3)` |
| `actualQuantity` | Decimal? | Фактическое количество | `@map("actual_quantity") @db.Decimal(15, 3)` |
| `unitOfMeasure` | String | Единица измерения | `@map("unit_of_measure") @db.VarChar(10)` |
| `status` | OrderStatus | Статус заказа | `@default(PLANNED)` |
| `productionLine` | String | Производственная линия | `@map("production_line") @db.VarChar(50)` |
| `plannedStart` | DateTime | Планируемое начало | `@map("planned_start")` |
| `plannedEnd` | DateTime | Планируемое окончание | `@map("planned_end")` |
| `actualStart` | DateTime? | Фактическое начало | `@map("actual_start")` |
| `actualEnd` | DateTime? | Фактическое окончание | `@map("actual_end")` |
| `createdAt` | DateTime | Дата создания | `@default(now()) @map("created_at")` |
| `updatedAt` | DateTime | Дата обновления | `@updatedAt @map("updated_at")` |

#### Связи

- `product` — многие к одному с Product
- `outputs` — один ко многим с ProductionOutput

#### Индексы

- `productId` — индекс
- `status` — индекс
- `productionLine` — индекс
- `plannedStart` — индекс

#### Prisma модель

```prisma
model ProductionOrder {
  id              String      @id @default(uuid()) @db.Uuid
  externalOrderId      String?         @unique @map("external_order_id") @db.VarChar(50)
  productId       String      @map("product_id") @db.Uuid
  targetQuantity  Decimal     @map("target_quantity") @db.Decimal(15, 3)
  actualQuantity  Decimal?    @map("actual_quantity") @db.Decimal(15, 3)
  unitOfMeasure   String      @map("unit_of_measure") @db.VarChar(10)
  status          OrderStatus @default(PLANNED)
  productionLine  String      @map("production_line") @db.VarChar(50)
  plannedStart    DateTime    @map("planned_start")
  plannedEnd      DateTime    @map("planned_end")
  actualStart     DateTime?   @map("actual_start")
  actualEnd       DateTime?   @map("actual_end")
  createdAt       DateTime    @default(now()) @map("created_at")
  updatedAt       DateTime    @updatedAt @map("updated_at")

  product Product           @relation(fields: [productId], references: [id])
  outputs ProductionOutput[]

  @@index([productId])
  @@index([status])
  @@index([productionLine])
  @@index([plannedStart])
  @@map("production_orders")
}
```

---

### ProductionOutput

Модель выпуска продукции.

**Таблица:** `production_output`  
**Схема:** `apps/production/prisma/schema.prisma`

#### Поля

| Поле | Тип | Описание | Constraints |
|------|-----|----------|-------------|
| `id` | UUID @id | Уникальный идентификатор | `@default(uuid())` |
| `orderId` | UUID | ID заказа | `@map("order_id") @db.Uuid` |
| `productId` | UUID | ID продукта | `@map("product_id") @db.Uuid` |
| `lotNumber` | String | Номер партии | `@map("lot_number") @db.VarChar(20)` |
| `quantity` | Decimal | Количество | `@db.Decimal(15, 3)` |
| `qualityStatus` | QualityStatus | Статус качества | `@default(PENDING) @map("quality_status")` |
| `productionDate` | DateTime | Дата производства | `@map("production_date")` |
| `shift` | String | Смена | `@db.VarChar(20)` |
| `createdAt` | DateTime | Дата создания | `@default(now()) @map("created_at")` |

#### Связи

- `order` — многие к одному с ProductionOrder
- `product` — многие к одному с Product

#### Индексы

- `orderId` — индекс
- `productId` — индекс
- `lotNumber` — индекс
- `productionDate` — индекс

#### Prisma модель

```prisma
model ProductionOutput {
  id             String        @id @default(uuid()) @db.Uuid
  orderId        String        @map("order_id") @db.Uuid
  productId      String        @map("product_id") @db.Uuid
  lotNumber      String        @map("lot_number") @db.VarChar(20)
  quantity       Decimal       @db.Decimal(15, 3)
  qualityStatus  QualityStatus @default(PENDING) @map("quality_status")
  productionDate DateTime      @map("production_date")
  shift          String        @db.VarChar(20)
  createdAt      DateTime      @default(now()) @map("created_at")

  order   ProductionOrder @relation(fields: [orderId], references: [id])
  product Product         @relation(fields: [productId], references: [id])

  @@index([orderId])
  @@index([productId])
  @@index([lotNumber])
  @@index([productionDate])
  @@map("production_output")
}
```

---

### Sale

Модель продажи.

**Таблица:** `sales`  
**Схема:** `apps/production/prisma/schema.prisma`

#### Поля

| Поле | Тип | Описание | Constraints |
|------|-----|----------|-------------|
| `id` | UUID @id | Уникальный идентификатор | `@default(uuid())` |
| `externalId` | String | Внешний ID продажи | `@map("external_id") @db.VarChar(20)` |
| `productId` | UUID | ID продукта | `@map("product_id") @db.Uuid` |
| `customerName` | String | Имя клиента | `@map("customer_name") @db.VarChar(200)` |
| `quantity` | Decimal | Количество | `@db.Decimal(15, 3)` |
| `amount` | Decimal | Сумма | `@db.Decimal(15, 2)` |
| `saleDate` | DateTime | Дата продажи | `@map("sale_date") @db.Date` |
| `region` | String | Регион | `@db.VarChar(100)` |
| `channel` | SaleChannel | Канал продаж | |
| `createdAt` | DateTime | Дата создания | `@default(now()) @map("created_at")` |

#### Связи

- `product` — многие к одному с Product

#### Индексы

- `productId` — индекс
- `saleDate` — индекс
- `region` — индекс
- `channel` — индекс

#### Prisma модель

```prisma
model Sale {
  id           String      @id @default(uuid()) @db.Uuid
  externalId   String      @map("external_id") @db.VarChar(20)
  productId    String      @map("product_id") @db.Uuid
  customerName String      @map("customer_name") @db.VarChar(200)
  quantity     Decimal     @db.Decimal(15, 3)
  amount       Decimal     @db.Decimal(15, 2)
  saleDate     DateTime    @map("sale_date") @db.Date
  region       String      @db.VarChar(100)
  channel      SaleChannel
  createdAt    DateTime    @default(now()) @map("created_at")

  product Product @relation(fields: [productId], references: [id])

  @@index([productId])
  @@index([saleDate])
  @@index([region])
  @@index([channel])
  @@map("sales")
}
```

---

### Inventory

Модель складских остатков.

**Таблица:** `inventory`  
**Схема:** `apps/production/prisma/schema.prisma`

#### Поля

| Поле | Тип | Описание | Constraints |
|------|-----|----------|-------------|
| `id` | UUID @id | Уникальный идентификатор | `@default(uuid())` |
| `productId` | UUID | ID продукта | `@map("product_id") @db.Uuid` |
| `warehouseCode` | String | Код склада | `@map("warehouse_code") @db.VarChar(20)` |
| `lotNumber` | String? | Номер партии | `@map("lot_number") @db.VarChar(20)` |
| `quantity` | Decimal | Количество | `@db.Decimal(15, 3)` |
| `unitOfMeasure` | String | Единица измерения | `@map("unit_of_measure") @db.VarChar(10)` |
| `lastUpdated` | DateTime | Дата последнего обновления | `@map("last_updated")` |

#### Связи

- `product` — многие к одному с Product

#### Индексы

- `productId` — индекс
- `warehouseCode` — индекс

#### Prisma модель

```prisma
model Inventory {
  id            String   @id @default(uuid()) @db.Uuid
  productId     String   @map("product_id") @db.Uuid
  warehouseCode String   @map("warehouse_code") @db.VarChar(20)
  lotNumber     String?  @map("lot_number") @db.VarChar(20)
  quantity      Decimal  @db.Decimal(15, 3)
  unitOfMeasure String   @map("unit_of_measure") @db.VarChar(10)
  lastUpdated   DateTime @map("last_updated")

  product Product @relation(fields: [productId], references: [id])

  @@index([productId])
  @@index([warehouseCode])
  @@map("inventory")
}
```

---

### QualityResult

Модель результата контроля качества.

**Таблица:** `quality_results`  
**Схема:** `apps/production/prisma/schema.prisma`

#### Поля

| Поле | Тип | Описание | Constraints |
|------|-----|----------|-------------|
| `id` | UUID @id | Уникальный идентификатор | `@default(uuid())` |
| `lotNumber` | String | Номер партии | `@map("lot_number") @db.VarChar(20)` |
| `productId` | UUID | ID продукта | `@map("product_id") @db.Uuid` |
| `parameterName` | String | Название параметра | `@map("parameter_name") @db.VarChar(100)` |
| `resultValue` | Decimal | Результат | `@map("result_value") @db.Decimal(15, 6)` |
| `lowerLimit` | Decimal | Нижний предел | `@map("lower_limit") @db.Decimal(15, 6)` |
| `upperLimit` | Decimal | Верхний предел | `@map("upper_limit") @db.Decimal(15, 6)` |
| `inSpec` | Boolean | Соответствует норме | `@map("in_spec")` |
| `decision` | QualityDecision | Решение | |
| `testDate` | DateTime | Дата теста | `@map("test_date")` |
| `createdAt` | DateTime | Дата создания | `@default(now()) @map("created_at")` |

#### Связи

- `product` — многие к одному с Product

#### Индексы

- `lotNumber` — индекс
- `productId` — индекс
- `decision` — индекс

#### Prisma модель

```prisma
model QualityResult {
  id            String          @id @default(uuid()) @db.Uuid
  lotNumber     String          @map("lot_number") @db.VarChar(20)
  productId     String          @map("product_id") @db.Uuid
  parameterName String          @map("parameter_name") @db.VarChar(100)
  resultValue   Decimal         @map("result_value") @db.Decimal(15, 6)
  lowerLimit    Decimal         @map("lower_limit") @db.Decimal(15, 6)
  upperLimit    Decimal         @map("upper_limit") @db.Decimal(15, 6)
  inSpec        Boolean         @map("in_spec")
  decision      QualityDecision
  testDate      DateTime        @map("test_date")
  createdAt     DateTime        @default(now()) @map("created_at")

  product Product @relation(fields: [productId], references: [id])

  @@index([lotNumber])
  @@index([productId])
  @@index([decision])
  @@map("quality_results")
}
```

---

### SensorReading

Модель показания датчика.

**Таблица:** `sensor_readings`  
**Схема:** `apps/production/prisma/schema.prisma`

#### Поля

| Поле | Тип | Описание | Constraints |
|------|-----|----------|-------------|
| `id` | UUID @id | Уникальный идентификатор | `@default(uuid())` |
| `deviceId` | String | ID устройства | `@map("device_id") @db.VarChar(50)` |
| `productionLine` | String | Производственная линия | `@map("production_line") @db.VarChar(50)` |
| `parameterName` | String | Название параметра | `@map("parameter_name") @db.VarChar(50)` |
| `value` | Decimal | Значение | `@db.Decimal(15, 4)` |
| `unit` | String | Единица измерения | `@db.VarChar(20)` |
| `quality` | SensorQuality | Качество сигнала | |
| `recordedAt` | DateTime | Время записи | `@map("recorded_at")` |
| `createdAt` | DateTime | Дата создания | `@default(now()) @map("created_at")` |

#### Индексы

- `deviceId` — индекс
- `productionLine` — индекс
- `parameterName` — индекс
- `recordedAt` — индекс

#### Prisma модель

```prisma
model SensorReading {
  id             String        @id @default(uuid()) @db.Uuid
  deviceId       String        @map("device_id") @db.VarChar(50)
  productionLine String        @map("production_line") @db.VarChar(50)
  parameterName  String        @map("parameter_name") @db.VarChar(50)
  value          Decimal       @db.Decimal(15, 4)
  unit           String        @db.VarChar(20)
  quality        SensorQuality
  recordedAt     DateTime      @map("recorded_at")
  createdAt      DateTime      @default(now()) @map("created_at")

  @@index([deviceId])
  @@index([productionLine])
  @@index([parameterName])
  @@index([recordedAt])
  @@map("sensor_readings")
}
```

---

### OutboxMessage (Production)

Модель outbox для надежной публикации событий (аналогично Personnel).

**Таблица:** `outbox_messages`  
**Схема:** `apps/production/prisma/schema.prisma`

Структура идентична Personnel OutboxMessage.

---

### Production Enums

#### ProductCategory

**Таблица:** `product_category`

| Значение | База данных | Описание |
|----------|-------------|----------|
| `RAW_MATERIAL` | `raw_material` | Сырье |
| `SEMI_FINISHED` | `semi_finished` | Полуфабрикат |
| `FINISHED_PRODUCT` | `finished_product` | Готовая продукция |
| `PACKAGING` | `packaging` | Упаковка |

#### OrderStatus

**Таблица:** `order_status`

| Значение | База данных | Описание |
|----------|-------------|----------|
| `PLANNED` | `planned` | Запланирован |
| `IN_PROGRESS` | `in_progress` | В работе |
| `COMPLETED` | `completed` | Завершен |
| `CANCELLED` | `cancelled` | Отменен |

#### QualityStatus

**Таблица:** `quality_status`

| Значение | База данных | Описание |
|----------|-------------|----------|
| `PENDING` | `pending` | Ожидает |
| `APPROVED` | `approved` | Одобрено |
| `REJECTED` | `rejected` | Отклонено |

#### QualityDecision

**Таблица:** `quality_decision`

| Значение | База данных | Описание |
|----------|-------------|----------|
| `APPROVED` | `approved` | Одобрено |
| `REJECTED` | `rejected` | Отклонено |
| `PENDING` | `pending` | Ожидает |

#### SaleChannel

**Таблица:** `sale_channel`

| Значение | База данных | Описание |
|----------|-------------|----------|
| `RETAIL` | `retail` | Розница |
| `WHOLESALE` | `wholesale` | Опт |
| `HORECA` | `horeca` | HoReCa |
| `EXPORT` | `export` | Экспорт |

#### SensorQuality

**Таблица:** `sensor_quality`

| Значение | База данных | Описание |
|----------|-------------|----------|
| `GOOD` | `good` | Хорошее |
| `DEGRADED` | `degraded` | Ухудшенное |
| `BAD` | `bad` | Плохое |

---

## ETL Service Models (MongoDB)

ETL сервис использует MongoDB для хранения данных интеграции.

### RawImport

Журнал операций импорта.

**Коллекция:** `raw_imports`  
**Схема:** Mongoose

#### Поля

| Поле | Тип | Описание |
|------|-----|----------|
| `_id` | ObjectId | Уникальный идентификатор |
| `sourceSystem` | String | Источник системы (ZUP, ERP, MES, SCADA, LIMS) |
| `importType` | String | Тип импорта |
| `status` | String | Статус (PROCESSING, COMPLETED, FAILED) |
| `recordsCount` | Number | Количество записей |
| `rawPayload` | Array | Исходные данные |
| `fileId` | ObjectId? | GridFS ID файла (если загружен через file upload) |
| `statistics` | Object | Статистика трансформаций |
| `errors` | Array | Ошибки обработки |
| `createdAt` | Date | Дата создания |
| `processedAt` | Date? | Дата обработки |

---

### TransformationLog

Лог трансформации записей.

**Коллекция:** `transformation_logs`  
**Схема:** Mongoose

#### Поля

| Поле | Тип | Описание |
|------|-----|----------|
| `_id` | ObjectId | Уникальный идентификатор |
| `importId` | ObjectId | ID импорта |
| `entityType` | String | Тип сущности (employee, product, etc.) |
| `sourceRecord` | Object | Исходная запись |
| `canonicalRecord` | Object | Каноническая запись |
| `status` | String | Статус (SUCCESS, ERROR, SKIPPED) |
| `errorMessage` | String? | Сообщение об ошибке |
| `createdAt` | Date | Дата создания |

---

### GridFS (Files)

Хранение исходных файлов импорта.

**Buckets:** `fs.files`, `fs.chunks`  
**Используется:** Mongoose GridFS

Для хранения файлов .xlsx и .json, загруженных через `POST /etl/import/file`.

---

## Работа с Prisma

### Генерация клиента

```bash
cd apps/<service>
npx prisma generate
```

Клиент генерируется в `apps/<service>/src/generated/prisma`.

### Применение миграций

```bash
cd apps/<service>
npx prisma migrate dev --name <migration-name>
```

### Prisma Studio

```bash
cd apps/<service>
npx prisma studio
```

Откроется веб-интерфейс для работы с БД.

### Использование в коде

```typescript
import { PrismaClient } from '../generated/prisma';

const prisma = new PrismaClient();

// Создание
const user = await prisma.user.create({
  data: {
    email: 'ivan@example.com',
    passwordHash: '...',
    fullName: 'Иванов Иван',
  },
});

// Чтение
const users = await prisma.user.findMany({
  where: { isActive: true },
});

// Обновление
const updated = await prisma.user.update({
  where: { id: userId },
  data: { fullName: 'Иванов Иван Петрович' },
});

// Удаление
await prisma.user.delete({
  where: { id: userId },
});
```

---

## Мониторинг БД

### PostgreSQL

Для мониторинга PostgreSQL используйте:

- `pg_stat_activity` — активные соединения
- `pg_stat_user_tables` — статистика по таблицам
- `pg_stat_user_indexes` — статистика по индексам

Пример запроса для проверки outbox:

```sql
SELECT 
  event_type,
  status,
  COUNT(*) as count
FROM outbox_messages
GROUP BY event_type, status;
```

### MongoDB

Для мониторинга MongoDB используйте:

- `db.stats()` — статистика базы данных
- `db.collection.stats()` — статистика коллекции
- `db.currentOp()` — активные операции

Пример запроса для проверки импортов:

```javascript
db.raw_imports.aggregate([
  {
    $group: {
      _id: { sourceSystem: "$sourceSystem", status: "$status" },
      count: { $sum: 1 }
    }
  }
]);
```
