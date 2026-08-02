/* =========================================================
   Officina della Narrazione — modulo di iscrizione al kit
   ========================================================= */

/* ---------------------------------------------------------
   CONFIGURAZIONE — l'unica cosa da modificare.

   Incollare qui l'URL del modulo MailerLite:
   MailerLite → Forms → Embedded forms → crea il modulo →
   scheda "HTML" → copiare l'indirizzo dentro action="..."
   (ha questa forma: https://assets.mailerlite.com/jsonp/XXXXX/forms/YYYYY/subscribe)

   Finché resta vuoto, il modulo avvisa che le iscrizioni
   non sono ancora attive invece di fingere di funzionare.
   --------------------------------------------------------- */
var MAILERLITE_ENDPOINT = '';

(function () {
  'use strict';

  var form    = document.getElementById('kit-form');
  if (!form) return;

  var email   = document.getElementById('kit-email');
  var consent = document.getElementById('kit-consent');
  var submit  = document.getElementById('kit-submit');
  var msg     = document.getElementById('kit-msg');

  function show(text) {
    msg.textContent = text;
    msg.hidden = false;
  }

  // Da quale libro arriva l'iscritto: /kit?da=dialoghi
  function origine() {
    try {
      var v = new URLSearchParams(window.location.search).get('da') || '';
      return v.replace(/[^a-zA-Z0-9_-]/g, '').slice(0, 40);
    } catch (e) { return ''; }
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();

    if (!email.value || !email.checkValidity()) {
      show('Controlla l’indirizzo email: sembra incompleto.');
      email.focus();
      return;
    }
    if (!consent.checked) {
      show('Per ricevere il kit serve il consenso al trattamento dei dati.');
      consent.focus();
      return;
    }

    if (!MAILERLITE_ENDPOINT) {
      show('Le iscrizioni aprono a breve. Torna tra qualche giorno: il kit sarà pronto al download.');
      return;
    }

    submit.disabled = true;
    var originale = submit.textContent;
    submit.textContent = 'Invio in corso…';

    var dati = new FormData();
    dati.append('fields[email]', email.value.trim());
    var da = origine();
    if (da) dati.append('fields[origine]', da);
    dati.append('ml-submit', '1');
    dati.append('anticsrf', 'true');

    fetch(MAILERLITE_ENDPOINT, { method: 'POST', body: dati, mode: 'no-cors' })
      .then(function () {
        form.style.display = 'none';
        show('Ci siamo quasi: ti ho mandato una email di conferma. Aprila e clicca il link, poi ricevi subito il kit. Se non la vedi, controlla nello spam.');
      })
      .catch(function () {
        submit.disabled = false;
        submit.textContent = originale;
        show('Qualcosa non ha funzionato. Riprova tra poco, oppure scrivimi e te lo mando a mano.');
      });
  });
}());
