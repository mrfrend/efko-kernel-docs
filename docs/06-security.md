# Безопасность

Полное руководство по безопасности системы EFKO Kernel, включая аутентификацию, авторизацию, CSRF защиту и управление ключами.

## Обзор

Система использует многоуровневую модель безопасности:
- **Аутентификация** — JWT токены (access + refresh)
- **Авторизация** — ролевая модель на основе ролей
- **CSRF защита** — Double Submit Cookie для браузерных клиентов
- **Rate limiting** — защита от DDoS атак
- **Валидация** — проверка данных на границах системы

---

## Аутентификация

### JWT Токены

Система использует JWT (JSON Web Token) для аутентификации:

- **Access Token** — краткоживущий токен для доступа к API
- **Refresh Token** — долгоживущий токен для обновления сессии

### Access Token

**Назначение:** Доступ к защищенным эндпоинтам API  
**Алгоритм:** RS256 (RSA с SHA-256) или HS256  
**TTL:** Конфигурируется через `JWT_ACCESS_TTL` (по умолчанию 15 минут, во время разработки 7 дней, так как CORS_ORIGIN в development mode * и CORS_CREDENTIALS false)  
**Передача:** В заголовке `Authorization: Bearer <token>`

#### Структура Payload

```typescript
{
  sub: string;      // UUID пользователя
  email: string;    // Email пользователя
  role: UserRole;   // Роль пользователя
  iat: number;      // Issued At (timestamp)
  exp: number;      // Expiration (timestamp)
  iss: string;      // Issuer (из JWT_ACCESS_ISSUER)
}
```

#### Пример

```json
{
  "sub": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "email": "ivan@example.com",
  "role": "ADMIN",
  "iat": 1705248000,
  "exp": 1705253400,
  "iss": "efko-kernel"
}
```

---

### Refresh Token

**Назначение:** Обновление access токена без повторного логина  
**TTL:** Конфигурируется через `JWT_REFRESH_TTL` (по умолчанию 7 дней)  
**Хранение:** 
- Браузерные клиенты: httpOnly cookie
- Мобильные клиенты: в памяти приложения
- В dev режиме cookie не передается, ручка refresh недоступна


#### Rotation

Refresh токены ротируются при каждом обновлении сессии:
- Старый токен аннулируется (помечается как revoked)
- Выдается новый токен
- Защищает от replay атак

#### Хранение в БД

```prisma
model RefreshToken {
  id        String   @id @default(uuid())
  userId    String
  tokenHash String   @db.VarChar(255)
  expiresAt DateTime
  isRevoked Boolean  @default(false)
  createdAt DateTime @default(now())
  user      User     @relation(...)
}
```

---

### Password Hashing

Пароли хешируются с использованием bcrypt:
- **Алгоритм:** bcrypt
- **Salt rounds:** Конфигурируется (по умолчанию 10)
- **Хранение:** В поле `passwordHash` таблицы `users`

```typescript
// Хеирование
const hash = await bcrypt.hash(password, 10);

// Проверка
const isValid = await bcrypt.compare(password, hash);
```

---

## Авторизация

### Ролевая модель

Система использует ролевую модель с 5 предопределенными ролями:

| Роль | Код | Описание | Права |
|------|-----|----------|-------|
| Администратор | `ADMIN` | Полный доступ ко всем операциям | Все CRUD операции, управление пользователями |
| Менеджер | `MANAGER` | Управление данными в доменах | CRUD в Personnel и Production |
| Менеджер смены | `SHIFT_MANAGER` | Операционное управление | Чтение данных, создание смен |
| Аналитик | `ANALYST` | Только чтение | Только GET запросы |
| Сотрудник | `EMPLOYEE` | Базовый доступ | Только собственные данные |

### Реализация

#### Auth Guard

`AuthGuard` проверяет JWT токен и добавляет пользователя в запрос:

```typescript
@UseGuards(AuthGuard)
@Controller('personnel')
export class PersonnelController {
  @Get('employees')
  @Auth(UserRole.ADMIN, UserRole.MANAGER)
  getEmployees() {
    // Только ADMIN и MANAGER
  }
}
```

#### Role Guard

`RoleGuard` проверяет роль пользователя:

```typescript
@Auth(UserRole.ADMIN, UserRole.MANAGER)
@Post('departments')
createDepartment() {
  // Требуется ADMIN или MANAGER
}
```

#### Проверка в Downstream сервисах

Domain сервисы также проверяют роли:

```typescript
// В domain сервисе
if (!allowedRoles.includes(user.role)) {
  throw new ForbiddenException('Insufficient permissions');
}
```

---

## CSRF Защита

### Обзор

Gateway использует паттерн **Double Submit Cookie** для защиты от CSRF атак браузерных клиентов.

### Как это работает

1. **При логине:** сервер устанавливает cookie `XSRF-TOKEN` (не httpOnly, читаемый JS)
2. **При запросах:** браузер должен читать эту cookie и отправлять её значение в заголовке `X-CSRF-Token`
3. **Проверка:** сервер сравнивает значение cookie и заголовка
4. **Результат:** несоответствие или отсутствие заголовка → 401 Unauthorized

### Mobile клиенты

Мобильные клиенты не используют cookies и автоматически исключаются из CSRF проверок:
- Нет cookie механизма → проверка пропускается
- Refresh токен передается в теле запроса при обновлении сессии

### Конфигурация

| Переменная окружения | Значения | Описание |
|---------------------|----------|----------|
| `CSRF_ENABLED` | `true` / `false` | Принудительное включение CSRF |
| `NODE_ENV` | `production` / `development` | CSRF всегда включен в production |

В development CSRF пропускается, если `CSRF_ENABLED=true` не установлено.

### Cookie настройки

`XSRF-TOKEN` cookie настраивается в `CookieConfigService`:
- `httpOnly: false` — должен быть читаемым JavaScript
- `sameSite: 'strict'` в production
- Очищается при logout вместе с `refreshToken`

### Endpoints

Все `POST`, `PATCH`, `DELETE` эндпоинты требуют CSRF валидации для браузерных клиентов. Токен генерируется и устанавливается на:
- `POST /auth/login`
- `POST /auth/refresh-session`

### Интеграция для браузерных клиентов

```typescript
// Чтение CSRF токена после логина
function getCsrfToken(): string {
  return document.cookie
    .split('; ')
    .find(row => row.startsWith('XSRF-TOKEN='))
    ?.split('=')[1] ?? '';
}

// Добавление к мутирующим запросам
fetch('/api/personnel/employees', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${accessToken}`,
    'X-CSRF-Token': getCsrfToken(),
  },
  body: JSON.stringify(payload),
});
```

### Csrf Guard

`CsrfGuard` применяется глобально через `APP_GUARD` в `AppModule`:

1. `GET`, `HEAD`, `OPTIONS` — пропускаются (safe methods)
2. Нет `XSRF-TOKEN` cookie — пропускается (mobile клиент)
3. Cookie есть, заголовок отсутствует — 401 Unauthorized
4. Значения не совпадают — 401 Unauthorized
5. Значения совпадают — запрос проходит

---

## JWT Key Rotation

### Обзор

Регулярная ротация JWT ключей важна для безопасности системы.

### Зачем ротировать ключи

- **Безопасность:** Ограничивает окно экспозиции при компрометации ключа
- **Compliance:** Многие стандарты безопасности требуют периодической ротации
- **Best Practice:** Индустриальный стандарт для production систем

### Переменные окружения

- `JWT_ACCESS_SECRET` — секрет для подписи access токенов
- `JWT_REFRESH_SECRET` — секрет для подписи refresh токенов
- `JWT_ACCESS_ISSUER` — идентификатор issuer для валидации JWT

### Стратегия ротации

#### Вариант 1: Graceful Rotation с поддержкой двойных ключей

Позволяет использовать старые и новые ключи во время переходного периода.

**Шаги:**

1. **Генерация новых ключей**
   ```bash
   node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"
   ```

2. **Обновление конфигурации с поддержкой двойных ключей**
   ```typescript
   JwtModule.registerAsync({
     secret: process.env.JWT_ACCESS_SECRET,
     signOptions: {
       issuer: process.env.JWT_ACCESS_ISSUER,
     },
     verifyOptions: {
       issuer: process.env.JWT_ACCESS_ISSUER,
       algorithms: ['HS256'],
     },
   })
   ```

3. **Развертывание нового ключа на все сервисы одновременно**
   - Обновить переменные окружения для: gateway, auth-service
   - Перезапустить сервисы

4. **Мониторинг 1-2 недели**
   - Проверять логи на ошибки аутентификации
   - Следить за ошибками валидации JWT

5. **Удаление старого ключа**
   - Обновить переменные окружения
   - Перезапустить сервисы

#### Вариант 2: Немедленная ротация (рекомендуется для некритичных систем)

Проще, но вызывает кратковременное прерывание — существующие токены становятся невалидными.

**Шаги:**

1. **Генерация нового ключа**
   ```bash
   node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"
   ```

2. **Обновление переменных окружения**
   ```bash
   JWT_ACCESS_SECRET=<new-secret>
   ```

3. **Перезапуск всех сервисов**
   ```bash
   npx nx serve gateway
   npx nx serve auth-service
   ```

4. **Уведомление пользователей**
   - Существующие сессии будут инвалидированы
   - Пользователям нужно повторно войти

### Чек-лист перед ротацией

- [ ] Генерация новых секретных ключей
- [ ] Бэкап текущих секретов
- [ ] Планирование окна обслуживания (при немедленной ротации)
- [ ] Подготовка плана отката
- [ ] Уведомление стейкхолдеров
- [ ] Тестирование нового ключа в staging окружении

### Верификация после ротации

```bash
# Тест аутентификации с новым токеном
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}'

# Проверка подписи токена на jwt.io
```

### Процедура отката

Если проблемы после ротации:

1. Откат к предыдущему секрету в переменных окружения
2. Перезапуск всех сервисов
3. Исследование логов для определения причины
4. Повторная ротация после исправления проблем

### Рекомендуемый график ротации

- **Development:** каждые 30 дней
- **Staging:** каждые 60 дней
- **Production:** каждые 90 дней

### Best Practices для хранения ключей

1. **Никогда не коммитить секреты в git** — использовать переменные окружения или secret management
2. **Использовать сильные секреты** — минимум 32 байта (256 бит) для HS256
3. **Регулярная ротация ключей** — следовать графику выше
4. **Мониторинг несанкционированного доступа** — проверять на неожиданные ошибки аутентификации
5. **Разные секреты для разных окружений** — dev, staging, production

### Экстренная ротация

Если ключ скомпрометирован:

1. **Немедленная ротация** — использовать Вариант 2 (немедленная ротация)
2. **Исследование логов** — определить когда произошла компрометация
3. **Уведомление security team** — если применимо
4. **Проверка логов доступа** — определить потенциально затронутых пользователей
5. **Принудительный сброс паролей** — если учетные данные пользователей могут быть скомпрометированы

---

## Rate Limiting

### Профили лимитов

Система использует три профиля rate limiting:

| Профиль | Лимит | Период | Применение |
|---------|-------|--------|------------|
| short | 20 req | 1 s | Глобально |
| medium | 100 req | 10 s | Глобально |
| long | 500 req | 60 s | Глобально |

### Auth endpoints

Auth endpoints имеют отдельные строгие лимиты:
- `POST /auth/register` — 3 req / 60 s
- `POST /auth/login` — 5 req / 60 s

### Ответ при превышении лимита

```json
{
  "statusCode": 429,
  "message": "Too Many Requests",
  "error": "Too Many Requests"
}
```

### Конфигурация

```typescript
@Throttle({ short: { limit: 3, ttl: 60_000 } })
@Post('register')
register() {
  // Лимит: 3 запроса за 60 секунд
}
```

---

## Валидация

### ValidationPipe

NestJS ValidationPipe применяется глобально для валидации DTO на границах системы:

```typescript
app.useGlobalPipes(
  new ValidationPipe({
    whitelist: true,    // Отбрасывать неизвестные поля
    forbidNonWhitelisted: true, // Ошибка при неизвестных полях
    transform: true,    // Автоматическое преобразование типов
  }),
);
```

### Пример DTO

```typescript
export class RegisterUserCommandDTO {
  @IsEmail()
  email: string;

  @IsString()
  @MinLength(8)
  password: string;

  @IsString()
  @IsNotEmpty()
  firstName: string;

  @IsString()
  @IsNotEmpty()
  lastName: string;

  @IsEnum(UserRole)
  @IsOptional()
  role?: UserRole;
}
```

### Ошибки валидации

```json
{
  "statusCode": 400,
  "message": [
    "email must be an email",
    "password must be longer than or equal to 8 characters"
  ],
  "error": "Bad Request"
}
```

---

## Безопасность окружения

### Переменные окружения

Критичные переменные окружения:

```bash
# JWT
JWT_ACCESS_SECRET=<strong-secret>
JWT_REFRESH_SECRET=<strong-secret>
JWT_ACCESS_ISSUER=efko-kernel
JWT_ACCESS_TTL=15m
JWT_REFRESH_TTL=7d

# CSRF
CSRF_ENABLED=true
NODE_ENV=production

# Базы данных
DATABASE_URL=<postgresql-connection-string>
MONGO_URI=<mongodb-connection-string>
AMQP_URI=<rabbitmq-connection-string>
```

### Хранение секретов

**Не делайте:**
- Коммитить `.env` файлы в git
- Хранить секреты в коде
- Использовать слабые пароли

**Делайте:**
- Использовать секреты в переменных окружения
- Использовать secret management (Vault, AWS Secrets Manager, etc.)
- Генерировать сильные случайные секреты
- Разные секреты для разных окружений

---

## Логирование безопасности

### Аудит событий

Система логирует следующие события безопасности:
- Неудачные попытки логина
- Попытки доступа без авторизации
- Попытки доступа с недостаточными правами
- CSRF ошибки
- Rate limit превышения
- JWT валидация ошибки

### Логи

Логи пишутся в формате JSON через Pino:
- `logs/gateway.log`
- `logs/auth-service.log`
- `logs/personnel.log`
- `logs/production.log`

Пример лога:

```json
{
  "level": "warn",
  "time": "2025-01-15T10:30:00Z",
  "requestId": "req-123",
  "userId": "user-456",
  "action": "AUTH_LOGIN_FAILED",
  "ip": "192.168.1.100",
  "message": "Invalid credentials for user ivan@example.com"
}
```

---

## Best Practices

### Для разработчиков

1. **Всегда используйте HTTPS** в production
2. **Валидируйте все входные данные** на границах системы
3. **Используйте параметризованные запросы** для БД
4. **Не暴露** детали ошибок в production
5. **Логируйте** события безопасности
6. **Регулярно обновляйте** зависимости
7. **Используйте** CSP headers для веб-клиентов

### Для DevOps

1. **Разделяйте** секреты по окружениям
2. **Ротируйте** ключи регулярно
3. **Мониторируйте** подозрительную активность
4. **Резервируйте** конфигурацию
5. **Используйте** managed сервисы (RDS, etc.)
6. **Настраивайте** firewall правила
7. **Включите** audit logging

### Для клиентов

1. **Храните** токены безопасно
2. **Не храните** секреты в коде клиента
3. **Используйте** HTTPS для всех запросов
4. **Валидируйте** SSL сертификаты
5. **Реализуйте** timeout для запросов
6. **Обрабатывайте** ошибки безопасности корректно
7. **Логируйте** события безопасности на клиенте

---

## Мониторинг безопасности

### Ключевые метрики

- Количество неудачных попыток логина
- Количество CSRF ошибок
- Количество rate limit превышений
- Количество JWT валидация ошибок
- Количество ошибок авторизации

### Алерты

Настраивайте алерты для:
- Резкого увеличения неудачных попыток логина
- Успешных логинов с необычных IP
- Множественных CSRF ошибок от одного IP
- Превышения rate limit

---

## Ссылки

- [JWT Best Practices (RFC 8725)](https://tools.ietf.org/html/rfc8725)
- [NestJS Security Documentation](https://docs.nestjs.com/security)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
