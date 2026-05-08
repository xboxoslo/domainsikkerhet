'use strict';
/* data1.no privacy-vennlig pageview-tracker.
 * Sender én POST per sidevisning til intake-serverens /track endpoint.
 * Ingen cookies. IP hashes server-side med salt.
 *
 * Kan slås av i nettleseren ved å sette window.NO_TRACK = true før dette skriptet.
 */
(function () {
  if (window.NO_TRACK) return;
  if (navigator.doNotTrack === '1' || navigator.doNotTrack === 'yes') return;
  if (sessionStorage.getItem('data1-tracked-' + location.pathname)) return;

  const isLocal = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
  const ENDPOINT = isLocal ? 'http://localhost:3001/track' : 'https://web-production-1681.up.railway.app/track';

  const params = new URLSearchParams(location.search);
  const utm = {
    utm_source: params.get('utm_source') || '',
    utm_medium: params.get('utm_medium') || '',
    utm_campaign: params.get('utm_campaign') || ''
  };
  // Persist UTM in sessionStorage so the intake form (other page or later)
  // can attach it to the conversion event.
  if (utm.utm_source) {
    try { sessionStorage.setItem('data1-utm', JSON.stringify(utm)); } catch {}
  }
  window.data1Utm = utm;
  const payload = {
    path: location.pathname,
    referrer: document.referrer || '',
    ...utm
  };

  const send = () => {
    try {
      const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });
      if (navigator.sendBeacon && navigator.sendBeacon(ENDPOINT, blob)) {
        sessionStorage.setItem('data1-tracked-' + location.pathname, '1');
        return;
      }
      fetch(ENDPOINT, { method: 'POST', body: JSON.stringify(payload), headers: { 'Content-Type': 'application/json' }, keepalive: true })
        .then(() => sessionStorage.setItem('data1-tracked-' + location.pathname, '1'))
        .catch(() => {});
    } catch {}
  };

  if (document.readyState === 'complete') send();
  else window.addEventListener('load', send, { once: true });
})();
