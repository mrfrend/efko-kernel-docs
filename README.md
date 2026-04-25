# EFKO Kernel Documentation

Статический сайт документации для проекта EFKO Kernel, построенный на MkDocs с темой Material.

## Установка

```bash
# Создание виртуального окружения
python3 -m venv .venv

# Активация окружения
source .venv/bin/activate  # Linux/macOS
# или
.venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt
```

## Разработка

```bash
# Запуск dev сервера
mkdocs serve

# Сборка статического сайта
mkdocs build
```

## Структура проекта

```
efko-kernel-docs/
├── docs/              # Копия документации из efko-kernel
├── mkdocs.yml         # Конфигурация MkDocs
├── scripts/           # Скрипты для копирования файлов
├── .github/           # GitHub Actions workflows
└── requirements.txt   # Python зависимости
```

## Копирование документации

Перед сборкой документация автоматически копируется из проекта `efko-kernel`:

```bash
./scripts/copy-docs.sh
```

Этот скрипт копирует все файлы из `/home/ivan/projects/efko-kernel/docs/` в `docs/`.

## CI/CD

Автоматический деплой на GitHub Pages настроен через GitHub Actions. При каждом push в ветку `main`:

1. Копируется документация из efko-kernel
2. Собирается статический сайт
3. Деплоится на GitHub Pages

## Доступ к документации

- **Dev сервер:** http://127.0.0.1:8000 (при `mkdocs serve`)
- **GitHub Pages:** https://mrfrend.github.io/efko-kernel-docs/
