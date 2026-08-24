# Google Looker Connector — Preparation

## 1. Паспорт приложения

- **Название:** Google Looker Connector
- **Короткое описание:** Управление Looks, Dashboards, Explores и
  Scheduled Plans Google Looker прямо из Imperal — запуск расписаний,
  ad-hoc запросы к Explore и проверка целостности контента.
- **Владелец продукта:** vlad@bluebeeweb.com
- **Дата подготовки:** 2026-08-24
- **Почему сейчас:** BI/Аналитика — новая категория портфеля (см.
  `Docs/session-notes/NEXT_12_CATEGORIES_RESEARCH.md` §5); Looker —
  собственный BI-продукт Google Cloud, LookML-семантический слой
  разнообразит портфель альтернативой Power BI/Tableau/Qlik.
- **Scope:** максимальный функционал в рамках Looker API 4.0 (LookML Git
  project management и embed SSO явно вне scope v1, см.
  CONNECTOR_DISCOVERY.md §5).

## 2. Проблема в человеческих словах

Когда **BI/Data аналитик или Looker админ** сталкивается с
**необходимостью проверить упавший Scheduled Plan, найти Look/Dashboard со
сломанной ссылкой на удалённое поле или быстро прогнать ad-hoc запрос к
Explore**, ей приходится **открывать отдельный веб-интерфейс Looker,
искать нужный content вручную по папкам и ждать, пока кто-то пожалуется на
битый дашборд**, из-за чего возникает **задержка в обнаружении проблем с
данными и отсутствие единого места мониторинга Looker рядом с остальными
операционными системами компании**.

## 3. Пользователи и роли

- **BI/Data аналитик** — строит Looks/Explores-запросы, следит за
  Scheduled Plans, чинит упавшие расписания.
- **Looker админ** — управляет пользователями/папками, следит за
  целостностью контента (content validation).
- **Руководитель/консьюмер дашбордов** — не имеет прямого доступа к
  приложению, выигрывает от свежих и корректных данных.

## 4. Credential type и авторизация

API3 Key (client_id + client_secret) + instance hostname — обменивается на
короткоживущий access_token через `/login` (TTL ~60 минут), без refresh
token; прозрачный повторный login при истечении (см.
CONNECTOR_DISCOVERY.md §3).

## 5. Ярус функционала (максимум в рамках API)

**Ярус 1 (v1, всё что даёт REST API):**
connect/disconnect/list_connections, list_folders, list_looks,
get_look, run_look, list_dashboards, get_dashboard, list_lookml_models,
get_explore, run_query, list_scheduled_plans, get_scheduled_plan,
run_scheduled_plan_once, list_users, run_content_validation,
audit_instance_health.

**Ярус 2/3 (вне scope v1):** LookML Git project management, embed SSO URL
generation, custom visualization config editing (см. CONNECTOR_DISCOVERY.md
§5 для полного обоснования).

## 6. Связь с существующим портфелем

Четвёртый BI-коннектор в категории (после Power BI, Tableau, Qlik) — все
четыре покрывают разные модели авторизации (delegated OAuth2/Azure AD,
session PAT, static API key, static API3 key+login) и разные модели
организации контента (Workspaces, Sites/Projects, Spaces, Folders), что
даёт живую вариативность для UI_COMPONENT_VOCABULARY.md паттернов.
