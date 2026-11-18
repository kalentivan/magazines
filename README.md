# Истории в печати — авторские журналы

Статическая витрина B2C и `/hotels/` B2B на GitHub Pages. Существующие журналы и материалы сохранены.

**Статус:** UI реализован; локальный приём заявок протестирован. Production lead capture отключён до доступа к серверу и утверждения политики. Email — отдельный контакт, не замена подтверждённому приёму.

## Разработка и проверки

Python 3.12+ и Node 22+ для syntax check. Устанавливать npm-пакеты не нужно.

```sh
python scripts/preview.py --port 4173
python -m unittest discover -s tests -v
python scripts/check_site.py
node --check assets/site/site.js
```

Для **синтетических** заявок локально: `python scripts/preview.py --port 4173 --test-leads`. Тестовая БД находится в системном temp, вне static root. Публичный `assets/site/config.js` от этого не меняется. После завершения тестирования не используйте этот сервер для клиентов.

## Публикация frontend

GitHub Pages из main / root; сохраняется текущий способ публикации. Перед merge — CI Site checks, preview и проверка diff. `backend`, `docs`, `scripts`, `tests` исключены из Jekyll, но исходный код открыто хранится в GitHub. В нём **никогда** не должно быть БД, контактов лидов, токенов или .env.

Rollback: обычный `git revert <release-commit>` в main и новая публикация Pages; force-push не нужен. Отключение приёма: endpoint='' и privacyApproved=false в config.js, затем остановить API при необходимости.

## API и приватное хранилище

`POST /leads`: JSON name, contact, lead_type=b2c|b2b, consent=true, request_id UUID; B2B требует company/message; необязательны message, occasion_date, quantity; website — honeypot. Ответ 201 `{saved:true,lead_id}` только после commit. 422 validation, 403 origin, 409 ID conflict, 429 limit, 503 storage. GET /health, других публичных GET нет.

На согласованном сервере:

1. Скопировать backend/.env.example в backend/.env, сгенерировать RATE_SECRET (`python -c "import secrets; print(secrets.token_hex(32))"`), задать CONSENT_VERSION после утверждения текста и LEADS_ENABLED=true.
2. `cd backend && docker compose up -d --build`. Контейнер непривилегированный; порт 8080 опубликован только на loopback, БД на отдельном volume.
3. Настроить TLS reverse proxy по Caddyfile.example, домен и firewall. Не открывать SQLite через HTTP. Ограничить запросы на edge; пример API — для небольшого потока, не для публичного высоконагруженного сервиса.
4. Утвердить и опубликовать privacy, реквизиты оператора, сроки хранения/удаления, место хранения. Обновить consent version.
5. В config.js указать HTTPS `/leads` и privacyApproved=true **после** тестов реального deployment.
6. Отправить синтетические B2C/B2B заявки с production origin; найти их через manage.py; проверить уведомления, backup и восстановление. Только затем объявлять приём готовым.

GitHub Pages бесплатен в рамках доступного аккаунта; Python/SQLite не требуют подписки. Сервер, домен и инфраструктура владельцем не выбраны — их стоимость не предполагается нулевой.

## Обработка менеджером

Только через доступ к приватному серверу:

```sh
docker compose exec leads python manage.py --db /data/leads.sqlite3 list
docker compose exec leads python manage.py --db /data/leads.sqlite3 show LEAD_ID
docker compose exec leads python manage.py --db /data/leads.sqlite3 handled LEAD_ID
```

`show` выводит PII: не копировать вывод в публичный GitHub. Назначить ответственного и регулярный просмотр статуса new. Для уведомлений настроить секретные NOTIFY_WEBHOOK/NOTIFY_TOKEN на сервере и запускать `python notify.py` по расписанию. Webhook получает ID/тип; контакт и текст остаются в БД. Сбой оставляет запись pending, повтор с Idempotency-Key; получатель должен уметь дедуплицировать. Канал/расписание пока не подключены.

Backup: `manage.py --db /data/leads.sqlite3 backup /data/backup.sqlite3`, затем копировать в согласованное приватное зашифрованное хранилище. Проверять восстановление отдельным файлом. Retention и удаление из backup согласовать с владельцем. Удаление конкретной заявки: `manage.py --db /data/leads.sqlite3 delete LEAD_ID` — только после проверки запроса и полномочий. Backup и .env никогда не класть в repository/static directory.

## Документы

- docs/audit.md — baseline и маршруты
- docs/research/ — 6 конкурентов, гипотезы, интервью
- docs/ux.md, docs/design.md — сценарии и визуальная система
- docs/decisions.md — принятые решения и ограничения
- docs/qa.md, docs/progress.md — проверки и статус
- docs/metrics.md — приоритеты следующего этапа

robots.txt в project Pages не заменяет host-root robots.txt; sitemap доступен по /magazines/sitemap.xml. Старую policy/ABIE не использовать для журналов.
