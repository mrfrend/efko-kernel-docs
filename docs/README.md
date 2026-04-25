# EFKO Kernel - Документация

Полная техническая документация системы EFKO Kernel для разработчиков и ИИ-агентов.

## О системе

EFKO Kernel — Nx-монорепозиторий с микросервисной архитектурой на NestJS. Система состоит из 5 доменных сервисов, которые общаются через RabbitMQ, и 3 общих библиотек.

**Сервисы:**
- `gateway` — публичный HTTP API Gateway
- `auth-service` — аутентификация и управление пользователями
- `personnel` — кадровый домен (подразделения, должности, сотрудники, смены)
- `production` — производственный домен (продукты, заказы, выпуск, качество, датчики)
- `etl` — интеграция с внешними системами (ZUP, ERP, MES, SCADA, LIMS)

**Библиотеки:**
- `contracts` — типизированные контракты для RabbitMQ (commands, queries, events)
- `interfaces` — общие TypeScript интерфейсы и enum-ы
- `nest-utils` — инфраструктурные утилиты (logging, metrics, tracing, auth guards)

## Навигация по документации

### Начало работы
- [**Архитектура системы**](01-architecture.md) — обзор архитектуры, коммуникация между сервисами, паттерны
- [**Quick Start**](02-quickstart.md) — пошаговое руководство для быстрого старта разработки

### API Reference
- [**API Reference**](03-api-reference.md) — полный справочник по REST API с примерами запросов/ответов
  - Auth API (регистрация, логин, refresh, пользователи)
  - Personnel API (подразделения, должности, сотрудники, смены)
  - Production API (продукты, заказы, выпуск, продажи, качество, датчики, KPI)
  - ETL API (импорт данных из внешних систем)

### События
- [**Events Catalog**](04-events.md) — полный каталог всех доменных событий в системе
  - Auth события
  - Personnel события
  - Production события
  - ETL события

### Данные
- [**Модели данных**](05-data-models.md) — Prisma схемы всех сервисов
  - Auth Service (User, RefreshToken)
  - Personnel Service (Department, Position, Employee, ShiftScheduleTemplate)
  - Production Service (Product, ProductionOrder, ProductionOutput, Sale, Inventory, QualityResult, SensorReading)

### Безопасность и эксплуатация
- [**Безопасность**](06-security.md) — аутентификация, авторизация, CSRF защита, key rotation
- [**Troubleshooting**](07-troubleshooting.md) — диагностика проблем, логирование, health checks

### Для клиентов
- [**Client Guide**](08-client-guide.md) — руководство по интеграции для веб и мобильных клиентов
  - Аутентификация для браузерных клиентов (cookies + CSRF)
  - Аутентификация для мобильных клиентов (токены в памяти)
  - Примеры запросов

## Технологии

- **Фреймворк:** NestJS
- **Монорепозиторий:** Nx
- **Брокер сообщений:** RabbitMQ (@golevelup/nestjs-rabbitmq)
- **Базы данных:**
  - PostgreSQL (Prisma) — auth, personnel, production
  - MongoDB (Mongoose) — etl
- **Логирование:** nestjs-pino + Loki
- **Трассировка:** OpenTelemetry
- **Метрики:** Prometheus
- **API документация:** Swagger/OpenAPI

## Ключевые паттерны

- **CQRS** — разделение команд (write) и запросов (read)
- **Transactional Outbox** — надежная публикация событий
- **Event-Driven Architecture** — асинхронная коммуникация через события
- **Contracts-First** — типизированные контракты в общей библиотеке

## Целевая аудитория

Документация предназначена для:
- Разработчиков команды (внутренняя разработка)
- DevOps инженеров (деплой, мониторинг, эксплуатация)
- Веб-разработчиков клиентов (интеграция через REST API)
- Мобильных разработчиков клиентов (интеграция через REST API)
- ИИ-агентов (автоматизация и генерация кода)

## Дополнительные материалы

- **Swagger UI:** `GET /api/swagger` (при запущенном gateway)
- **Swagger JSON:** `GET /api/swagger/json`
- **CLAUDE.md** — руководство для Claude Code
- **.env.example** — пример конфигурации окружения

## Поддержка

При возникновении вопросов или проблем:
1. Обратитесь к [Troubleshooting](07-troubleshooting.md)
2. Проверьте логи в папке `logs/`
3. Используйте Loki для агрегированного логирования (если настроено)
