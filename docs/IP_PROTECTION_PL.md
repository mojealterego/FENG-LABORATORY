# Thermo-IoT — kontrola własności intelektualnej i zasad ujawniania

**Stan: 9 października 2026, PUBLICZNE repozytorium.** Dokument organizacyjny; nie jest opinią o patentowalności ani projektem zgłoszenia patentowego. Nie umieszczać tutaj zastrzeżeń patentowych, szczegółów nowego mocowania TEG, nowych algorytmów sterowania, danych nieujawnionych partnerów lub pomiarów o charakterze tajemnicy przedsiębiorstwa.

## Istotne rozróżnienia

- **Copyright / wszelkie prawa zastrzeżone:** chroni określone oryginalne utwory, **nie daje monopolu patentowego na zasadę działania urządzenia**. Chronimy kod, dokumentację i schematy, a prawa osób trzecich pozostają odrębne.
- **Patent/wzór użytkowy:** ocenie podlegają m.in. nowość, poziom wynalazczy, przemysłowa stosowalność i odpowiedni zakres rozwiązania. **Własna wcześniejsza publiczna publikacja może zniszczyć nowość**. UPRP jako stan techniki rozumie udostępnienie publiczne bez względu na to, czy ktoś faktycznie materiał przeczytał.
- **Brak ogólnej dwunastomiesięcznej ulgi na publikację wynalazku w Polsce lub w systemie EPC.** Wyjątki przy ujawnieniach bez uszczerbku dla nowości są wąskie (np. oczywiste nadużycie i wskazane wystawy; nie traktować tego jako ochrony zwykłej publikacji GitHub).
- **12 miesięcy pierwszeństwa** oznacza na ogół przedział **od daty pierwszego prawidłowego zgłoszenia** wynalazku dla odpowiednich kolejnych zgłoszeń, a **nie od publikacji w GitHub**. Nie przesuwa wcześniejszego stanu techniki wstecz.
- **Tajemnica przedsiębiorstwa:** dotyczy niepublicznych informacji mających wartość gospodarczą, dla których podjęto realne kroki zachowania poufności (np. ograniczenie dostępu, NDA, rozliczalność uprawnień). Publiczny GitHub jej nie zapewnia.

## Procedura dla Thermo-IoT — obowiązująca od teraz

1. **Nie publikować nowych, potencjalnie wynalazczych szczegółów** w tym repo, GitHub Issues, Releases/Artifacts, grantowych załącznikach dostępnych publicznie ani materiałach marketingowych przed indywidualną oceną.
2. **Zachować dowód tego, co już ujawniono** — historia SHA, daty (UTC), opublikowane pliki i ewentualne publiczne kopie; patrz [rejestr metadanych ujawnień](IP_PUBLIC_DISCLOSURE_REGISTER.md). Samo usunięcie pliku z `main` nie usuwa historii, klonów, cache ani wcześniejszego ujawnienia.
3. Prowadzić **poufny dziennik twórców i rozwiązań** poza tym publicznym repo. Wskazać odrębnie autorów kodu, twórców rozwiązań technicznych i właścicieli praw; zweryfikować umowy przeniesienia praw, licencje i relacje z wykonawcami.
4. Niezwłocznie przekazać rzecznikowi patentowemu **historię dotychczasowych publicznych ujawnień i prywatny opis różnicy technicznej** względem znanego stanu techniki (TEG/PMIC/LoRaWAN oraz literatura ciepłownicza). Rzecznik oceni, czy jeszcze istnieje zakres nieujawniony, nowy i nadający się do zgłoszenia, oraz czy zasadne są wzór użytkowy, patent, poufne know-how lub brak zgłoszenia.
5. **Przed kolejną publikacją** uzyskać udokumentowaną decyzję: `PUBLIC_APPROVED` (niewynalazczy opis), `FILE_FIRST` (wymaga potwierdzenia złożenia właściwego zgłoszenia), `KEEP_CONFIDENTIAL` (tajemnica) lub `REWORK_NO_PUBLICATION`. Nie interpretować nazwy statusu jako prawomocnego patentu.
6. Przy rozmowach z laboratorium, fabryką PCB, partnerami, inwestorami i operatorem ciepłowniczym ocenić **NDA, dostęp do danych, prawa do wyników, zgodę na publikację i warunki programu grantowego**. Sama notka poufności nie tworzy podpisanej NDA.
7. Umieszczać w publicznym repo tylko ogólne wymagania, opis działania referencyjnego i **syntetyczne** dane. Surowe pomiary, pliki produkcyjne nowej konstrukcji, zapisy eksperymentów twórczych i nieujawnione algorytmy trzymać w prywatnej przestrzeni.
8. Monitorować patentowe **freedom-to-operate (FTO)** osobno od możliwości uzyskania patentu: patent na własne ulepszenie nie zapewnia swobody korzystania z rozwiązań osób trzecich.
9. Prawa do własnego projektu: **© 2026 Mojeaterego — Andrzej Mikulski, wszelkie prawa zastrzeżone**. Dane kontaktowe udostępnione za zgodą właściciela: mojealterego21@gmail.com, +48 455 575 337.

## Automatyczna bariera publikacyjna (nie gwarancja)

Wymagane na każdym stanowisku klonującym to repo:

```bash
git config --local core.hooksPath .githooks
python -m tools.ip_guard --staged
python -m tools.ip_guard --tracked
```

`.githooks/pre-commit` blokuje wskazane nazwy ścieżek, ciągi sugerujące niezgłoszony wynalazek oraz typowe formy poświadczeń z **indeksu Git**. `.githooks/pre-push` skanuje **każdy wypychany commit**, nawet jeśli poufny plik później usunięto. Nie zmieniają bieżącego stanu repozytorium, tylko ostrzegają / blokują lokalną czynność. `.github/workflows/ip-guard.yml` ponownie analizuje publiczne HEAD, lecz **jest uruchamiany dopiero po publikacji do GitHub**, a więc sam niczego nie utajnia.

Te filtry są celowo proste, nie potrafią wykryć wszystkich sekretów, nowości ani rysunków nadających się do zgłoszenia; mogą również generować błędne alarmy. `--no-verify`, błędna konfiguracja hooków, GitHub UI/API i transfer poza Gitem mogą je ominąć. Gwarancją proceduralną pozostaje **przegląd człowieka i brak publikacji materiału przed zgłoszeniem/zgodą**. Repozytorium pozostaje publiczne, dopóki właściciel jawnie nie podejmie decyzji o zmianie dostępu.

## Źródła oficjalne (weryfikacja 2026-10-09)

- UPRP, nowość i stan techniki: https://uprp.gov.pl/pl/przedmioty-ochrony/wynalazki-i-wzory-u%C5%BCytkowe/wynalazki-i-wzory-uzytkowe-informacje-podstawowe/zdolnosc-patentowa-i-zdolnosc-ochronna
- EPC, art. 55, wąskie wyjątki ujawnienia: https://www.epo.org/en/legal/epc/2020/a55.html
- EPO, pierwszeństwo z pierwszego zgłoszenia: https://www.epo.org/en/legal/guidelines-epc/2026/a_iii_6_1.html
- UPRP, 12 miesięcy zgłoszenia wynalazku: https://uprp.gov.pl/pl/najczesciej-zadawane-pytania-faq
- UPRP, tajemnica przedsiębiorstwa: https://uprp.gov.pl/pl/slownik-terminow?nazwa=Tajemnica-przedsi%C4%99biorstwa

**Działanie priorytetowe:** bez zwłoki skonsultować już publiczne pliki i przyszłe unikatowe elementy techniczne z rzecznikiem patentowym **zanim** dalsze innowacyjne szczegóły zostaną udostępnione.
