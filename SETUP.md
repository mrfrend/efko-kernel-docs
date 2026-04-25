# Настройка GitHub репозитория и GitHub Pages

## Шаг 1: Создание репозитория на GitHub

1. Перейдите на https://github.com/new
2. Создайте новый репозиторий с именем `efko-kernel-docs`
3. Сделайте репозиторий публичным (public)
4. Не инициализируйте README, .gitignore или LICENSE (они уже есть)

## Шаг 2: Пуш локального репозитория на GitHub

```bash
cd /home/ivan/projects/efko-kernel-docs

# Добавьте remote (замените на ваш GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/efko-kernel-docs.git

# Пушните код
git push -u origin main
```

## Шаг 3: Настройка GitHub Pages

1. Перейдите в репозиторий на GitHub
2. Зайдите в **Settings** → **Pages**
3. В разделе **Build and deployment**:
   - **Source**: GitHub Actions
4. GitHub Actions автоматически настроится из файла `.github/workflows/deploy.yml`

## Шаг 4: Проверка деплоя

После пуша в ветку `main`:
1. Перейдите в раздел **Actions** в репозитории
2. Вы увидите workflow "Deploy Documentation"
3. После успешного завершения документация будет доступна по адресу:
   - `https://YOUR_USERNAME.github.io/efko-kernel-docs/`

## Шаг 5: Настройка GitHub Pages в mkdocs.yml

Отредактируйте `mkdocs.yml` и замените:
```yaml
site_url: https://mrfrend.github.io/efko-kernel-docs/
repo_url: https://github.com/mrfrend/efko-kernel-docs
repo_name: mrfrend/efko-kernel-docs
```

На ваши данные:
```yaml
site_url: https://YOUR_USERNAME.github.io/efko-kernel-docs/
repo_url: https://github.com/YOUR_USERNAME/efko-kernel-docs
repo_name: YOUR_USERNAME/efko-kernel-docs
```

## Локальная разработка

```bash
# Копирование документации из efko-kernel
./scripts/copy-docs.sh

# Запуск dev сервера
.venv/bin/mkdocs serve

# Сборка статического сайта
.venv/bin/mkdocs build
```

## Автоматическое обновление документации

### Вариант 1: Ручное обновление

При изменении документации в `efko-kernel`:
1. Выполните `./scripts/copy-docs.sh`
2. Закоммитьте и запушьте изменения
3. GitHub Actions автоматически соберет и задеплоит документацию

### Вариант 2: Автоматическое обновление через repository_dispatch

При изменении документации в `efko-kernel` (папка `docs/`):
1. Закоммитьте и запушьте изменения в ветку `main`
2. GitHub Actions workflow `update_docs` автоматически отправит событие в `efko-kernel-docs`
3. GitHub Actions workflow `deploy` в `efko-kernel-docs` автоматически соберет и задеплоит документацию

Для работы автоматического обновления необходимо настроить секрет `DOCS_DEPLOY_PAT` в репозитории `efko-kernel` (см. инструкции выше).

## Примечание

Скрипт `copy-docs.sh` жестко задан на `/home/ivan/projects/efko-kernel/docs`. Если путь изменится, отредактируйте скрипт.

## Требования

### Секреты в efko-kernel-docs

- Репозиторий `efko-kernel` приватный, поэтому требуется Personal Access Token
- Создайте Personal Access Token с правами `repo` (read access)
- Добавьте токен как secret `EFKO_KERNEL_ACCESS` в Settings → Secrets and variables → Actions репозитория `efko-kernel-docs`

### Секреты в efko-kernel

- Для автоматического деплоя при изменении документации в efko-kernel требуется Personal Access Token
- Создайте Personal Access Token с правами `repo` (write access для repository dispatch)
- Добавьте токен как secret `DOCS_DEPLOY_PAT` в Settings → Secrets and variables → Actions репозитория `efko-kernel`

### Создание Personal Access Token для efko-kernel-docs

1. Перейдите на https://github.com/settings/tokens
2. Нажмите "Generate new token (classic)"
3. Назовите токен (например, "efko-kernel-docs")
4. Выберите права: `repo` (read access)
5. Сгенерируйте токен и скопируйте его
6. Перейдите в репозиторий `efko-kernel-docs` → Settings → Secrets and variables → Actions
7. Нажмите "New repository secret"
8. Name: `EFKO_KERNEL_ACCESS`
9. Value: вставьте сгенерированный токен
10. Нажмите "Add secret"

### Создание Personal Access Token для efko-kernel

1. Перейдите на https://github.com/settings/tokens
2. Нажмите "Generate new token (classic)"
3. Назовите токен (например, "docs-deploy-pat")
4. Выберите права: `repo` (write access для repository dispatch)
5. Сгенерируйте токен и скопируйте его
6. Перейдите в репозиторий `efko-kernel` → Settings → Secrets and variables → Actions
7. Нажмите "New repository secret"
8. Name: `DOCS_DEPLOY_PAT`
9. Value: вставьте сгенерированный токен
10. Нажмите "Add secret"
