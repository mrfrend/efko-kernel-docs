# Troubleshooting

Руководство по диагностике и устранению проблем в системе EFKO Kernel.

## Логирование

### Структура логов

Система использует Pino для структурированного логирования. Логи пишутся в папку `logs/` в dev режиме:

- `logs/gateway.log` — логи API Gateway
- `logs/auth-service.log` — логи Auth Service
- `logs/personnel.log` — логи Personnel Service
- `logs/production.log` — логи Production Service
- `logs/etl.log` — логи ETL Service

### Формат логов

Логи в формате JSON:

```json
{
  "level": "info",
  "time": "2025-01-15T10:30:00Z",
  "requestId": "req-123",
  "userId": "user-456",
  "service": "gateway",
  "message": "Request received",
  "context": {
    "method": "GET",
    "url": "/api/personnel/employees"
  }
}
```

### Просмотр логов

```bash
# Просмотр логов в реальном времени
tail -f logs/gateway.log

# Поиск по requestId
grep "req-123" logs/*.log

# Поиск ошибок
grep '"level":"error"' logs/*.log

# Фильтрация по уровню
jq 'select(.level == "error")' logs/gateway.log
```

### Loki (Production)

В production логи отправляются в Loki через pino-loki. Используйте Grafana Loki для поиска и анализа логов.

---

## Распространенные проблемы

### Сервис не запускается

#### Симптомы

```
Error: Cannot connect to database
Error: RabbitMQ connection failed
Port already in use
```

#### Диагностика

1. Проверьте, что инфраструктура запущена:
   ```bash
   docker ps
   ```

2. Проверьте логи сервиса:
   ```bash
   cat logs/<service>.log
   ```

3. Проверьте переменные окружения в `.env`

4. Проверьте, что порты не заняты:
   ```bash
   lsof -i :3000
   ```

#### Решения

**PostgreSQL недоступен:**
```bash
# Перезапуск PostgreSQL
docker-compose restart postgres

# Проверка подключения
docker exec -it postgres psql -U postgres -d efko_kernel -c "SELECT 1"
```

**RabbitMQ недоступен:**
```bash
# Перезапуск RabbitMQ
docker-compose restart rabbitmq

# Проверка подключения
docker exec -it rabbitmq rabbitmqctl status
```

**MongoDB недоступен:**
```bash
# Перезапуск MongoDB
docker-compose restart mongo

# Проверка подключения
docker exec -it mongo mongosh --eval "db.stats()"
```

**Порт занят:**
```bash
# Найти процесс
lsof -i :3000

# Убить процесс
kill -9 <PID>

# Или изменить порт в .env
GATEWAY_PORT=3001
```

---

### RabbitMQ Connection Error

#### Симптомы

```
Error: AMQP connection failed
Error: Service unavailable (503)
Timeout waiting for RPC response
```

#### Диагностика

```bash
# Проверьте статус RabbitMQ
docker exec -it rabbitmq rabbitmqctl status

# Проверьте логи RabbitMQ
docker logs rabbitmq

# Проверьте AMQP_URI в .env
grep AMQP_URI .env
```

#### Решения

**Неверный AMQP_URI:**
```bash
# Правильный формат
AMQP_URI=amqp://guest:guest@localhost:5672
```

**RabbitMQ не запущен:**
```bash
docker-compose up -d rabbitmq
```

**Memory/Disk limit:**
```bash
# Проверьте лимиты
docker exec -it rabbitmq rabbitmqctl list_queues

# Сбросьте лимиты (dev mode)
docker exec -it rabbitmq rabbitmqctl set_vm_memory_high_watermark 0.8
```

---

### Database Connection Error

#### Симптомы

```
Error: Can't reach database server
Error: PrismaClientInitializationError
Connection timeout
```

#### Диагностика

```bash
# Проверьте статус PostgreSQL
docker exec -it postgres pg_isready

# Проверьте логи PostgreSQL
docker logs postgres

# Проверьте DATABASE_URL в .env
grep DATABASE_URL .env
```

#### Решения

**Неверный DATABASE_URL:**
```bash
# Правильный формат
DATABASE_URL=postgresql://postgres:password@localhost:5432/efko_kernel_auth
```

**Миграции не применены:**
```bash
cd apps/<service>
npx prisma migrate dev
npx prisma generate
```

**PostgreSQL не запущен:**
```bash
docker-compose up -d postgres
```

**Проверьте подключение:**
```bash
docker exec -it postgres psql -U postgres -d efko_kernel_auth -c "SELECT 1"
```

---

### Timeout ошибки в RPC

#### Симптомы

```
Error: RPC timeout
Error: Request timeout after 5000ms
504 Gateway Timeout
```

#### Диагностика

```bash
# Проверьте логи downstream сервиса
cat logs/personnel.log

# Проверьте RabbitMQ queues
docker exec -it rabbitmq rabbitmqctl list_queues

# Проверьте корреляцию
grep "requestId" logs/*.log
```

#### Решения

**Downstream сервис не запущен:**
```bash
npx nx serve personnel
```

**Очередь заблокирована:**
```bash
# Проверьте unacked messages
docker exec -it rabbitmq rabbitmqctl list_queues name messages messages_unacked

# Очистите очередь (dev mode)
docker exec -it rabbitmq rabbitmqctl purge_queue personnel-service.commands.queue
```

**Увеличьте timeout:**
```typescript
// В proxy service
await this.amqpConnection.publish(
  exchange,
  routingKey,
  payload,
  { timeout: 10000 }, // Увеличить до 10s
);
```

---

### Outbox не публикуется

#### Симптомы

```
Events not appearing in RabbitMQ
Outbox messages stuck in PENDING status
```

#### Диагностика

```sql
-- Проверьте outbox таблицу
SELECT * FROM outbox_messages 
WHERE status = 'FAILED' 
ORDER BY created_at DESC 
LIMIT 10;

-- Проверьте PENDING события
SELECT COUNT(*) FROM outbox_messages WHERE status = 'PENDING';
```

#### Решения

**Publisher не запущен:**
```bash
# Проверьте логи
grep "OutboxPeriodicPublisher" logs/personnel.log
```

**Ошибка публикации:**
```sql
-- Посмотрите errorMessage
SELECT eventType, errorMessage, retryCount 
FROM outbox_messages 
WHERE status = 'FAILED';
```

**Ручной retry:**
```sql
-- Сбросьте статус на PENDING
UPDATE outbox_messages 
SET status = 'PENDING', retryCount = 0, errorMessage = NULL 
WHERE id = '<id>';
```

---

### CSRF ошибки

#### Симптомы

```
401 Unauthorized on POST requests
CSRF token validation failed
```

#### Диагностика

```bash
# Проверьте логи
grep "CSRF" logs/gateway.log

# Проверьте cookies в браузере
document.cookie
```

#### Решения

**CSRF включен в dev:**
```bash
# Отключите в dev
CSRF_ENABLED=false
```

**Токен устарел:**
```bash
# Обновите сессию
POST /auth/refresh-session
```

**Mobile клиент:**
```typescript
// Убедитесь, что не отправляете cookie
// Refresh токен в теле запроса
{
  "refreshToken": "<token>"
}
```

---

### JWT валидация ошибки

#### Симптомы

```
401 Unauthorized
Invalid JWT token
Token expired
```

#### Диагностика

```bash
# Проверьте логи
grep "JWT" logs/auth-service.log

# Декодируйте токен на jwt.io
```

#### Решения

**Токен истек:**
```bash
# Обновите сессию
POST /auth/refresh-session
```

**Неверный секрет:**
```bash
# Проверьте JWT_ACCESS_SECRET
grep JWT_ACCESS_SECRET .env
```

**Issuer не совпадает:**
```bash
# Проверьте JWT_ACCESS_ISSUER
grep JWT_ACCESS_ISSUER .env
```

---

### Rate Limit превышен

#### Симптомы

```
429 Too Many Requests
```

#### Диагностика

```bash
# Проверьте логи
grep "rate limit" logs/gateway.log
```

#### Решения

**Подождите:**
- Лимит сбрасывается автоматически через TTL

**Увеличьте лимит:**
```typescript
@Throttle({ short: { limit: 50, ttl: 60_000 } })
```

**Используйте API ключ:**
- Для интеграций используйте отдельные механизмы

---

## Health Checks

### Проверка сервисов

```bash
# Gateway
curl http://localhost:3000/api

# RabbitMQ
curl http://localhost:15672/api/overview \
  -u guest:guest

# PostgreSQL
docker exec -it postgres pg_isready

# MongoDB
docker exec -it mongo mongosh --eval "db.stats()"
```

### Health endpoints

Если настроены health endpoints:

```bash
# Gateway health
curl http://localhost:3000/health

# Service health
curl http://localhost:3001/health  # auth-service
curl http://localhost:3002/health  # personnel
```

---

## Отладка

### Debug режим

```bash
# Запуск с debug логами
NODE_ENV=development LOG_LEVEL=debug npx nx serve gateway
```

### Включение трассировки

```bash
# Проверьте OpenTelemetry
grep "tracing" logs/gateway.log
```

### Проблемы с Prisma

```bash
# Prisma Studio для визуального просмотра БД
cd apps/<service>
npx prisma studio

# Сброс БД (dev mode)
npx prisma migrate reset
```

---

## RabbitMQ Диагностика

### Проверка очередей

```bash
# Список всех очередей
docker exec -it rabbitmq rabbitmqctl list_queues

# Сообщения в очереди
docker exec -it rabbitmq rabbitmqctl list_queues name messages

# Unacked сообщения
docker exec -it rabbitmq rabbitmqctl list_queues name messages_unacked
```

### Проверка exchanges

```bash
# Список exchanges
docker exec -it rabbitmq rabbitmqctl list_exchanges

# Bindings
docker exec -it rabbitmq rabbitmqctl list_bindings
```

### Очистка очередей (dev mode)

```bash
# Очистить конкретную очередь
docker exec -it rabbitmq rabbitmqctl purge_queue personnel-service.commands.queue

# Удалить очередь
docker exec -it rabbitmq rabbitmqctl delete_queue personnel-service.commands.queue
```

### Management UI

Откройте http://localhost:15672 для визуальной диагностики RabbitMQ.

---

## PostgreSQL Диагностика

### Проверка соединений

```bash
# Активные соединения
docker exec -it postgres psql -U postgres -c \
  "SELECT count(*) FROM pg_stat_activity;"

# Заблокированные запросы
docker exec -it postgres psql -U postgres -c \
  "SELECT * FROM pg_stat_activity WHERE state = 'idle in transaction';"
```

### Проверка размера БД

```bash
docker exec -it postgres psql -U postgres -c \
  "SELECT pg_size_pretty(pg_database_size('efko_kernel_auth'));"
```

### Проверка индексов

```bash
docker exec -it postgres psql -U postgres efko_kernel_auth -c \
  "SELECT * FROM pg_stat_user_indexes;"
```

### Проверка медленных запросов

```bash
# Включите log_min_duration_statement
docker exec -it postgres psql -U postgres -c \
  "ALTER SYSTEM SET log_min_duration_statement = 1000;"

# Перезагрузите PostgreSQL
docker-compose restart postgres
```

---

## MongoDB Диагностика

### Проверка статуса

```bash
docker exec -it mongo mongosh --eval "db.serverStatus()"
```

### Проверка размера коллекций

```bash
docker exec -it mongo mongosh --eval "db.getCollectionNames().forEach(function(c) { print(c + ': ' + db[c].count() + ' docs, ' + JSON.stringify(db[c].stats().size) + ' bytes'); })"
```

### Проверка индексов

```bash
docker exec -it mongo mongosh --eval "db.raw_imports.getIndexes()"
```

---

## ETL Проблемы

### Импорт застрял в PROCESSING

#### Диагностика

```javascript
// В MongoDB
db.raw_imports.find({ status: "PROCESSING" })
```

#### Решения

```javascript
// Измените статус на FAILED для retry
db.raw_imports.updateOne(
  { _id: ObjectId("...") },
  { $set: { status: "FAILED" } }
)

// Или retry через API
POST /etl/imports/:id/retry
```

### Ошибки трансформации

#### Диагностика

```bash
# Проверьте логи ETL
grep "transformation" logs/etl.log

# Проверьте transformation_log в MongoDB
db.transformation_log.find({ status: "ERROR" })
```

#### Решения

- Проверьте схему импорта
- Проверьте mapper для источника
- Проверьте валидацию данных

---

## Производительность

### Медленные запросы

#### Диагностика

```bash
# Проверьте логи на медленные операции
grep "duration" logs/*.log
```

#### Решения

- Добавьте индексы в Prisma schema
- Оптимизируйте запросы Prisma
- Используйте `select` для ограничения полей
- Используйте пагинацию

### Высокое использование памяти

#### Диагностика

```bash
# Проверьте использование памяти
docker stats
```

#### Решения

- Увеличьте память для Docker контейнеров
- Проверьте утечки памяти в коде
- Оптимизируйте запросы к БД

---

## Мониторинг

### Prometheus Metrics

```bash
# Проверьте метрики
curl http://localhost:3000/metrics
```

Ключевые метрики:
- `http_requests_total` — количество HTTP запросов
- `http_request_duration_seconds` — длительность запросов
- `rabbitmq_queue_messages` — сообщения в очередях
- `database_connections_active` — активные соединения с БД

### Grafana Dashboard

Если настроен Grafana:
- Откройте http://localhost:3000
- Проверьте дашборды для системы
- Мониторируйте аномалии

---

## Обращение за помощью

Если проблема не решена:

1. Соберите логи:
   ```bash
   tar -czf logs.tar.gz logs/
   ```

2. Соберите информацию об окружении:
   ```bash
   node --version
   npm --version
   docker --version
   docker-compose --version
   ```

3. Опишите шаги воспроизведения

4. Свяжитесь с командой поддержки

---

## Полезные команды

```bash
# Полный перезапуск инфраструктуры
docker-compose down && docker-compose up -d

# Очистка всех данных (dev mode)
docker-compose down -v

# Пересборка всех сервисов
npm run docker:build:all

# Проверка зависимостей
npm audit

# Linting
npx nx lint --all

# Тесты
npx nx test --all
```
