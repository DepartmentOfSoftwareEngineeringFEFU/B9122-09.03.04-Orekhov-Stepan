# Инструкция по развёртыванию

## Назначение

Проект `evacuation_simulator` является учебно-исследовательским прототипом для моделирования эвакуации людей из помещений. Программа реализована на Python и использует PyQt6, NumPy, Matplotlib, SQLite, JSON и python-docx.

## Требования

- Windows 10/11.
- Python 3.10 или новее.
- Распакованная папка с проектом.

## Структура перед запуском

Корень папки должен иметь примерно такой вид:

```text
./
  evacuation_simulator/
  photo/
  DEPLOYMENT.md
  screenshots.docx
```

Все команды ниже выполняются из корня этой папки, где лежит каталог `evacuation_simulator`.

## Установка

Создайте виртуальное окружение:

```powershell
python -m venv .venv
```

Активируйте его:

```powershell
./.venv/Scripts/Activate.ps1
```

Установите зависимости:

```powershell
pip install -r ./evacuation_simulator/requirements.txt
```

## Запуск приложения

Перейдите в папку приложения:

```powershell
cd ./evacuation_simulator
```

Запустите программу:

```powershell
python main.py
```

Альтернативно из корня проекта можно запустить так:

```powershell
python ./evacuation_simulator/main.py
```

## Запуск тестов

```powershell
cd ./evacuation_simulator
python -m pytest
```

## Локальное хранилище

SQLite-база данных создаётся автоматически:

```text
./data/evacuation.db
```

Файл базы не нужно создавать вручную. При первом запуске программа сама создаст папку `data` и файл `evacuation.db`.

## Демонстрационные сценарии

Готовые JSON-сценарии находятся в папке:

```text
./evacuation_simulator/examples
```

## Формирование отчётов

После завершения моделирования в интерфейсе выберите:

- `Сформировать DOCX`;
- `Сформировать CSV`.

По умолчанию сформированные файлы можно сохранять в папку:

```text
./evacuation_simulator/reports
```

## Скриншоты

PNG-файлы со скриншотами лежат в папке:

```text
./photo
```

Отдельный Word-файл со скриншотами:

```text
./screenshots.docx
```

## Ограничения

Программа является учебно-исследовательским прототипом и не заменяет сертифицированные расчётные комплексы пожарного риска.
