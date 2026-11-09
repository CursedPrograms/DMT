// Click a picture to see it full size; click again or Esc to close.
(function () {
  "use strict";
  var box = null;
  function close() { if (box) { box.remove(); box = null; } }
  document.querySelectorAll(".shot, .grid img").forEach(function (img) {
    img.addEventListener("click", function () {
      box = document.createElement("div");
      box.className = "lightbox";
      var big = document.createElement("img");
      big.src = img.src;
      big.alt = img.alt;
      box.appendChild(big);
      box.addEventListener("click", close);
      document.body.appendChild(box);
    });
  });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") close(); });
})();
