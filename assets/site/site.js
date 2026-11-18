(() => {
  'use strict';
  const config = window.MAGAZINES_CONFIG || {};
  const events = new Set(['view_example', 'cta_click', 'form_start', 'lead_submit_success', 'lead_submit_error', 'hotel_cta_click']);
  // Local event interface only. No network, cookies, contact values or page query strings.
  const track = name => { if (events.has(name)) window.dispatchEvent(new CustomEvent('magazines:event', {detail: {name, page: document.body.classList.contains('hotel-page') ? 'hotels' : 'home'}})); };
  document.querySelectorAll('[data-event]').forEach(a => a.addEventListener('click', () => track(a.dataset.event)));
  const toggle = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.nav');
  toggle?.addEventListener('click', () => { const open = toggle.getAttribute('aria-expanded') !== 'true'; toggle.setAttribute('aria-expanded', String(open)); nav.classList.toggle('open', open); });
  nav?.addEventListener('click', e => { if (e.target.closest('a')) { nav.classList.remove('open'); toggle.setAttribute('aria-expanded', 'false'); } });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && nav?.classList.contains('open')) { nav.classList.remove('open'); toggle.setAttribute('aria-expanded', 'false'); toggle.focus(); } });
  const form = document.querySelector('form[data-lead-type]');
  if (!form) return;
  const status = form.querySelector('.form-status'), button = form.querySelector('button[type=submit]');
  let enabled = false;
  try { const endpoint = new URL(config.endpoint); enabled = config.privacyApproved === true && (endpoint.protocol === 'https:' || (endpoint.protocol === 'http:' && ['localhost','127.0.0.1'].includes(endpoint.hostname) && ['localhost','127.0.0.1'].includes(location.hostname))); } catch (_) {}
  if (!enabled) return;
  form.querySelector('fieldset').disabled = false;
  document.getElementById('availability').textContent = 'После сохранения заявки вы увидите её номер. Мы свяжемся с вами по указанному контакту.';
  let started = false, busy = false, requestId = null, previousPayload = null;
  const contact = form.elements.contact;
  contact.addEventListener('input', () => contact.setCustomValidity(''));
  form.addEventListener('focusin', () => { if (!started) { track('form_start'); started = true; } });
  form.addEventListener('submit', async e => {
    e.preventDefault();
    if (busy) return;
    const value = contact.value.trim();
    const validContact = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) || (/^[+\d\s().-]+$/.test(value) && value.replace(/\D/g,'').length >= 10 && value.replace(/\D/g,'').length <= 15);
    contact.setCustomValidity(validContact ? '' : 'Укажите корректную почту или телефон с кодом страны.');
    if (!form.reportValidity()) return;
    const payload = Object.fromEntries(new FormData(form));
    payload.lead_type = form.dataset.leadType; payload.consent = form.elements.consent.checked;
    const serialized = JSON.stringify(payload);
    if (serialized !== previousPayload) { requestId = crypto.randomUUID(); previousPayload = serialized; }
    payload.request_id = requestId;
    busy = true; button.disabled = true; form.setAttribute('aria-busy','true');
    status.className = 'form-status full'; status.textContent = 'Сохраняем заявку…';
    const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(config.endpoint, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:controller.signal,credentials:'omit',redirect:'error'});
      const result = await response.json();
      if (!response.ok || result.saved !== true || !result.lead_id) throw new Error(response.status === 429 ? 'rate' : 'save');
      status.classList.add('success'); status.textContent = `Заявка сохранена. Номер: ${result.lead_id}. Мы свяжемся с вами по указанному контакту.`;
      track('lead_submit_success'); form.reset(); requestId = null; previousPayload = null;
    } catch (error) {
      status.classList.add('error'); status.textContent = error.message === 'rate' ? 'Слишком много попыток. Подождите несколько минут и попробуйте снова.' : 'Не удалось подтвердить сохранение. Данные остались в форме. Повторите отправку или свяжитесь по почте. Повторная отправка той же заявки не создаст дубль.';
      track('lead_submit_error');
    } finally { clearTimeout(timer); busy = false; button.disabled = false; form.removeAttribute('aria-busy'); status.focus(); }
  });
})();
