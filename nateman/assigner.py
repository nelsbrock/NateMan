# NateMan – Nachschreibtermin-Manager
# assigner.py
# Copyright © 2020  Johannes Bingel
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Zuordenen Methode
from typing import List


def iscoopLk(kurs: List):
    for k in kurs:
        if k.schueler.koop:
            return True
    return False


def zuordnen(k_schueler):
    # initziert Variablen
    termin_1_kurse: [int, int] = []
    termin_2_kurse: [int, int] = []

    probleme_kurse = []

    termin_1_kurse_s = []
    termin_2_kurse_s = []
    probleme_kurse_s = []

    if len(k_schueler) != 0:
        s_list = [[k_schueler.pop(0)]]

        # Ordnet die Schüler den ihren Kursen zu
        i = 0

        for s in k_schueler:
            while i < len(s_list):
                if s.klausur.id == s_list[i][0].klausur.id:
                    s_list[i].append(s)
                    break
                i += 1
            else:
                s_list.append([s])
            i = 0
        del i

        # Findet und speichert die Konflikte in ein Dictionary
        h_list = []

        dic = {}

        i = 0
        i2 = 0
        i3 = 0
        i4 = 0

        while i < len(s_list):
            while i2 < len(s_list[i]):
                while i3 < len(s_list):
                    while i4 < len(s_list[i3]):
                        if s_list[i][i2].schueler == s_list[i3][i4].schueler and i != i3 and str(i3) not in h_list:
                            h_list.append(str(i3))
                        i4 += 1
                    i3 += 1
                    i4 = 0
                i2 += 1
                i3 = 0
            if h_list:
                dic[str(i)] = h_list
                h_list = []
            i += 1
            i2 = 0

        del i
        del i2
        del i3
        del i4

        if dic != {}:

            # Fügt die LKs Termin 1 zu
            i = 0

            while i < len(s_list):
                if iscoopLk(s_list[i]) and str(i) in dic:
                    termin_1_kurse.append(str(i))
                i += 1

            while i < len(s_list):
                if s_list[i][0].klausur.kursname[-2] == "L" and str(i) not in termin_1_kurse and str(i) in dic:
                    termin_1_kurse.append(str(i))
                i += 1

            del i

            # Ordnet die LKs Fest ein
            i = 0

            while i < len(termin_1_kurse):
                if str(i) not in termin_2_kurse:
                    for kurs in dic[termin_1_kurse[i]]:
                        if not (kurs in termin_2_kurse):
                            termin_2_kurse.append(kurs)
                    i += 1
                else:
                    termin_1_kurse.remove(str(i))

            i2 = 0

            if not termin_1_kurse:
                for d in dic:
                    termin_1_kurse.append(d)
                    break

            # Füllt die Termine
            finished = False
            while not finished:
                while not (i >= len(termin_1_kurse) and i2 >= len(termin_2_kurse)):
                    if i < len(termin_1_kurse):
                        for kurs in dic[termin_1_kurse[i]]:
                            if kurs in termin_1_kurse[:i]:
                                probleme_kurse.append(termin_1_kurse.pop(i))
                                break
                        else:
                            for kurs in dic[termin_1_kurse[i]]:
                                if not (kurs in termin_2_kurse):
                                    termin_2_kurse.append(kurs)
                            i += 1

                    if i2 < len(termin_2_kurse):
                        for kurs in dic[termin_2_kurse[i2]]:
                            if kurs in termin_2_kurse[:i2]:
                                probleme_kurse.append(termin_2_kurse.pop(i2))
                                break
                        else:
                            for kurs in dic[termin_2_kurse[i2]]:
                                if not (kurs in termin_1_kurse):
                                    termin_1_kurse.append(kurs)
                            i2 += 1
                probleme_kurse = list(set(probleme_kurse))

                for kurs in dic:
                    if kurs not in termin_1_kurse and kurs not in termin_2_kurse \
                            and kurs not in probleme_kurse:
                        termin_2_kurse.append(kurs)
                        break
                else:
                    finished = True

        # Ordnet die nicht problematischen Kurse zu

        i = 0
        while i < len(s_list):
            if str(i) not in termin_1_kurse and str(i) not in termin_2_kurse and str(i) not in probleme_kurse:
                termin_1_kurse.append(str(i))
            i += 1

        for kurs in termin_1_kurse:
            for s in s_list[int(kurs)]:
                termin_1_kurse_s.append(s)

        for kurs in termin_2_kurse:
            for s in s_list[int(kurs)]:
                termin_2_kurse_s.append(s)

        for kurs in probleme_kurse:
            for s in s_list[int(kurs)]:
                probleme_kurse_s.append(s)

        k_schueler.insert(0, s_list[0][0])

        # Ruft die Methode rekursiv auf bis keine Problemkurse vorhanden sind
        if not probleme_kurse_s:
            return [termin_1_kurse_s, termin_2_kurse_s]
        else:
            return [termin_1_kurse_s] + [termin_2_kurse_s] + zuordnen(probleme_kurse_s)
