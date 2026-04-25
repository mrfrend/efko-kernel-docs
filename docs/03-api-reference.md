# API Reference

Полный справочник по REST API EFKO Kernel с примерами запросов и ответов.

## Общие принципы

### Base URL

```
http://localhost:3000/api
```

Все эндпоинты доступны относительно этого базового URL.

### Формат данных

- **Request Format:** JSON (`Content-Type: application/json`)
- **Response Format:** JSON
- **Date Format:** ISO 8601 (`YYYY-MM-DD` или `YYYY-MM-DDTHH:mm:ss.sssZ`)
- **UUID Format:** Стандартный UUID v4

### Аутентификация

Система использует JWT токены:

- **Access Token:** Короткоживущий токен для аутентификации запросов
- **Refresh Token:** Долгоживущий токен для обновления сессии

Access токен передается в заголовке:

```
Authorization: Bearer <accessToken>
```

### CSRF Защита

**Для браузерных клиентов:**
- После логина устанавливается cookie `XSRF-TOKEN`
- Браузер должен читать эту cookie и передавать её значение в заголовке `X-CSRF-Token` при каждом мутирующем запросе (POST, PATCH, DELETE)
- GET, HEAD, OPTIONS запросы CSRF не проверяются

**Для мобильных клиентов:**
- CSRF проверка автоматически пропускается (нет cookie механизма)
- Refresh токен передается в теле запроса при обновлении сессии

### Rate Limiting

Три профиля лимитов применяются глобально:

| Профиль | Лимит |
|---------|-------|
| short | 20 req / 1 s |
| medium | 100 req / 10 s |
| long | 500 req / 60 s |

Auth endpoints (`/auth/register`, `/auth/login`) имеют более строгие отдельные лимиты.

### Корреляция запросов

Каждый запрос имеет `requestId` для трассировки:
- Автоматически генерируется через `RequestIdMiddleware`
- Может быть передан вручную через заголовок `x-request-id`
- Пропагируется через все сервисы

### Обработка ошибок

#### Стандартная структура ошибки

```json
{
  "statusCode": 401,
  "message": "Unauthorized",
  "error": "Unauthorized"
}
```

#### HTTP коды ошибок

| Код | Описание |
|-----|----------|
| `400` | Ошибка валидации |
| `401` | Не авторизован / невалидный токен |
| `403` | Недостаточно прав |
| `404` | Ресурс не найден |
| `409` | Конфликт (дубликат, недопустимый переход) |
| `429` | Rate limit превышен |
| `503` | Downstream сервис недоступен |
| `504` | Downstream сервис не ответил вовремя (timeout) |

---

## Auth API

Эндпоинты аутентификации и управления пользователями.

### POST /auth/register

Регистрация нового пользователя.

**Аутентификация:** Не требуется  
**CSRF:** Требуется для браузера  
**Rate Limit:** Отдельный строгий лимит

#### Request Body

```typescript
{
  email: string;        // Email пользователя
  password: string;     // Пароль (минимум 8 символов)
  firstName: string;    // Имя
  lastName: string;     // Фамилия
  role?: UserRole;      // Роль (опционально, по умолчанию EMPLOYEE)
}
```

#### Response

```typescript
{
  id: string;           // UUID пользователя
  email: string;        // Email
  fullName: string;     // Полное имя
  role: UserRole;       // Роль
  isActive: boolean;    // Статус активности
  employeeId: string | null; // ID сотрудника (если привязан)
}
```

#### Пример запроса

```bash
curl -X POST http://localhost:3000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "ivan@example.com",
    "password": "SecurePass123!",
    "firstName": "Иван",
    "lastName": "Иванов",
    "role": "ADMIN"
  }'
```

#### Пример ответа

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

#### Ошибки

- `400` — Некорректный формат email или имени
- `409` — Email уже занят (`USER_ALREADY_EXISTS`)

---

### POST /auth/login

Вход в систему.

**Аутентификация:** Не требуется  
**CSRF:** Требуется для браузера  
**Rate Limit:** Отдельный строгий лимит

#### Request Body

```typescript
{
  email: string;
  password: string;
}
```

#### Response

```typescript
{
  accessToken: string;   // JWT access токен
  refreshToken: string;  // Refresh токен
}
```

#### Cookies

Устанавливаются в ответе:
- `refreshToken` — httpOnly cookie для обновления сессии
- `XSRF-TOKEN` — читаемый JS cookie с CSRF токеном

#### Пример запроса

```bash
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "ivan@example.com",
    "password": "SecurePass123!"
  }' \
  -c cookies.txt
```

#### Пример ответа

```json
{
  "accessToken": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refreshToken": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Ошибки

- `400` — Некорректный формат
- `401` — Невалидные учетные данные или аккаунт деактивирован (`INVALID_CREDENTIALS`)

---

### GET /auth/me

Получить профиль текущего пользователя.

**Аутентификация:** Bearer accessToken  
**CSRF:** Не требуется

#### Response

```typescript
{
  id: string;
  email: string;
  fullName: string;
  role: UserRole;
  isActive: boolean;
  employeeId: string | null;
}
```

#### Пример запроса

```bash
curl -X GET http://localhost:3000/api/auth/me \
  -H "Authorization: Bearer <accessToken>"
```

#### Пример ответа

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "email": "ivan@example.com",
  "fullName": "Иванов Иван",
  "role": "ADMIN",
  "isActive": true,
  "employeeId": "d4e5f6a7-b8c9-0123-defa-234567890123"
}
```

#### Ошибки

- `401` — Токен недействителен или истек
- `404` — Пользователь не найден или деактивирован (`USER_NOT_FOUND`)

---

### POST /auth/refresh-session

Обновить сессию по refresh токену.

**Аутентификация:** Refresh токен (через cookie или тело)  
**CSRF:** Требуется для браузера

#### Request Body (мобильные клиенты)

```typescript
{
  refreshToken: string;
}
```

#### Response

```typescript
{
  accessToken: string;
  refreshToken: string;
}
```

#### Cookies

Обновляются в ответе:
- `refreshToken` — новый refresh токен (rotation)
- `XSRF-TOKEN` — новый CSRF токен

#### Пример запроса (браузер)

```bash
curl -X POST http://localhost:3000/api/auth/refresh-session \
  -H "X-CSRF-Token: <value from XSRF-TOKEN cookie>" \
  -b cookies.txt \
  -c cookies.txt
```

#### Пример запроса (мобильный)

```bash
curl -X POST http://localhost:3000/api/auth/refresh-session \
  -H "Content-Type: application/json" \
  -d '{
    "refreshToken": "<stored refresh token>"
  }'
```

#### Пример ответа

```json
{
  "accessToken": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refreshToken": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Ошибки

- `401` — Refresh токен отсутствует, отозван (`REFRESH_TOKEN_REVOKED`), истек (`REFRESH_TOKEN_EXPIRED`)

---

### POST /auth/logout

Завершение сессии.

**Аутентификация:** Bearer accessToken  
**CSRF:** Требуется для браузера

#### Response

```typescript
{
  success: boolean;
}
```

#### Cookies

Очищаются:
- `refreshToken`
- `XSRF-TOKEN`

#### Пример запроса

```bash
curl -X POST http://localhost:3000/api/auth/logout \
  -H "Authorization: Bearer <accessToken>" \
  -H "X-CSRF-Token: <value from XSRF-TOKEN cookie>" \
  -b cookies.txt \
  -c cookies.txt
```

#### Пример ответа

```json
{
  "success": true
}
```

---

### GET /users

Список всех пользователей.

**Аутентификация:** Bearer accessToken  
**Роль:** ADMIN (требуется)  
**CSRF:** Не требуется

#### Response

```typescript
{
  users: Array<{
    id: string;
    email: string;
    fullName: string;
    role: UserRole;
    isActive: boolean;
    employeeId: string | null;
  }>;
}
```

#### Пример запроса

```bash
curl -X GET http://localhost:3000/api/users \
  -H "Authorization: Bearer <accessToken>"
```

#### Ошибки

- `403` — Недостаточно прав

---

### PATCH /users/:userId

Обновить данные пользователя.

**Аутентификация:** Bearer accessToken  
**Роль:** ADMIN (требуется)  
**CSRF:** Требуется для браузера

#### Request Body

```typescript
{
  email?: string;
  fullName?: string;
  role?: UserRole;
  employeeId?: string | null;
}
```

#### Response

```typescript
{
  id: string;
  email: string;
  fullName: string;
  role: UserRole;
  isActive: boolean;
  employeeId: string | null;
}
```

#### Пример запроса

```bash
curl -X PATCH http://localhost:3000/api/users/a1b2c3d4-e5f6-7890-abcd-ef1234567890 \
  -H "Authorization: Bearer <accessToken>" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <value>" \
  -d '{
    "fullName": "Иванов Иван Петрович"
  }'
```

#### Ошибки

- `403` — Недостаточно прав
- `404` — Пользователь не найден

---

### POST /users/deactivate

Деактивировать пользователя.

**Аутентификация:** Bearer accessToken  
**Роль:** ADMIN (требуется)  
**CSRF:** Требуется для браузера

#### Request Body

```typescript
{
  userId: string;
}
```

#### Response

```typescript
{
  id: string;
  isActive: boolean;
}
```

#### Пример запроса

```bash
curl -X POST http://localhost:3000/api/users/deactivate \
  -H "Authorization: Bearer <accessToken>" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <value>" \
  -d '{
    "userId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }'
```

---

## Personnel API

Управление кадровыми данными: подразделения, должности, сотрудники, шаблоны смен.

### POST /personnel/departments

Создать подразделение.

**Аутентификация:** Bearer accessToken  
**Роли:** ADMIN, MANAGER  
**CSRF:** Требуется для браузера

#### Request Body

```typescript
{
  name: string;
  code: string;
  type: DepartmentType;
  parentId?: string | null;
  headEmployeeId?: string | null;
}
```

#### Response

```typescript
{
  id: string;
  name: string;
  code: string;
  type: DepartmentType;
  parentId: string | null;
  headEmployeeId: string | null;
  sourceSystemId: string | null;
}
```

#### Пример запроса

```bash
curl -X POST http://localhost:3000/api/personnel/departments \
  -H "Authorization: Bearer <accessToken>" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <value>" \
  -d '{
    "name": "Производственный цех №1",
    "code": "PROD-001",
    "type": "DIVISION"
  }'
```

#### Ошибки

- `400` — Ошибка валидации
- `409` — Код уже занят (`DEPARTMENT_CODE_ALREADY_EXISTS`)

---

### GET /personnel/departments

Список подразделений.

**Аутентификация:** Bearer accessToken  
**Роли:** ADMIN, MANAGER, SHIFT_MANAGER, ANALYST  
**CSRF:** Не требуется

#### Query Parameters

- `type?` — Тип подразделения
- `code?` — Код подразделения

#### Response

```typescript
{
  departments: Array<{
    id: string;
    name: string;
    code: string;
    type: DepartmentType;
    parentId: string | null;
    headEmployeeId: string | null;
    sourceSystemId: string | null;
  }>;
}
```

#### Пример запроса

```bash
curl -X GET "http://localhost:3000/api/personnel/departments?type=DIVISION" \
  -H "Authorization: Bearer <accessToken>"
```

---

### PATCH /personnel/departments/:id

Обновить подразделение.

**Аутентификация:** Bearer accessToken  
**Роли:** ADMIN, MANAGER  
**CSRF:** Требуется для браузера

#### Request Body

```typescript
{
  name?: string;
  code?: string;
  type?: DepartmentType;
  headEmployeeId?: string | null;
}
```

#### Response

```typescript
{
  id: string;
  name: string;
  code: string;
  type: DepartmentType;
  headEmployeeId: string | null;
  sourceSystemId: string | null;
}
```

#### Пример запроса

```bash
curl -X PATCH http://localhost:3000/api/personnel/departments/<id> \
  -H "Authorization: Bearer <accessToken>" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <value>" \
  -d '{
    "headEmployeeId": "d4e5f6a7-b8c9-0123-defa-234567890123"
  }'
```

---

### POST /personnel/positions

Создать должность.

**Аутентификация:** Bearer accessToken  
**Роли:** ADMIN, MANAGER  
**CSRF:** Требуется для браузера

#### Request Body

```typescript
{
  title: string;
  code: string;
  departmentId: string;
}
```

#### Response

```typescript
{
  id: string;
  title: string;
  code: string;
  departmentId: string;
}
```

#### Пример запроса

```bash
curl -X POST http://localhost:3000/api/personnel/positions \
  -H "Authorization: Bearer <accessToken>" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <value>" \
  -d '{
    "title": "Оператор станка",
    "code": "OP-001",
    "departmentId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }'
```

#### Ошибки

- `404` — Подразделение не найдено (`DEPARTMENT_NOT_FOUND`)
- `409` — Код должности уже занят (`POSITION_CODE_ALREADY_EXISTS`)

---

### GET /personnel/positions

Список должностей.

**Аутентификация:** Bearer accessToken  
**Роли:** ADMIN, MANAGER, SHIFT_MANAGER, ANALYST  
**CSRF:** Не требуется

#### Query Parameters

- `departmentId?` — UUID подразделения

#### Response

```typescript
{
  positions: Array<{
    id: string;
    title: string;
    code: string;
    departmentId: string;
  }>;
}
```

---

### PATCH /personnel/positions/:id

Обновить должность.

**Аутентификация:** Bearer accessToken  
**Роли:** ADMIN, MANAGER  
**CSRF:** Требуется для браузера

#### Request Body

```typescript
{
  title?: string;
  code?: string;
  departmentId?: string;
}
```

#### Response

```typescript
{
  id: string;
  title: string;
  code: string;
  departmentId: string;
}
```

---

### POST /personnel/employees

Создать сотрудника.

**Аутентификация:** Bearer accessToken  
**Роли:** ADMIN, MANAGER  
**CSRF:** Требуется для браузера

#### Request Body

```typescript
{
  fullName: string;
  dateOfBirth: string; // ISO date
  departmentId: string;
  positionId: string;
  hireDate: string; // ISO date
  employmentType: EmploymentType;
}
```

#### Response

```typescript
{
  id: string;
  personnelNumber: string;
  fullName: string;
  status: EmployeeStatus;
  employmentType: EmploymentType;
  departmentId: string;
  positionId: string;
  hireDate: string;
  dateOfBirth: string;
  terminationDate: string | null;
}
```

#### Пример запроса

```bash
curl -X POST http://localhost:3000/api/personnel/employees \
  -H "Authorization: Bearer <accessToken>" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <value>" \
  -d '{
    "fullName": "Иванов Иван Иванович",
    "dateOfBirth": "1985-05-15",
    "departmentId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "positionId": "c3d4e5f6-a7b8-9012-cdef-123456789012",
    "hireDate": "2025-01-01",
    "employmentType": "FULL_TIME"
  }'
```

#### Ошибки

- `400` — Некорректное имя (`INVALID_FULL_NAME`)
- `404` — Подразделение или должность не найдены

---

### GET /personnel/employees

Список сотрудников.

**Аутентификация:** Bearer accessToken  
**Роли:** ADMIN, MANAGER, SHIFT_MANAGER, ANALYST  
**CSRF:** Не требуется

#### Query Parameters

- `departmentId?` — UUID подразделения
- `positionId?` — UUID должности
- `status?` — Статус (ACTIVE, TERMINATED, ON_LEAVE)
- `employmentType?` — Тип занятости

#### Response

```typescript
{
  employees: Array<{
    id: string;
    personnelNumber: string;
    fullName: string;
    status: EmployeeStatus;
    employmentType: EmploymentType;
    departmentId: string;
    positionId: string;
    hireDate: string;
    dateOfBirth: string;
    terminationDate: string | null;
  }>;
}
```

---

### PATCH /personnel/employees/:id

Обновить данные сотрудника.

**Аутентификация:** Bearer accessToken  
**Роли:** ADMIN, MANAGER  
**CSRF:** Требуется для браузера

#### Request Body

```typescript
{
  fullName?: string;
  departmentId?: string;
  positionId?: string;
  employmentType?: EmploymentType;
}
```

#### Response

```typescript
{
  id: string;
  personnelNumber: string;
  fullName: string;
  status: EmployeeStatus;
  employmentType: EmploymentType;
  departmentId: string;
  positionId: string;
  hireDate: string;
}
```

---

### POST /personnel/employees/:id/terminate

Уволить сотрудника.

**Аутентификация:** Bearer accessToken  
**Роли:** ADMIN, MANAGER  
**CSRF:** Требуется для браузера

#### Request Body

```typescript
{
  terminationDate?: string; // ISO date, опционально
}
```

#### Response

```typescript
{
  id: string;
  status: EmployeeStatus;
  terminationDate: string;
}
```

#### Пример запроса

```bash
curl -X POST http://localhost:3000/api/personnel/employees/<id>/terminate \
  -H "Authorization: Bearer <accessToken>" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <value>" \
  -d '{
    "terminationDate": "2025-06-30"
  }'
```

#### Ошибки

- `409` — Сотрудник уже уволен (`EMPLOYEE_ALREADY_TERMINATED`)

---

### POST /personnel/shift-templates

Создать шаблон смены.

**Аутентификация:** Bearer accessToken  
**Роли:** ADMIN, MANAGER, SHIFT_MANAGER  
**CSRF:** Требуется для браузера

#### Request Body

```typescript
{
  name: string;
  shiftType: ShiftType;
  startTime: string; // HH:MM
  endTime: string; // HH:MM
  workDaysPattern: string; // Бинарная строка, например "1111100"
}
```

#### Response

```typescript
{
  id: string;
  name: string;
  shiftType: ShiftType;
  startTime: string;
  endTime: string;
  workDaysPattern: string;
}
```

#### Пример запроса

```bash
curl -X POST http://localhost:3000/api/personnel/shift-templates \
  -H "Authorization: Bearer <accessToken>" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <value>" \
  -d '{
    "name": "Дневная смена",
    "shiftType": "DAY",
    "startTime": "08:00",
    "endTime": "20:00",
    "workDaysPattern": "1111100"
  }'
```

---

### GET /personnel/shift-templates

Список шаблонов смен.

**Аутентификация:** Bearer accessToken  
**Роли:** ADMIN, MANAGER, SHIFT_MANAGER, ANALYST  
**CSRF:** Не требуется

#### Response

```typescript
{
  templates: Array<{
    id: string;
    name: string;
    shiftType: ShiftType;
    startTime: string;
    endTime: string;
    workDaysPattern: string;
  }>;
}
```

---

### PATCH /personnel/shift-templates/:id

Обновить шаблон смены.

**Аутентификация:** Bearer accessToken  
**Роли:** ADMIN, MANAGER, SHIFT_MANAGER  
**CSRF:** Требуется для браузера

#### Request Body

```typescript
{
  name?: string;
  shiftType?: ShiftType;
  startTime?: string;
  endTime?: string;
  workDaysPattern?: string;
}
```

#### Response

```typescript
{
  id: string;
  name: string;
  shiftType: ShiftType;
  startTime: string;
  endTime: string;
  workDaysPattern: string;
}
```

---

## Production API

Управление производственными данными: продукты, заказы, выпуск, качество, датчики, KPI.

### POST /production/products

Создать продукт.

**Аутентификация:** Bearer accessToken  
**CSRF:** Требуется для браузера

#### Request Body

```typescript
{
  code: string;
  name: string;
  category: ProductCategory;
  brand?: string;
  unitOfMeasure: string;
  shelfLifeDays?: number;
  requiresQualityCheck?: boolean;
}
```

#### Response

```typescript
{
  id: string;
  code: string;
  name: string;
  category: ProductCategory;
}
```

#### Пример запроса

```bash
curl -X POST http://localhost:3000/api/production/products \
  -H "Authorization: Bearer <accessToken>" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <value>" \
  -d '{
    "code": "PROD-001",
    "name": "Творог 5%",
    "category": "FINISHED_PRODUCT",
    "brand": "Домик в деревне",
    "unitOfMeasure": "kg",
    "shelfLifeDays": 30,
    "requiresQualityCheck": true
  }'
```

#### Ошибки

- `409` — Код продукта уже занят (`PRODUCT_CODE_ALREADY_EXISTS`)

---

### GET /production/products

Список продуктов.

**Аутентификация:** Bearer accessToken  
**CSRF:** Не требуется

#### Query Parameters

- `category?` — Категория продукта
- `brand?` — Бренд

#### Response

```typescript
{
  products: Array<{
    id: string;
    code: string;
    name: string;
    category: ProductCategory;
    brand: string | null;
    unitOfMeasure: string;
    shelfLifeDays: number | null;
    requiresQualityCheck: boolean;
  }>;
}
```

---

### POST /production/orders

Создать производственный заказ.

**Аутентификация:** Bearer accessToken  
**CSRF:** Требуется для браузера

#### Request Body

```typescript
{
  externalOrderId?: string;
  productId: string;
  targetQuantity: number;
  unitOfMeasure: string;
  productionLine: string;
  plannedStart: string; // ISO datetime
  plannedEnd: string; // ISO datetime
}
```

#### Response

```typescript
{
  id: string;
  externalOrderId: string | null;
  productId: string;
  status: OrderStatus;
}
```

#### Пример запроса

```bash
curl -X POST http://localhost:3000/api/production/orders \
  -H "Authorization: Bearer <accessToken>" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <value>" \
  -d '{
    "externalOrderId": "EXT-ORDER-001",
    "productId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "targetQuantity": 1000,
    "unitOfMeasure": "kg",
    "productionLine": "Line-1",
    "plannedStart": "2025-01-01T06:00:00Z",
    "plannedEnd": "2025-01-10T18:00:00Z"
  }'
```

#### Ошибки

- `404` — Продукт не найден (`PRODUCT_NOT_FOUND`)

---

### GET /production/orders

Список заказов.

**Аутентификация:** Bearer accessToken  
**CSRF:** Не требуется

#### Query Parameters

- `status?` — Статус заказа
- `productId?` — UUID продукта
- `productionLine?` — Производственная линия
- `from?` — Начало периода (ISO date)
- `to?` — Конец периода (ISO date)

#### Response

```typescript
{
  orders: Array<{
    id: string;
    externalOrderId: string | null;
    productId: string;
    targetQuantity: number;
    actualQuantity: number | null;
    unitOfMeasure: string;
    status: OrderStatus;
    productionLine: string;
    plannedStart: string;
    plannedEnd: string;
    actualStart: string | null;
    actualEnd: string | null;
  }>;
}
```

---

### GET /production/orders/:id

Заказ по ID с выпусками.

**Аутентификация:** Bearer accessToken  
**CSRF:** Не требуется

#### Response

```typescript
{
  id: string;
  externalOrderId: string | null;
  productId: string;
  targetQuantity: number;
  actualQuantity: number | null;
  unitOfMeasure: string;
  status: OrderStatus;
  productionLine: string;
  plannedStart: string;
  plannedEnd: string;
  actualStart: string | null;
  actualEnd: string | null;
  outputs: Array<{
    id: string;
    orderId: string;
    productId: string;
    lotNumber: string;
    quantity: number;
    qualityStatus: QualityStatus;
    productionDate: string;
    shift: string;
  }>;
}
```

---

### PATCH /production/orders/:id/status

Обновить статус заказа.

**Аутентификация:** Bearer accessToken  
**CSRF:** Требуется для браузера

#### Request Body

```typescript
{
  action: 'start' | 'complete' | 'cancel';
  actualQuantity?: number;
}
```

#### Response

```typescript
{
  id: string;
  status: OrderStatus;
  actualQuantity: number | null;
  actualStart: string | null;
  actualEnd: string | null;
}
```

#### Пример запроса

```bash
curl -X PATCH http://localhost:3000/api/production/orders/<id>/status \
  -H "Authorization: Bearer <accessToken>" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <value>" \
  -d '{
    "action": "start"
  }'
```

#### Ошибки

- `409` — Недопустимый переход статуса (`INVALID_ORDER_STATUS_TRANSITION`)

---

### POST /production/output

Зарегистрировать выпуск продукции.

**Аутентификация:** Bearer accessToken  
**CSRF:** Требуется для браузера

#### Request Body

```typescript
{
  orderId: string;
  productId: string;
  lotNumber: string;
  quantity: number;
  shift: string;
}
```

#### Response

```typescript
{
  id: string;
  orderId: string;
  lotNumber: string;
  quantity: number;
}
```

#### Пример запроса

```bash
curl -X POST http://localhost:3000/api/production/output \
  -H "Authorization: Bearer <accessToken>" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <value>" \
  -d '{
    "orderId": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "productId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "lotNumber": "LOT-2025-001",
    "quantity": 500,
    "shift": "morning"
  }'
```

---

### GET /production/output

Список выпусков.

**Аутентификация:** Bearer accessToken  
**CSRF:** Не требуется

#### Query Parameters

- `orderId?` — UUID заказа
- `productId?` — UUID продукта
- `lotNumber?` — Номер партии
- `from?` — Дата производства от
- `to?` — Дата производства до

#### Response

```typescript
{
  outputs: Array<{
    id: string;
    orderId: string;
    productId: string;
    lotNumber: string;
    quantity: number;
    qualityStatus: QualityStatus;
    productionDate: string;
    shift: string;
  }>;
}
```

---

### POST /production/sales

Зарегистрировать продажу.

**Аутентификация:** Bearer accessToken  
**CSRF:** Требуется для браузера

#### Request Body

```typescript
{
  externalId: string;
  productId: string;
  customerName: string;
  quantity: number;
  amount: number;
  saleDate: string; // ISO date
  region: string;
  channel: SaleChannel;
}
```

#### Response

```typescript
{
  id: string;
  externalId: string;
  productId: string;
  amount: number;
}
```

#### Пример запроса

```bash
curl -X POST http://localhost:3000/api/production/sales \
  -H "Authorization: Bearer <accessToken>" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <value>" \
  -d '{
    "externalId": "SALE-001",
    "productId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "customerName": "ООО Ромашка",
    "quantity": 100,
    "amount": 50000,
    "saleDate": "2025-02-01",
    "region": "Краснодарский край",
    "channel": "RETAIL"
  }'
```

---

### GET /production/sales

Список продаж.

**Аутентификация:** Bearer accessToken  
**CSRF:** Не требуется

#### Query Parameters

- `productId?` — UUID продукта
- `region?` — Регион
- `channel?` — Канал продаж
- `from?` — Дата продажи от
- `to?` — Дата продажи до

#### Response

```typescript
{
  sales: Array<{
    id: string;
    externalId: string;
    productId: string;
    customerName: string;
    quantity: number;
    amount: number;
    saleDate: string;
    region: string;
    channel: SaleChannel;
  }>;
}
```

---

### GET /production/sales/summary

Сводка продаж.

**Аутентификация:** Bearer accessToken  
**CSRF:** Не требуется

#### Query Parameters

- `from?` — Начало периода
- `to?` — Конец периода
- `groupBy?` — Ось группировки (region | channel | product)

#### Response

```typescript
{
  summary: Array<{
    groupKey: string;
    totalQuantity: number;
    totalAmount: number;
    salesCount: number;
  }>;
  totalAmount: number;
  totalQuantity: number;
}
```

---

### POST /production/inventory

Обновить/создать остаток на складе.

**Аутентификация:** Bearer accessToken  
**CSRF:** Требуется для браузера

#### Request Body

```typescript
{
  productId: string;
  warehouseCode: string;
  lotNumber?: string;
  quantity: number;
  unitOfMeasure: string;
}
```

#### Response

```typescript
{
  id: string;
  productId: string;
  warehouseCode: string;
  quantity: number;
}
```

#### Пример запроса

```bash
curl -X POST http://localhost:3000/api/production/inventory \
  -H "Authorization: Bearer <accessToken>" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <value>" \
  -d '{
    "productId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "warehouseCode": "WH-01",
    "lotNumber": "LOT-2025-001",
    "quantity": 200,
    "unitOfMeasure": "kg"
  }'
```

---

### GET /production/inventory

Остатки на складах.

**Аутентификация:** Bearer accessToken  
**CSRF:** Не требуется

#### Query Parameters

- `productId?` — UUID продукта
- `warehouseCode?` — Код склада

#### Response

```typescript
{
  inventory: Array<{
    id: string;
    productId: string;
    warehouseCode: string;
    lotNumber: string | null;
    quantity: number;
    unitOfMeasure: string;
    lastUpdated: string;
  }>;
}
```

---

### POST /production/quality

Зарегистрировать результат контроля качества.

**Аутентификация:** Bearer accessToken  
**CSRF:** Требуется для браузера

#### Request Body

```typescript
{
  lotNumber: string;
  productId: string;
  parameterName: string;
  resultValue: number;
  lowerLimit: number;
  upperLimit: number;
  testDate: string; // ISO date
}
```

#### Response

```typescript
{
  id: string;
  lotNumber: string;
  productId: string;
  inSpec: boolean;
  decision: QualityDecision;
}
```

#### Пример запроса

```bash
curl -X POST http://localhost:3000/api/production/quality \
  -H "Authorization: Bearer <accessToken>" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <value>" \
  -d '{
    "lotNumber": "LOT-2025-001",
    "productId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "parameterName": "moisture",
    "resultValue": 12.5,
    "lowerLimit": 10.0,
    "upperLimit": 14.0,
    "testDate": "2025-01-06"
  }'
```

---

### GET /production/quality

Результаты контроля качества.

**Аутентификация:** Bearer accessToken  
**CSRF:** Не требуется

#### Query Parameters

- `productId?` — UUID продукта
- `lotNumber?` — Номер партии
- `decision?` — Решение
- `inSpec?` — Только в норме

#### Response

```typescript
{
  results: Array<{
    id: string;
    lotNumber: string;
    productId: string;
    parameterName: string;
    resultValue: number;
    lowerLimit: number;
    upperLimit: number;
    inSpec: boolean;
    decision: QualityDecision;
    testDate: string;
  }>;
}
```

---

### POST /production/sensors

Записать показание датчика.

**Аутентификация:** Bearer accessToken  
**CSRF:** Требуется для браузера

#### Request Body

```typescript
{
  deviceId: string;
  productionLine: string;
  parameterName: string;
  value: number;
  unit: string;
  quality: SensorQuality;
}
```

#### Response

```typescript
{
  id: string;
  deviceId: string;
  productionLine: string;
  parameterName: string;
  quality: SensorQuality;
}
```

#### Пример запроса

```bash
curl -X POST http://localhost:3000/api/production/sensors \
  -H "Authorization: Bearer <accessToken>" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <value>" \
  -d '{
    "deviceId": "SENSOR-01",
    "productionLine": "Line-1",
    "parameterName": "temperature",
    "value": 72.5,
    "unit": "°C",
    "quality": "GOOD"
  }'
```

---

### GET /production/sensors

Показания датчиков.

**Аутентификация:** Bearer accessToken  
**CSRF:** Не требуется

#### Query Parameters

- `productionLine?` — Производственная линия
- `parameterName?` — Название параметра
- `quality?` — Качество сигнала
- `from?` — Начало диапазона (ISO datetime)
- `to?` — Конец диапазона (ISO datetime)

#### Response

```typescript
{
  readings: Array<{
    id: string;
    deviceId: string;
    productionLine: string;
    parameterName: string;
    value: number;
    unit: string;
    quality: SensorQuality;
    recordedAt: string;
  }>;
}
```

---

### GET /production/kpi

KPI производства.

**Аутентификация:** Bearer accessToken  
**CSRF:** Не требуется

#### Query Parameters

- `from?` — Начало периода
- `to?` — Конец периода
- `productionLine?` — Производственная линия

#### Response

```typescript
{
  totalOutput: number;
  defectRate: number;
  completedOrders: number;
  totalOrders: number;
  oeeEstimate: number;
}
```

#### Пример запроса

```bash
curl -X GET "http://localhost:3000/api/production/kpi?from=2025-01-01&to=2025-12-31" \
  -H "Authorization: Bearer <accessToken>"
```

---

## ETL API

Интеграция с внешними системами (1C-ZUP, 1C-ERP, MES, SCADA, LIMS).

### POST /etl/import

Загрузить пакет данных (JSON body).

**Аутентификация:** Bearer accessToken  
**Роль:** ADMIN (требуется)  
**CSRF:** Требуется для браузера

#### Request Body

```typescript
{
  source_system: 'ZUP' | 'ERP' | 'MES' | 'SCADA' | 'LIMS';
  import_type: string;
  data: Array<Record<string, any>>;
}
```

#### Response

```typescript
{
  id: string; // MongoDB ObjectId
  source_system: string;
  import_type: string;
  status: 'PROCESSING' | 'COMPLETED' | 'FAILED';
  records_count: number;
}
```

#### Пример запроса

```bash
curl -X POST http://localhost:3000/api/etl/import \
  -H "Authorization: Bearer <accessToken>" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <value>" \
  -d '{
    "source_system": "ZUP",
    "import_type": "employees",
    "data": [
      {
        "ТабельныйНомер": "EMP-0001",
        "ФИО": "Иванов Иван Иванович",
        "ДатаРождения": "1985-05-15"
      }
    ]
  }'
```

---

### POST /etl/import/file

Загрузить файл (xlsx/json).

**Аутентификация:** Bearer accessToken  
**Роль:** ADMIN (требуется)  
**CSRF:** Требуется для браузера  
**Max file size:** 20 MB

#### Request Body (multipart/form-data)

```
file: <file>
source_system: string
import_type: string
```

#### Response

```typescript
{
  id: string;
  source_system: string;
  import_type: string;
  status: 'PROCESSING';
  records_count: number;
}
```

#### Пример запроса

```bash
curl -X POST http://localhost:3000/api/etl/import/file \
  -H "Authorization: Bearer <accessToken>" \
  -H "X-CSRF-Token: <value>" \
  -F "file=@data.xlsx" \
  -F "source_system=ZUP" \
  -F "import_type=employees"
```

#### Ошибки

- `400` — Неподдерживаемый формат файла или превышен размер

---

### GET /etl/imports

Список импортов.

**Аутентификация:** Bearer accessToken  
**Роль:** ADMIN (требуется)  
**CSRF:** Не требуется

#### Query Parameters

- `source_system?` — Источник системы
- `status?` — Статус импорта
- `limit?` — Лимит записей

#### Response

```typescript
Array<{
  id: string;
  source_system: string;
  import_type: string;
  status: string;
  records_count: number;
  processed_at: string | null;
}>
```

---

### GET /etl/imports/:id

Детали импорта.

**Аутентификация:** Bearer accessToken  
**Роль:** ADMIN (требуется)  
**CSRF:** Не требуется

#### Response

```typescript
{
  id: string;
  source_system: string;
  import_type: string;
  status: string;
  records_count: number;
  processed_at: string | null;
  statistics: {
    success: number;
    error: number;
    skipped: number;
  };
  errors: Array<string>;
}
```

#### Ошибки

- `404` — Импорт не найден

---

### GET /etl/imports/:id/file

Скачать исходный файл импорта.

**Аутентификация:** Bearer accessToken  
**Роль:** ADMIN (требуется)  
**CSRF:** Не требуется

#### Response

Бинарный поток файла (application/octet-stream или исходный MIME)

#### Ошибки

- `404` — Импорт или файл не найден

---

### POST /etl/imports/:id/retry

Повторить импорт.

**Аутентификация:** Bearer accessToken  
**Роль:** ADMIN (требуется)  
**CSRF:** Требуется для браузера

#### Response

```typescript
{
  id: string;
  status: 'PROCESSING';
}
```

#### Пример запроса

```bash
curl -X POST http://localhost:3000/api/etl/imports/<id>/retry \
  -H "Authorization: Bearer <accessToken>" \
  -H "X-CSRF-Token: <value>"
```

#### Ошибки

- `400` — Импорт не может быть повторен (не в статусе failed)
- `404` — Импорт не найден

---

## Enum значения

### UserRole

- `ADMIN` — Администратор
- `MANAGER` — Менеджер
- `SHIFT_MANAGER` — Менеджер смены
- `ANALYST` — Аналитик
- `EMPLOYEE` — Сотрудник

### DepartmentType

- `DIVISION` — Дивизион
- `DEPARTMENT` — Отдел
- `SECTION` — Секция
- `UNIT` — Юнит

### EmploymentType

- `MAIN` — Основной
- `PART_TIME` — Неполный

### EmployeeStatus

- `ACTIVE` — Активен
- `TERMINATED` — Уволен
- `ON_LEAVE` — В отпуске

### ShiftType

- `DAY_SHIFT` — Дневная смена
- `NIGHT_SHIFT` — Ночная смена
- `ROTATING` — Ротирующаяся

### ProductCategory

- `RAW_MATERIAL` — Сырье
- `SEMI_FINISHED` — Полуфабрикат
- `FINISHED_PRODUCT` — Готовая продукция
- `PACKAGING` — Упаковка

### OrderStatus

- `PLANNED` — Запланирован
- `IN_PROGRESS` — В работе
- `COMPLETED` — Завершен
- `CANCELLED` — Отменен

### QualityStatus

- `PENDING` — Ожидает
- `APPROVED` — Одобрено
- `REJECTED` — Отклонено

### QualityDecision

- `APPROVED` — Одобрено
- `REJECTED` — Отклонено
- `PENDING` — Ожидает

### SaleChannel

- `RETAIL` — Розница
- `WHOLESALE` — Опт
- `HORECA` — HoReCa
- `EXPORT` — Экспорт

### SensorQuality

- `GOOD` — Хорошее
- `DEGRADED` — Ухудшенное
- `BAD` — Плохое
