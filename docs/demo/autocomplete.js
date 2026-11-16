// City search with a planted race: a slow response for an old query can
// overwrite the results for the current one. Used by app.html and the docs demo.
(function () {
  "use strict";

  // Amsterdijk, Amsterdorp and Amsterdrecht are made up, so "Amsterd" and "Amsterdam" give different results.
  var CITIES = [
    "Amstelveen", "Amsterdam", "Amsterdijk", "Amsterdorp", "Amsterdrecht",
    "Antwerp", "Arnhem", "Athens", "Barcelona",
    "Berlin", "Bern", "Brussels", "Budapest", "Copenhagen", "Dublin",
    "Edinburgh", "Helsinki", "Lisbon", "London", "Madrid", "Oslo",
    "Paris", "Prague", "Rome", "Rotterdam", "Stockholm", "Vienna", "Warsaw",
  ];

  var DEBOUNCE_MS = 300;
  var LATENCY_MIN_MS = 100;
  var LATENCY_MAX_MS = 1100;

  // Latency is a fixed function of the query so a failing run replays exactly.
  // Random latency would make failures unreproducible; real networks do vary,
  // which is one more reason these bugs show up in production and not in tests.
  function latencyFor(query) {
    var h = 0x811c9dc5;
    for (var i = 0; i < query.length; i++) {
      h ^= query.charCodeAt(i);
      h = Math.imul(h, 0x01000193) >>> 0;
    }
    return LATENCY_MIN_MS + (h % (LATENCY_MAX_MS - LATENCY_MIN_MS + 1));
  }

  function fakeSearch(query) {
    var q = query.toLowerCase();
    var matches = q ? CITIES.filter(function (c) { return c.toLowerCase().indexOf(q) === 0; }) : [];
    return new Promise(function (resolve) {
      setTimeout(function () { resolve(matches); }, latencyFor(query));
    });
  }

  // options.fixed: ignore responses that aren't for the latest request.
  // options.onEvent(e): optional hook, e = {type: "request"|"response"|"render"|"ignored", query, id, t}.
  function createAutocomplete(root, options) {
    options = options || {};
    var fixed = !!options.fixed;
    var emit = options.onEvent || function () {};
    var input = root.querySelector("[data-role=input]");
    var heading = root.querySelector("[data-role=query]");
    var list = root.querySelector("[data-role=list]");
    var timer = null;
    var latestId = 0;
    var destroyed = false;

    function render(query, matches) {
      heading.textContent = query;
      list.replaceChildren();
      if (matches.length === 0) {
        var li = document.createElement("li");
        li.className = "empty";
        li.textContent = query ? "No matches" : "";
        list.appendChild(li);
        return;
      }
      matches.forEach(function (city) {
        var item = document.createElement("li");
        item.textContent = city;
        list.appendChild(item);
      });
    }

    function search(query) {
      var id = ++latestId;
      emit({ type: "request", query: query, id: id, latency: latencyFor(query), t: performance.now() });
      fakeSearch(query).then(function (matches) {
        if (destroyed) return;
        emit({ type: "response", query: query, id: id, t: performance.now() });
        if (fixed && id !== latestId) {
          emit({ type: "ignored", query: query, id: id, t: performance.now() });
          return;
        }
        // BUG (when not fixed): whichever response arrives last wins.
        render(query, matches);
        emit({ type: "render", query: query, id: id, t: performance.now() });
      });
    }

    function onInput() {
      clearTimeout(timer);
      timer = setTimeout(function () { search(input.value); }, DEBOUNCE_MS);
    }

    input.addEventListener("input", onInput);

    return {
      input: input,
      destroy: function () {
        clearTimeout(timer);
        input.removeEventListener("input", onInput);
        destroyed = true;
      },
    };
  }

  window.Autocomplete = {
    create: createAutocomplete,
    latencyFor: latencyFor,
    DEBOUNCE_MS: DEBOUNCE_MS,
  };
})();
