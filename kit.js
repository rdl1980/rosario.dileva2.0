/* =========================================================
   Officina della Narrazione — modulo di iscrizione al kit
   Invia a Brevo (lista "Officina della Narrazione") con
   doppio opt-in. Il kit arriva nell'email di conferma finale.
   ========================================================= */

var BREVO_ENDPOINT = 'https://7fe28f70.sibforms.com/serve/MUIFAGfZtB3mou91Nr2ScbYZgUSLaL28uSMfTFXD-3i5jBPF7om3cSMWeFMpUdD4SNee7f1S-1l_lpb82L8Lhhy6LZYg_TsBP9fMnNIdOPbMTZnhFzv0Z0fI5WgFeIn77KmZOnjMEv9OsAVh6GXiPLG87gx0Jqd8NwewTmmzJnAZYXsjTqJ3FYaHUwm4RoIXaU5CY2ozRVg3MGsj_w==';

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

    submit.disabled = true;
    var originale = submit.textContent;
    submit.textContent = 'Invio in corso…';

    var dati = new FormData();
    dati.append('EMAIL', email.value.trim());
    dati.append('email_address_check', '');   // honeypot antispam di Brevo
    dati.append('locale', 'it');
    dati.append('html_type', 'simple');
    var da = origine();
    if (da) dati.append('ORIGINE', da);

    fetch(BREVO_ENDPOINT, { method: 'POST', body: dati, mode: 'no-cors' })
      .then(function () {
        form.style.display = 'none';
        show('Ci siamo quasi: ti ho mandato una email di conferma. Aprila e clicca il link, e ricevi subito il kit. Se non la vedi, controlla nello spam.');
      })
      .catch(function () {
        submit.disabled = false;
        submit.textContent = originale;
        show('Qualcosa non ha funzionato. Riprova tra poco, oppure scrivimi e te lo mando a mano.');
      });
  });
}());
