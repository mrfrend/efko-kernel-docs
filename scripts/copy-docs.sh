#!/bin/bash

# Скрипт для копирования документации из efko-kernel
# Использование: ./scripts/copy-docs.sh

SOURCE_DIR="/home/ivan/projects/efko-kernel/docs"
DEST_DIR="docs"

echo "Копирование документации из $SOURCE_DIR в $DEST_DIR..."

# Очистка папки docs перед копированием
if [ -d "$DEST_DIR" ]; then
  rm -rf "$DEST_DIR"
fi

# Создание папки docs
mkdir -p "$DEST_DIR"

# Копирование всех файлов и папок
cp -r "$SOURCE_DIR"/* "$DEST_DIR/"

echo "Документация скопирована успешно!"
echo "Файлы в docs/:"
ls -la "$DEST_DIR"
