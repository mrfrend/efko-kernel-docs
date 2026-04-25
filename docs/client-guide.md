# Client Guide

Руководство по интеграции с REST API EFKO Kernel для веб и мобильных клиентов.

Полная документация API доступна в Swagger: `GET /api/swagger` или `GET /api/swagger/json`.

## Общие сведения

- **Base URL:** `http://localhost:3000/api` (dev) или ваш production URL
- **Формат данных:** JSON (`Content-Type: application/json`)
- **Аутентификация:** Bearer JWT в заголовке `Authorization`
- **Корреляция:** `requestId` проставляется автоматически через middleware; можно передать вручную заголовком `x-request-id`
- **Язык ответов:** Русский (сообщения об ошибках)

---

## Аутентификация

### Схема токенов

Система использует двухтокенную схему:

| Токен | Где хранится (Web) | Где хранится (Mobile) | TTL | Назначение |
|---|---|---|---|---|
| `accessToken` | Память приложения | Память приложения | 15 минут (по умолчанию) | Bearer в `Authorization` |
| `refreshToken` | httpOnly cookie | Secure storage (Keychain/Keystore) | 7 дней (по умолчанию) | Обновление сессии |

Access token передаётся в каждом защищённом запросе:
```
Authorization: Bearer <accessToken>
```

### Жизненный цикл сессии

```
register / login
    └─> получить accessToken + refreshToken
           │
           ▼
    использовать accessToken для запросов
           │
           ▼ (accessToken истёк → 401)
    POST /auth/refresh-session
           │
           ▼
    новый accessToken + ротация refreshToken
           │
           ▼ (выход)
    POST /auth/logout
```

---

## Веб клиенты (Browser)

### Особенности

- Используют cookies для refresh токена
- Требуют CSRF защиту (Double Submit Cookie)
- Доступен XSRF-TOKEN cookie (не httpOnly)

### Хранение токенов

```typescript
// Храните accessToken в памяти (не в localStorage)
let accessToken: string | null = null;

// Refresh token хранится в httpOnly cookie (автоматически)
// Не храните в localStorage для защиты от XSS
```

### Чтение CSRF токена

```typescript
function getCsrfToken(): string {
  return document.cookie
    .split('; ')
    .find(row => row.startsWith('XSRF-TOKEN='))
    ?.split('=')[1] ?? '';
}
```

### Пример: Вход в систему

```typescript
async function login(email: string, password: string) {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });

  const data = await response.json();
  
  // Сохраняем accessToken в памяти
  accessToken = data.accessToken;
  
  // Cookies (refreshToken и XSRF-TOKEN) устанавливаются автоматически
  return data;
}
```

### Пример: Защищенный запрос

```typescript
async function createDepartment(name: string, code: string) {
  const response = await fetch('/api/personnel/departments', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`,
      'X-CSRF-Token': getCsrfToken(), // Обязательно для POST/PATCH/DELETE
    },
    body: JSON.stringify({ name, code, type: 'DIVISION' }),
  });

  if (response.status === 401) {
    // Попробовать обновить сессию
    await refreshSession();
    // Повторить запрос
    return createDepartment(name, code);
  }

  return response.json();
}
```

### Пример: Обновление сессии

```typescript
async function refreshSession() {
  const response = await fetch('/api/auth/refresh-session', {
    method: 'POST',
    headers: {
      'X-CSRF-Token': getCsrfToken(), // Обязательно
    },
    // Cookies отправляются автоматически
  });

  if (!response.ok) {
    // Редирект на логин
    window.location.href = '/login';
    return;
  }

  const data = await response.json();
  accessToken = data.accessToken;
  // Cookies ротируются автоматически
}
```

### Пример: Выход из системы

```typescript
async function logout() {
  await fetch('/api/auth/logout', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'X-CSRF-Token': getCsrfToken(),
    },
  });

  accessToken = null;
  // Cookies очищаются автоматически
  window.location.href = '/login';
}
```

### Обработка ошибок

```typescript
async function apiRequest(url: string, options: RequestInit = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`,
      ...options.headers,
    },
  });

  if (response.status === 401) {
    // Попробовать refresh
    await refreshSession();
    // Повторить запрос
    return apiRequest(url, options);
  }

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || 'Request failed');
  }

  return response.json();
}
```

---

## Мобильные клиенты (Mobile)

### Особенности

- Не используют cookies
- CSRF проверка автоматически пропускается
- Refresh token хранится в защищенном хранилище
- Refresh token передается в теле запроса

### Хранение токенов

```typescript
// iOS (Swift)
// Храните accessToken в памяти
var accessToken: String?

// Храните refreshToken в Keychain
KeychainHelper.set("refreshToken", value: refreshToken)

// Android (Kotlin)
// Храните accessToken в памяти
var accessToken: String? = null

// Храните refreshToken в EncryptedSharedPreferences
val sharedPreferences = EncryptedSharedPreferences.create(...)
sharedPreferences.edit().putString("refreshToken", refreshToken).apply()
```

### Пример: Вход в систему (React Native)

```typescript
import SecureStore from 'expo-secure-store';

async function login(email: string, password: string) {
  const response = await fetch(API_URL + '/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });

  const data = await response.json();
  
  // Сохраняем accessToken в памяти
  accessToken = data.accessToken;
  
  // Сохраняем refreshToken в SecureStore
  await SecureStore.setItemAsync('refreshToken', data.refreshToken);
  
  return data;
}
```

### Пример: Защищенный запрос (React Native)

```typescript
async function createDepartment(name: string, code: string) {
  const response = await fetch(API_URL + '/personnel/departments', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`,
      // X-CSRF-Token НЕ нужен для мобильных клиентов
    },
    body: JSON.stringify({ name, code, type: 'DIVISION' }),
  });

  if (response.status === 401) {
    // Попробовать обновить сессию
    await refreshSession();
    return createDepartment(name, code);
  }

  return response.json();
}
```

### Пример: Обновление сессии (React Native)

```typescript
async function refreshSession() {
  const refreshToken = await SecureStore.getItemAsync('refreshToken');
  
  if (!refreshToken) {
    // Редирект на логин
    navigation.navigate('Login');
    return;
  }

  const response = await fetch(API_URL + '/auth/refresh-session', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ refreshToken }), // Refresh токен в теле запроса
  });

  if (!response.ok) {
    // Удалить refresh токен и редирект на логин
    await SecureStore.deleteItemAsync('refreshToken');
    navigation.navigate('Login');
    return;
  }

  const data = await response.json();
  accessToken = data.accessToken;
  
  // Сохранить новый refresh токен (rotation)
  await SecureStore.setItemAsync('refreshToken', data.refreshToken);
}
```

### Пример: Выход из системы (React Native)

```typescript
async function logout() {
  const refreshToken = await SecureStore.getItemAsync('refreshToken');
  
  await fetch(API_URL + '/auth/logout', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ userId, refreshToken }),
  });

  accessToken = null;
  await SecureStore.deleteItemAsync('refreshToken');
  navigation.navigate('Login');
}
```

---

## Ключевые различия Web vs Mobile

| Аспект | Web (Браузер) | Mobile (Приложение) |
|--------|--------------|---------------------|
| **Refresh Token** | httpOnly cookie | Secure storage (Keychain/Keystore/SecureStore) |
| **CSRF Token** | Требуется (X-CSRF-Token header) | Не требуется (автоматический пропуск) |
| **Refresh Session** | Cookies отправляются автоматически | Refresh токен в теле запроса |
| **Хранение Access Token** | Память приложения | Память приложения |
| **Logout** | Cookies очищаются автоматически | Ручное удаление из secure storage |

---

## Эндпоинты аутентификации

### Жизненный цикл сессии

```
register / login
    └─> получить accessToken + refreshToken (cookie)
           │
           ▼
    использовать accessToken для запросов
           │
           ▼ (accessToken истёк → 401)
    POST /auth/refresh-session
           │
           ▼
    новый accessToken + ротация refreshToken
           │
           ▼ (выход)
    POST /auth/logout
```

---

## CSRF-защита (только браузерные клиенты)

Используется паттерн **Double Submit Cookie**.

**Мобильные клиенты** не используют cookies — CSRF-проверка для них автоматически пропускается.

### Как работает

1. После `POST /auth/login` сервер устанавливает cookie `XSRF-TOKEN` (не `httpOnly` — доступна из JS).
2. Браузерный клиент обязан читать эту cookie и передавать её значение в заголовке `X-CSRF-Token` при каждом мутирующем запросе (`POST`, `PATCH`, `DELETE`).
3. Несовпадение заголовка и cookie → `401 Unauthorized`.
4. `GET`, `HEAD`, `OPTIONS` — CSRF не проверяется.

### Когда обновляется токен

- Устанавливается при `POST /auth/login`
- Ротируется при `POST /auth/refresh-session`
- Очищается при `POST /auth/logout`

### Заголовок

```
X-CSRF-Token: <значение cookie XSRF-TOKEN>
```

---

## Эндпоинты аутентификации

### `POST /auth/register`

Регистрация нового пользователя.

- Аутентификация: не требуется
- CSRF: требуется для браузера
- Rate limit: отдельный (строгий)
- Тело: `{ email, password, firstName, lastName, role? }`
- Ответ: `{ accessToken, user }`

### `POST /auth/login`

Вход в систему.

- Аутентификация: не требуется
- CSRF: требуется для браузера
- Rate limit: отдельный (строгий)
- Тело: `{ email, password }`
- Ответ: `{ accessToken, user }`
- Побочный эффект: устанавливает cookies `refreshToken` и `XSRF-TOKEN`

### `POST /auth/refresh-session`

Обновление сессии по refresh token.

- Аутентификация: не требуется (refresh token — через cookie или тело)
- CSRF: требуется для браузера
- Тело (мобильные): `{ refreshToken }` — для клиентов без cookie
- Ответ: `{ accessToken }`
- Побочный эффект: ротирует `refreshToken` cookie и `XSRF-TOKEN`

### `GET /auth/me`

Получить профиль текущего пользователя.

- Аутентификация: Bearer accessToken
- Ответ: `{ id, email, firstName, lastName, role, isActive, ... }`
- Примечание: данные догружаются из `auth-service` и кэшируются на 30 с

### `POST /auth/logout`

Завершение сессии.

- Аутентификация: Bearer accessToken
- CSRF: требуется для браузера
- Ответ: `204 No Content`
- Побочный эффект: очищает cookies `refreshToken` и `XSRF-TOKEN`

---

## Ролевая модель

### Роли

| Роль | Описание |
|---|---|
| `ADMIN` | Полный доступ, управление пользователями |
| `MANAGER` | Управление персоналом и производством |
| `SHIFT_MANAGER` | Операции со сменами и выпуском |
| `ANALYST` | Доступ на чтение к аналитическим данным |

Роль пользователя возвращается в `GET /auth/me` и в payload JWT.

### Проверка авторизации

При недостаточной роли → `403 Forbidden`.  
При отсутствии или невалидном токене → `401 Unauthorized`.

---

## Управление пользователями

Все маршруты требуют роли `ADMIN`.

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/users` | Список всех пользователей |
| `PATCH` | `/users/:userId` | Обновить данные пользователя |
| `POST` | `/users/deactivate` | Деактивировать пользователя |

---

## Personnel API

Маршруты защищены — требуемые роли зависят от операции (чтение: `ANALYST`+, запись: `MANAGER`+).

| Ресурс | Маршруты |
|---|---|
| Подразделения | `GET/POST /personnel/departments`, `GET/PATCH/DELETE /personnel/departments/:id` |
| Должности | `GET/POST /personnel/positions`, `GET/PATCH/DELETE /personnel/positions/:id` |
| Сотрудники | `GET/POST /personnel/employees`, `GET/PATCH/DELETE /personnel/employees/:id` |
| Шаблоны смен | `GET/POST /personnel/shift-templates`, `GET/PATCH/DELETE /personnel/shift-templates/:id` |

---

## Production API

Маршруты защищены — требуемые роли зависят от операции.

| Ресурс | Маршруты |
|---|---|
| Продукты | `GET/POST /production/products`, `GET/PATCH/DELETE /production/products/:id` |
| Производственные заказы | `GET/POST /production/orders`, `GET/PATCH/DELETE /production/orders/:id` |
| Выпуск продукции | `GET/POST /production/output`, `GET /production/output/:id` |
| Продажи | `GET/POST /production/sales`, `GET /production/sales/summary` |
| Складские остатки | `GET /production/inventory` |
| Контроль качества | `GET/POST /production/quality` |
| Показания датчиков | `GET/POST /production/sensors` |
| KPI | `GET /production/kpi` |

---

## ETL API

Требуется роль `ADMIN`.

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/etl/import` | Запустить импорт (JSON payload) |
| `POST` | `/etl/import/file` | Загрузить файл (multipart, макс. 20 MB) |
| `GET` | `/etl/imports` | Список импортов |
| `GET` | `/etl/imports/:id` | Статус импорта |
| `GET` | `/etl/imports/:id/file` | Скачать исходный файл |
| `POST` | `/etl/imports/:id/retry` | Повторить неудавшийся импорт |

---

## Обработка ошибок

### Стандартная структура ошибки

```json
{
  "statusCode": 401,
  "message": "Unauthorized",
  "error": "Unauthorized"
}
```

### Коды ошибок аутентификации

| HTTP | Причина |
|---|---|
| `401` | Невалидный/истёкший токен, неверные credentials, ошибка CSRF |
| `403` | Недостаточная роль |
| `404` | Пользователь не найден |
| `409` | Пользователь уже существует |
| `429` | Rate limit превышен |
| `503` | Downstream-сервис недоступен |
| `504` | Downstream-сервис не ответил вовремя (RPC timeout) |

---

## Rate Limiting

Три профиля, применяются глобально:

| Профиль | Лимит |
|---|---|
| short | 20 req / 1 s |
| medium | 100 req / 10 s |
| long | 500 req / 60 s |

`/auth/register` и `/auth/login` имеют более строгие отдельные лимиты.

---

## Рекомендации для клиентов

**Браузер (Web)**
- Хранить `accessToken` в памяти (не в `localStorage`) — защита от XSS.
- Читать `XSRF-TOKEN` из cookie и передавать в `X-CSRF-Token` при каждом мутирующем запросе.
- При получении `401` на защищённом маршруте — пробовать `POST /auth/refresh-session`; если снова `401` — редиректить на логин.

**Мобильные клиенты**
- CSRF-заголовок не нужен.
- Хранить `refreshToken` в защищённом хранилище (Keychain / Keystore).
- При `POST /auth/refresh-session` передавать `refreshToken` в теле запроса.
- `refreshToken` cookie не устанавливается для мобильных клиентов (нет cookie-механизма).

**AI-агенты**
- Аутентифицироваться через `POST /auth/login`, сохранить `accessToken`.
- Обновлять через `POST /auth/refresh-session` при `401`.
- CSRF-заголовок не нужен (нет cookie).
- Полные контракты запросов и ответов — в `GET /api/swagger/json`.
