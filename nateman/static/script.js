// JavaScript des NateMan von Niklas Elsbrock

// --- Flashnachrichten EventListener ---
var flashNode;
for (flashNode of document.getElementsByClassName('flash')) {
  flashNode.onclick = function () {
    this.style.display = 'none';
  };

  flashNode.onkeydown = function (event) {
    if (event.keyCode === 13) {
      this.style.display = 'none';
    }
  };
}


// --- Tabellenzeilen EventListener ---
var trNode;
var href;
for (trNode of document.getElementsByTagName('tr')) {
  if (trNode.getAttribute('data-href') !== null) {
    trNode.onclick = function () {
      window.location = this.getAttribute('data-href');
    };

    trNode.onkeydown = function (event) {
      if (event.keyCode === 13) {
        window.location = this.getAttribute('data-href');
      }
    };
  }
}
