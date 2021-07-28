// NateMan – Nachschreibtermin-Manager
// static/script.js
// Copyright © 2020  Niklas Elsbrock
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
