# Лабораторная работа №12
## Тимонина Юлиана Александровна, группа 221131, вариант 19

### Задание

Предметная область: Сервис заказа такси

Повышенная сложность:
Создание полноценного веб-приложения, интеграция ИИ в CI/CD, генерация unit-тестов с высоким покрытием
---

### Структура репозитория

```
lab12/
├── .gitignore
├── app.py
├── config.py
├── decorators.py
├── models.py
├── test_app.py
├── requirements.txt
├── .github/workflows
│       └── ai-pr-review.yml
│
├── auth/
│   ├── __init__.py
│   └── routes.py
│
├── orders/
│   ├── __init__.py
│   └── routes.py
│
├── drivers/
│   ├── __init__.py
│   └── routes.py
│
├── tariffs/
│   ├── __init__.py
│   └── routes.py
│
├── reports/
│   ├── __init__.py
│   └── routes.py
│
├── geocoding/
│   ├── __init__.py
│   └── utils.py
│
├── static/
│   └── main.js
│
└── templates/
    ├── login.html
    ├── register.html
    ├── customer/
    │   └── dashboard.html
    ├── driver/
    │   └── dashboard.html
    └── admin/
        ├── dashboard.html
        ├── drivers.html
        ├── tariffs.html
        └── reports.html
```

## Запуск тестов

## Начальные данные (только для разработки и тестирования)

При первом запуске приложения в корневом файле `app.py` вызывается функция
`seed_data`, которая создаёт в базе данных учётную запись администратора и 
три стандартных тарифа.
Это сделано **исключительно для удобства ручного тестирования и демонстрации**.  
В реальном проекте подобные фикстуры следует вынести в отдельные миграции или 
скрипты инициализации, а не выполнять при каждом запуске приложения.

```bash
# Сборка и запуск
pip install -r requirements.txt
python app.py

# Открытие приложения в браузере
http://127.0.0.1:8080

# Логин админа
admin@admin.com
# Пароль админа
admin

# Запуск тестов
pytest test_app.py -v --cov=. --cov-report=term-missing

```