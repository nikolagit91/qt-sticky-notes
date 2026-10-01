# Fiksture za ručnu GNOME checklistu

Ovdje **nema automatskih testova.** Ovo su pomagala za stavke iz
`docs/RUCNA_GNOME_CHECKLISTA.md` koje se dokazuju samo na pravom
Ubuntu/GNOME sustavu, a traže pripremu koju nije praktično svaki put raditi
ručno. Ništa se odavde ne pokreće iz `run_all.sh` niti iz test suitea.

| Datoteka | Za koju stavku | Što radi |
|---|---|---|
| `sandbox50.sh` | P-1 (slajder prozirnosti), E („50 nota, puni kapacitet") | Podigne app s **50 nota u odvojenom `$HOME`-u**. Prave bilješke se ne diraju. |
| `linkovi.html` | S-2 (tooltip + odbijene sheme) | Stranica s linkovima koji se **kopiraju i zalijepe** u notu, da hrefovi dođu iz stvarnog HTML-a. |
| `link-test.desktop` | S-2 (odbijanje `.desktop`) | Zamka — vidi niže. |

## Zašto `.desktop` datoteka u repou

`link-test.desktop` je **namjerna zamka, ne alat.** Nalaz S-2 je bio da
`xdg-open` na GNOME-u `.desktop` datoteku **pokreće**, pa je link zalijepljen s
weba bio izvršni vektor. Popravak ih odbija.

Problem s provjerom tog popravka je što „ništa se nije dogodilo" izgleda
identično kao „popravak radi" i kao „klik nije registriran". Zato ova datoteka,
ako je nešto ipak pokrene, ispiše notifikaciju **„SIGURNOSNI TEST PAO"**. Time
neuspjeh postaje vidljiv umjesto tih.

Sadržaj je bezopasan — jedini `Exec` je `notify-send` s porukom. `NoDisplay=true`
je da se ne pojavljuje u izborniku aplikacija.

## Pokretanje

```bash
sticky_notes_tests/manual/sandbox50.sh          # 50 nota, odvojen HOME
xdg-open sticky_notes_tests/manual/linkovi.html # test stranica za S-2
```

**Pravi app mora biti ugašen prije `sandbox50.sh`.** D-Bus single-instance ime
(`ipc.py`) je isto bez obzira na `HOME`, pa bi druga instanca tiho izašla kao
sekundarna i ne bi se ništa pojavilo.
