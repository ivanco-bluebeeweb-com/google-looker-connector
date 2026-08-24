# Google Looker Connector — Discovery

**Статус:** discovery завершён, готов к PREPARATION.md
**Источники:** cloud.google.com/looker/docs/reference/looker-api/latest
(Looker API 4.0 reference), cloud.google.com/looker/docs/api-auth
(client_id/client_secret → access token).

## 1. Что за продукт

Looker (Google Cloud) — BI-платформа на семантическом слое LookML: модели
описываются кодом (Git-репозиторий), поверх них строятся **Explores**
(интерактивные исследования данных), **Looks** (сохранённые единичные
запросы/визуализации) и **Dashboards** (набор Looks/визуализаций на одной
странице). Существует как Looker (Google Cloud core) — managed instance
`https://<instance>.looker.com` — так и Looker Studio (бывший Data Studio,
ОТДЕЛЬНЫЙ бесплатный продукт с другим API/моделью) — вне scope этого
коннектора.

## 2. API-поверхность

REST API: `https://<instance>.looker.com:19999/api/4.0/*` (порт 19999 —
Looker API port, отдельный от порта UI 443/9999).

- **Auth** — `POST /api/4.0/login` с `client_id`+`client_secret` (form-data)
  → `access_token` (Bearer, TTL по умолчанию 60 минут) + `expires_in`. Нет
  refresh token — по истечении просто логинимся заново тем же
  client_id/secret (аналогично Tableau по духу, но ещё проще: не нужен
  site/session, только повторный login).
- **Looks** (`/looks`) — сохранённые запросы с визуализацией; можно
  получить рендер (`/looks/{id}/run/{format}` — json/csv/png/xlsx).
- **Dashboards** (`/dashboards`) — набор dashboard elements (обычно =
  Looks), можно получить полный dashboard со всеми элементами.
- **LookML Models / Explores** (`/lookml_models`, `.../explores/{name}`) —
  метаданные семантического слоя: какие поля/меры доступны для построения
  запроса.
- **Queries** (`/queries`, `/queries/run/{format}`) — построить и выполнить
  ad-hoc запрос против Explore напрямую (без сохранения как Look).
- **Scheduled Plans** (`/scheduled_plans`) — расписания доставки
  Look/Dashboard (email/Slack/webhook на cron); можно вручную
  `run_once` — тот же async job-паттерн, что extract refresh/reload task у
  Tableau/Qlik, но здесь синхронный запуск (job создаётся и сразу
  выполняется, без отдельного poll endpoint в большинстве случаев —
  `scheduled_plan_run_once` возвращает результат немедленно).
- **Folders/Spaces** (`/folders`) — иерархия папок, в которых лежат
  Looks/Dashboards (аналог Projects у Tableau/Spaces у Qlik).
- **Users** (`/users`) — пользователи инстанса, роли.
- **Content validation** (`/content_validation`) — встроенная проверка
  битых ссылок/полей в Looks/Dashboards (уникальная фича Looker, нет
  прямого аналога у Tableau/Qlik/Power BI — хороший кандидат для
  audit_instance_health).

## 3. Авторизация

**API3 Key** (client_id + client_secret) — создаётся в Admin > Users >
редактирование пользователя > "Edit Keys" (или через Admin > API Keys для
сервисного аккаунта). Обменивается на короткоживущий access_token через
`/login`; при истечении просто повторяем login — прозрачно для
пользователя коннектора.

## 4. Реальные пользовательские сценарии

1. BI/Data аналитик утром проверяет: какие Scheduled Plans упали ночью, и
   перезапускает конкретный вручную.
2. Админ ищет Look/Dashboard с битой ссылкой на удалённое поле — раньше
   находил случайно через жалобу пользователя, теперь запускает
   content_validation и видит список сразу.
3. Аналитик хочет быстро прогнать ad-hoc запрос против Explore без захода
   в Looker UI (например, чтобы вставить цифру в чат/отчёт).

## 5. Ярус функционала (максимум в рамках API v1)

**Ярус 1 (v1, всё что даёт REST API без доп. инфраструктуры):**
connect/disconnect/list_connections, list_folders, list_looks,
get_look+run_look (рендер данных), list_dashboards, get_dashboard,
list_lookml_models, get_explore (метаданные полей), run_query (ad-hoc),
list_scheduled_plans, get_scheduled_plan, run_scheduled_plan_once,
list_users, run_content_validation, audit_instance_health.

**Ярус 2/3 (не в v1):** LookML Git project management (создание/пуш
кода моделей — требует Git credentials отдельно от API3 key), embed SSO
URL generation (для встраивания дашбордов в сторонние сайты — сложная
подпись запроса), custom visualization config editing.
