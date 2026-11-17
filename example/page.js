// The example's page: asks its own service for the board file and card files,
// and tells it about button presses. Nothing is sent anywhere else.
(function () {
  'use strict';
  const place = document.getElementById('board');
  const text = r => (r.ok ? r.text() : Promise.reject(new Error('the service answered ' + r.status)));
  const board = () => fetch('api/board', { cache: 'no-store' }).then(text);
  const options = {
    refresh: board,
    getCard: id => fetch('api/cards/' + encodeURIComponent(id), { cache: 'no-store' })
      .then(r => (r.status === 404 ? null : text(r))),
    onAction: (action, id, typed) => fetch('api/cards/' + encodeURIComponent(id) + '/' + encodeURIComponent(action), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: typed === undefined ? null : typed }),
    }).then(r => r.json().then(j => {
      if (!r.ok) throw new Error(j.error || 'the service answered ' + r.status);
      return j.answer || undefined; // "keep open": the card stays open and is asked for again
    })),
  };
  board().then(t => { window.RESULT = BoardGenerator.draw(place, t, options); }, e => {
    place.textContent = 'The board could not be loaded: ' + e.message;
    place.className = 'load-failed';
  });
})();
