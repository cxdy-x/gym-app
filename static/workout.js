// Workout page helpers: add/remove sets, mark exercises done, and remember
// in-progress entries in this browser so a reload (or a swap/add exercise
// round-trip) doesn't wipe what's been typed so far.
(function () {
  var form = document.getElementById('workout-form');
  if (!form) return;

  var PREFIX = 'gym-workout-';
  var KEY = PREFIX + form.dataset.workout;
  var cards = Array.prototype.slice.call(form.querySelectorAll('.exercise[data-ex]'));
  var storage = null;
  try { storage = window.localStorage; } catch (e) { storage = null; }

  function read() {
    if (!storage) return null;
    try {
      var state = JSON.parse(storage.getItem(KEY));
      return state && typeof state === 'object' ? { sets: state.sets || {}, values: state.values || {}, done: state.done || {} } : null;
    } catch (e) { return null; }
  }
  function write(state) {
    if (!storage) return;
    try { storage.setItem(KEY, JSON.stringify(state)); } catch (e) { /* storage full or blocked */ }
  }
  function prune() {
    // Only one workout is pending at a time; drop saved state for any other.
    if (!storage) return;
    try {
      for (var i = storage.length - 1; i >= 0; i--) {
        var key = storage.key(i);
        if (key && key.indexOf(PREFIX) === 0 && key !== KEY) storage.removeItem(key);
      }
    } catch (e) { /* ignore */ }
  }

  function rows(card) { return card.querySelectorAll('.set'); }
  function toggle(card) { return card.querySelector('.done-toggle input'); }
  function isDone(card) { return toggle(card).checked; }

  function numberRow(row, n) {
    row.querySelector('b').textContent = 'Set ' + n;
    Array.prototype.forEach.call(row.querySelectorAll('input'), function (input) {
      input.name = input.name.replace(/-\d+$/, '-' + n);
    });
  }
  function addSet(card) {
    var list = rows(card);
    if (!list.length || list.length >= 30) return;
    var last = list[list.length - 1];
    var copy = last.cloneNode(true);
    var from = last.querySelectorAll('input');
    var to = copy.querySelectorAll('input');
    for (var i = 0; i < from.length; i++) to[i].value = from[i].value; // start from the previous set's numbers
    numberRow(copy, list.length + 1);
    last.parentNode.insertBefore(copy, last.nextSibling);
  }
  function removeSet(card) {
    var list = rows(card);
    if (list.length > 1) list[list.length - 1].remove();
  }

  function refresh() {
    var done = 0;
    cards.forEach(function (card) {
      var on = isDone(card);
      card.classList.toggle('is-done', on);
      if (on) done++;
    });
    var counter = document.getElementById('done-count');
    if (counter) counter.textContent = done;
    var all = document.getElementById('mark-all');
    if (all) all.textContent = cards.length && done === cards.length ? 'Clear all' : 'Mark all done';
  }

  function save() {
    var state = { sets: {}, values: {}, done: {} };
    cards.forEach(function (card) {
      var id = card.dataset.ex;
      state.sets[id] = rows(card).length;
      Array.prototype.forEach.call(card.querySelectorAll('.set input'), function (input) { state.values[input.name] = input.value; });
      if (isDone(card)) state.done[id] = true;
    });
    write(state);
  }

  function restore() {
    var state = read();
    if (!state) return;
    cards.forEach(function (card) {
      var id = card.dataset.ex;
      var wanted = parseInt(state.sets[id], 10);
      if (wanted >= 1 && wanted <= 30) {
        while (rows(card).length < wanted) addSet(card);
        while (rows(card).length > wanted) removeSet(card);
      }
      Array.prototype.forEach.call(card.querySelectorAll('.set input'), function (input) {
        if (Object.prototype.hasOwnProperty.call(state.values, input.name)) input.value = state.values[input.name];
      });
      toggle(card).checked = !!state.done[id];
    });
  }

  form.addEventListener('click', function (event) {
    var button = event.target.closest('[data-action]');
    var card = button && button.closest('.exercise[data-ex]');
    if (!card) return;
    if (button.getAttribute('data-action') === 'add-set') addSet(card); else removeSet(card);
    save();
  });
  form.addEventListener('input', save);
  form.addEventListener('change', function () { refresh(); save(); });
  // Enter in a number box shouldn't submit the whole workout by accident.
  form.addEventListener('keydown', function (event) {
    if (event.key === 'Enter' && event.target.tagName === 'INPUT') event.preventDefault();
  });

  var markAll = document.getElementById('mark-all');
  if (markAll) markAll.addEventListener('click', function () {
    var every = cards.every(isDone);
    cards.forEach(function (card) { toggle(card).checked = !every; });
    refresh();
    save();
  });

  // Swapping reloads the page; forget that exercise's old numbers so the new
  // exercise's own targets show up instead of the previous exercise's entries.
  Array.prototype.forEach.call(document.querySelectorAll('form[id^="swap-"]'), function (swap) {
    swap.addEventListener('submit', function () {
      save();
      var id = swap.id.slice(5);
      var state = read();
      if (!state) return;
      delete state.sets[id];
      delete state.done[id];
      Object.keys(state.values).forEach(function (name) { if (name.split('-')[1] === id) delete state.values[name]; });
      write(state);
    });
  });

  form.addEventListener('submit', function (event) {
    var done = cards.filter(isDone).length;
    if (!done) {
      event.preventDefault();
      window.alert('Mark at least one exercise as done first.');
      return;
    }
    var left = cards.length - done;
    if (left && !window.confirm(left + (left === 1 ? ' exercise isn\u2019t' : ' exercises aren\u2019t') + ' marked done and won\u2019t be logged. Complete anyway?')) {
      event.preventDefault();
    }
  });

  prune();
  restore();
  refresh();
})();
