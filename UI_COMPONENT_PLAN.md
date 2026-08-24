# Google Looker Connector — UI component plan

Источники: `Docs/session-notes/UI_COMPONENT_VOCABULARY.md`, `UI_INTERFACE_STANDARD.md`,
`concepts/panels.md`. Основано на функционале `google-looker-connector`.

## 0. Разница с IDEAL_ONBOARDING.md

Реализация ниже строго из существующего словаря `imperal_sdk.ui`. Единственный
компромисс — health snapshot после connect считается синхронно в первом
рендере sidebar (без фонового job), поэтому первый рендер может занять на
1-2 секунды больше при большом количестве Folders/Looks.

## 1. Компоненты

| Экран | Примитивы | Почему именно эти |
|---|---|---|
| Sidebar (left) | `ui.Stack`(v, align="stretch") + connect `ui.Form`(instance_hostname/client_id/client_secret, все с лейблами и контекстными placeholder) + `ui.Divider` + Folders список (`ui.Stack` v, без карточек) + `ui.Button`("App settings") | Без карточек по стандарту, форма растянута на всю ширину сайдбара. |
| Folder content (center, `center_overlay=True`) | `ui.Tabs`(Looks/Dashboards) + `ui.DataTable`(title, updated_at) в каждой вкладке | Табы — тот же паттерн, что у Power BI Workspace content, для переключения 2 типов контента одной папки. |
| Look Detail | Back-button + `ui.KeyValue`(model/explore/last_run) + `ui.Button`("Run now") → `ui.DataTable`(результат запроса как таблица) | Результат запроса Looker естественно табличный. |
| Dashboard Detail | Back-button + `ui.List`(dashboard elements: title, type) | Простой перечень элементов дашборда. |
| Scheduled Plans | `ui.DataTable`(name, look/dashboard, cron, last_run_status Badge) + `ui.Button`("Run once") | Табличный список с ручным запуском — тот же паттерн, что Extract Refresh Tableau/Reload Task Qlik. |
| Content Validation | `ui.DataTable`(content_type, title, error_message) | Единственный способ явно показать конкретные сломанные ссылки, а не просто счётчик. |
| Users | `ui.DataTable`(name, email, role) | Табличный список — стандартный паттерн admin-списков в портфеле. |
| App settings (center, `center_overlay=True`) | Connections список + Disconnect-кнопки + Health snapshot (`ui.Stats`) | Единственное место с Disconnect и агрегированной статистикой — не дублируется в сайдбаре. |
| Connect-help (modal) | `ui.Modal` с пошаговой инструкцией создания API3 Key | Вся инструкция живёт ТОЛЬКО здесь, не дублируется в сайдбаре. |

## 2. Формы — обязательные правила

Все `ui.Input` внутри `ui.Form` обёрнуты в `ui.Text`(caption) как лейбл;
placeholder контекстно подходящий под конкретное поле (не generic "Enter
value"). Контейнер формы (`ui.Stack` вокруг `ui.Form`) растянут на всю
ширину левого сайдбара (`align="stretch"`), содержимое формы растянуто
внутри него самого.
