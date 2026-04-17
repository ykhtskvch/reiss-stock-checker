# 👗 Reiss Stock Checker

Автоматически проверяет наличие **Valencia dress** (Ivory/Black, размер 12) на Reiss и шлёт уведомление в Telegram, как только размер появится в продаже.

Запускается **каждые 2 часа** бесплатно через GitHub Actions.

---

## Быстрый старт

### 1. Создай Telegram-бота

1. Напиши [@BotFather](https://t.me/BotFather) в Telegram → `/newbot`
2. Придумай имя боту → получи **токен** вида `123456:ABC-DEF...`

### 2. Узнай свой Chat ID

1. Напиши что-нибудь своему новому боту
2. Открой в браузере:
   ```
   https://api.telegram.org/bot<ВАШ_ТОКЕН>/getUpdates
   ```
3. Найди в ответе `"chat":{"id": XXXXXXX}` — это твой **Chat ID**

### 3. Загрузи файлы на GitHub

```bash
git init reiss-stock-checker
cd reiss-stock-checker

# Скопируй сюда check_stock.py и папку .github/
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/ВАШ_ЛОГИН/reiss-stock-checker.git
git push -u origin main
```

### 4. Добавь секреты в репозиторий

В GitHub: **Settings → Secrets and variables → Actions → New repository secret**

| Имя секрета          | Значение                       |
|----------------------|--------------------------------|
| `TELEGRAM_BOT_TOKEN` | Токен от BotFather             |
| `TELEGRAM_CHAT_ID`   | Твой числовой Chat ID          |

### 5. Проверь вручную

**Actions → Reiss Stock Checker → Run workflow** — убедись что скрипт запускается без ошибок.

---

## Структура файлов

```
reiss-stock-checker/
├── check_stock.py                  # Основной скрипт
└── .github/
    └── workflows/
        └── stock_check.yml         # Расписание GitHub Actions
```

---

## Как это работает

1. GitHub Actions запускает скрипт каждые 2 часа
2. Скрипт обращается к API/странице Reiss и проверяет наличие размера 12
3. Если размер доступен — отправляет сообщение в Telegram с ссылкой на покупку
4. Если нет — тихо завершается (без уведомления)

---

## Изменить частоту проверки

В файле `.github/workflows/stock_check.yml` измени строку cron:

```yaml
- cron: "0 */1 * * *"   # каждый час
- cron: "*/30 * * * *"  # каждые 30 минут
```

> ⚠️ GitHub Actions бесплатно даёт 2000 минут/месяц.  
> При проверке каждые 2 часа = ~360 запусков/месяц ≈ 360 минут — в пределах лимита.
