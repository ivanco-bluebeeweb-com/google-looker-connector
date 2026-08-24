# Google Looker Connector — идеальный первый запуск

Источник: `ONBOARDING_FIRST_LAUNCH_STANDARD.md`. Целевой пользователь:
BI/Data аналитик или Looker админ.

## 1. Credential type
API3 Key (client_id + client_secret) + instance hostname — обменивается на
короткоживущий access_token (`POST /login`, TTL ~60 минут, без refresh
token, прозрачный повторный login при истечении).

## 2. Идеальный флоу

1. **Первое открытие** — `Empty` со ссылкой на создание API3 Key (Admin >
   Users > свой профиль > "Edit Keys", либо Admin > API Keys для
   сервисного аккаунта) и явным пояснением, что нужен именно API-порт
   (`:19999`), не обычный URL инстанса.
2. **Форма** — instance_hostname (placeholder: `mycompany.looker.com`,
   без порта — порт добавляется коннектором автоматически) + client_id +
   client_secret, все с лейблами и контекстными placeholder-ами.
3. **После успешного подключения** — сразу список Folders с числом
   Looks/Dashboards в каждой; если Folders пусты — точное объяснение "API3
   Key подключен, но у пользователя нет доступа ни к одной папке" с
   инструкцией куда идти (Admin > Roles).
4. **Health snapshot сразу после connect** — сколько Looks, сколько
   Dashboards, сколько failed Scheduled Plans за последние 24ч, сколько
   content validation errors найдено — POST_CONNECT_EXPERIENCE принцип.
5. **Истечение access_token (401 mid-session)** — токен истёк за
   отведённые ~60 минут; автоматический silent re-login на том же
   client_id/secret, а не общая ошибка 401.
6. **Ошибка client_id/secret invalid** — конкретное сообщение "API3 Key
   недействителен или отозван — создайте новый в Admin > Users > Edit
   Keys" с прямой ссылкой, не общий "Unauthorized".
7. **Content validation с ошибками** — список конкретных Looks/Dashboards
   с точным полем/явно указанной причиной (сломанная ссылка на удалённое
   LookML поле), а не просто счётчик "N errors".

## 3. Разница с реализацией сейчас
См. UI_COMPONENT_PLAN.md §0 — реализация ниже строго из существующего
словаря `imperal_sdk.ui`, без компромиссов относительно этого идеального
флоу (Looker API 4.0 уже даёт всё необходимое для шагов 1-7).
