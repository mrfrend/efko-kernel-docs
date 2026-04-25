# Quick Start - Быстрый старт для разработчиков

Пошаговое руководство для быстрого запуска системы EFKO Kernel в режиме разработки.

## Требования к окружению

### Обязательные

- **Node.js** — версии 20.x или выше
- **npm** — версии 9.x или выше (или pnpm/yarn)
- **Docker** — версии 24.x или выше
- **Docker Compose** — версии 2.x или выше

### Рекомендуемые

- **Git** — для клонирования репозитория
- **VS Code** — с расширениями для NestJS и Docker
- **Postman** — или другой HTTP клиент для тестирования API

## Установка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd efko-kernel
```

### 2. Установка зависенций

```bash
npm install
```

Это установит зависимости для всего монорепозитория, включая все сервисы и библиотеки.

### 3. Настройка переменных окружения

Скопируйте пример файла окружения:

```bash
cp .env.example .env
```

Отредактируйте `.env` при необходимости. Основные переменные:

- `AMQP_URI` — строка подключения к RabbitMQ
- `DATABASE_URL` — строки подключения к PostgreSQL для каждого сервиса
- `MONGO_URI` — строка подключения к MongoDB для ETL
- `JWT_ACCESS_SECRET`, `JWT_REFRESH_SECRET` — секреты для JWT токенов

## Запуск инфраструктуры

Система требует следующую инфраструктуру:

- PostgreSQL (для auth, personnel, production)
- RabbitMQ (для межсервисной коммуникации)
- MongoDB (для ETL)

### Запуск базовой инфраструктуры

```bash
npm run infrastructure:up
```

Эта команда запустит:
- PostgreSQL на порту 5432
- RabbitMQ на порте 5672 (UI на 15672)
- MongoDB на порту 27017

### Проверка инфраструктуры

```bash
# Проверка RabbitMQ Management UI
open http://localhost:15672
# Логин: guest / guest

# Проверка PostgreSQL
docker ps | grep postgres

# Проверка MongoDB
docker ps | grep mongo
```

## Применение миграций базы данных

Каждый сервис с PostgreSQL требует применения миграций:

### Auth Service

```bash
cd apps/auth-service
npx prisma migrate dev
npx prisma generate
cd ../..
```

### Personnel Service

```bash
cd apps/personnel
npx prisma migrate dev
npx prisma generate
cd ../..
```

### Production Service

```bash
cd apps/production
npx prisma migrate dev
npx prisma generate
cd ../..
```

## Запуск сервисов в режиме разработки

### Запуск всех сервисов

В отдельном терминале для каждого сервиса:

```bash
# Terminal 1: Gateway
npx nx serve gateway

# Terminal 2: Auth Service
npx nx serve auth-service

# Terminal 3: Personnel Service
npx nx serve personnel

# Terminal 4: Production Service
npx nx serve production

# Terminal 5: ETL Service
npx nx serve etl
```

### Запуск конкретного сервиса

```bash
npx nx serve <service-name>
```

Доступные сервисы:
- `gateway`
- `auth-service`
- `personnel`
- `production`
- `etl`

### Проверка запуска сервисов

Каждый сервис должен показать сообщение о успешном запуске:

```
Nest application successfully started
```

## Проверка работоспособности

### 1. Проверка Gateway

```bash
curl http://localhost:3000/api
```

Ожидаемый ответ: JSON с информацией о API или redirect на Swagger.

### 2. Проверка Swagger UI

Откройте в браузере:

```
http://localhost:3000/api/swagger
```

Вы должны увидеть Swagger UI с документацией API.

### 3. Проверка RabbitMQ

Откройте RabbitMQ Management UI:

```
http://localhost:15672
```

Проверьте наличие exchanges:
- `efko.auth.commands`
- `efko.auth.queries`
- `efko.auth.events`
- `efko.personnel.commands`
- `efko.personnel.queries`
- `efko.personnel.events`
- `efko.production.commands`
- `efko.production.queries`
- `efko.production.events`

### 4. Первый тестовый запрос

#### Регистрация пользователя

```bash
curl -X POST http://localhost:3000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePassword123!",
    "firstName": "Иван",
    "lastName": "Иванов",
    "role": "ADMIN"
  }'
```

Ожидаемый ответ:

```json
{
  "id": "uuid",
  "email": "test@example.com",
  "fullName": "Иванов Иван",
  "role": "ADMIN",
  "isActive": true,
  "employeeId": null
}
```

#### Вход в систему

```bash
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePassword123!"
  }'
```

Ожидаемый ответ:

```json
{
  "accessToken": "eyJhbGciOiJSUzI1NiIs...",
  "refreshToken": "eyJhbGciOiJSUzI1NiIs..."
}
```

#### Получение текущего пользователя

```bash
curl -X GET http://localhost:3000/api/auth/me \
  -H "Authorization: Bearer <accessToken>"
```

Ожидаемый ответ:

```json
{
  "id": "uuid",
  "email": "test@example.com",
  "fullName": "Иванов Иван",
  "role": "ADMIN",
  "isActive": true,
  "employeeId": null
}
```

## Seed данных (опционально)

Для заполнения базы данных тестовыми данными:

```bash
# Seed всех сервисов
npm run seed:all

# Или по отдельности
npm run seed:auth
npm run seed:personnel
npm run seed:production
```

## Запуск с Observability Stack

Для запуска с полным стеком мониторинга (Grafana, Loki, Tempo):

```bash
npm run obs:up
```

Доступные UI:
- **Grafana:** http://localhost:3000
- **Loki:** http://localhost:3100
- **Tempo:** http://localhost:3200

## Полезные команды

### Nx команды

```bash
# Сборка сервиса
npx nx build <service-name>

# Запуск тестов
npx nx test <service-name>

# Линтинг
npx nx lint <service-name>

# Показать информацию о проекте
npx nx show project <service-name>

# Граф зависимостей
npx nx graph
```

### Prisma команды

```bash
# Создание миграции
npx prisma migrate dev --name <migration-name>

# Применение миграций в production
npx prisma migrate deploy

# Генерация клиента
npx prisma generate

# Открытие Prisma Studio
npx prisma studio
```

### Docker команды

```bash
# Остановка инфраструктуры
npm run infrastructure:down

# Остановка observability
npm run obs:down

# Сборка Docker образа сервиса
npm run docker:build:<service-name>

# Сборка всех образов
npm run docker:build:all

# Запуск production стека
npm run prod:up

# Логи production
npm run prod:logs
```

## Структура проекта

```
efko-kernel/
├── apps/                    # Сервисы
│   ├── gateway/            # API Gateway
│   ├── auth-service/       # Auth Service
│   ├── personnel/          # Personnel Service
│   ├── production/         # Production Service
│   └── etl/                # ETL Service
├── libs/                    # Общие библиотеки
│   ├── contracts/          # RabbitMQ контракты
│   ├── interfaces/         # TypeScript интерфейсы
│   └── nest-utils/         # NestJS утилиты
├── docs/                    # Документация
├── docker/                  # Docker конфигурации
└── tools/                   # Инструменты и скрипты
```

## Разработка

### Добавление нового сервиса

```bash
npx nx g @nx/nest:app <service-name>
```

### Добавление новой библиотеки

```bash
npx nx g @nx/node:lib <lib-name>
```

### Работа с контрактами

Контракты находятся в `libs/contracts/src/`:

- `auth/` — auth команды, запросы, события
- `personnel/` — personnel команды, запросы, события
- `production/` — production команды, запросы, события
- `etl/` — etl события

При добавлении новой команды/события:

1. Создайте файл в соответствующей папке
2. Добавьте export в `index.ts`
3. Обновите потребляющий сервис

### Логирование

Логи пишутся в папку `logs/` в dev режиме:

- `logs/gateway.log`
- `logs/auth-service.log`
- `logs/personnel.log`
- `logs/production.log`
- `logs/etl.log`

Файлы очищаются при каждом запуске сервиса.

## Troubleshooting

### Сервис не запускается

1. Проверьте, что инфраструктура запущена:
   ```bash
   docker ps
   ```

2. Проверьте логи сервиса в `logs/<service>.log`

3. Проверьте переменные окружения в `.env`

### RabbitMQ connection error

1. Проверьте, что RabbitMQ запущен:
   ```bash
   docker ps | grep rabbitmq
   ```

2. Проверьте `AMQP_URI` в `.env`

3. Перезапустите RabbitMQ:
   ```bash
   docker-compose restart rabbitmq
   ```

### Database connection error

1. Проверьте, что PostgreSQL запущен:
   ```bash
   docker ps | grep postgres
   ```

2. Проверьте `DATABASE_URL` в `.env`

3. Примените миграции:
   ```bash
   cd apps/<service>
   npx prisma migrate dev
   ```

### Порт уже занят

Если порт занят, измените его в `.env` или остановите процесс:

```bash
# Найти процесс на порту
lsof -i :3000

# Убить процесс
kill -9 <PID>
```

## Следующие шаги

После успешного запуска:

1. Изучите [Архитектуру системы](01-architecture.md)
2. Ознакомьтесь с [API Reference](03-api-reference.md)
3. Изучите [Events Catalog](04-events.md)
4. Прочитайте [Модели данных](05-data-models.md)
5. Изучите [Безопасность](06-security.md)

## Дополнительные ресурсы

- [NestJS Documentation](https://docs.nestjs.com)
- [Nx Documentation](https://nx.dev)
- [Prisma Documentation](https://www.prisma.io/docs)
- [RabbitMQ Documentation](https://www.rabbitmq.com/docs)
