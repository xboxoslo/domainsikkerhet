'use strict';
/* data1.no privacy-vennlig pageview-tracker.
 * Bruker en image-pixel (GET) for å unngå Safari ITP / cross-site tracking blocking.
 * Ingen cookies. IP hashes server-side med salt.
 *
 * Kan slås av i nettleseren ved å sette window.NO_TRACK = true før dette skriptet.
 */
(function () {
  if (window.NO_TRACK) return;
  if (sessionStorage.getItem('data1-tracked-' + location.pathname)) return;

  const isLocal = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
  const ENDPOINT = isLocal ? 'http://localhost:3001/track' : 'https://web-production-1681.up.railway.app/track';

  const params = new URLSearchParams(location.search);
  const utm = {
    utm_source: params.get('utm_source') || '',
    utm_medium: params.get('utm_medium') || '',
    utm_campaign: params.get('utm_campaign') || ''
  };
  if (utm.utm_source) {
    try { sessionStorage.setItem('data1-utm', JSON.stringify(utm)); } catch {}
  }
  window.data1Utm = utm;

  const send = () => {
    try {
      const q = new URLSearchParams({
        p: location.pathname,
        r: document.referrer || '',
        s: utm.utm_source,
        m: utm.utm_medium,
        c: utm.utm_campaign,
        t: Date.now().toString(36)
      });
      const img = new Image();
      img.onload = img.onerror = () => {
        try { sessionStorage.setItem('data1-tracked-' + location.pathname, '1'); } catch {}
      };
      img.src = ENDPOINT + '?' + q.toString();
    } catch {}
  };

  if (document.readyState === 'complete') send();
  else window.addEventListener('load', send, { once: true });
})();
