# Thermo-IoT — prywatna teczka dowodowa fizycznego MVP

## Cel

Jest to **procedura integralności danych laboratoryjnych**, nie zastępcze świadectwo pomiarowe, patent, certyfikat wyrobu ani potwierdzenie wykonania urządzenia. Kod jest jawny i referencyjny, ale **wszystkie rzeczywiste pliki pomiarowe przechowywać poza publicznym repozytorium**, z kontrolą dostępu i oceną patentową przed dalszym ujawnieniem.

Oryginalne części projektu: © 2026 Mojeaterego — Andrzej Mikulski. Wszelkie prawa zastrzeżone. Kontakt: mojealterego21@gmail.com / +48 455 575 337.

## Nazwy siedmiu wymaganych plików

| Nazwa pliku w prywatnym katalogu | Źródło fizyczne | Automatyczna kontrola |
|---|---|---|
| `teg_sweep.csv` | Pomiary I-V TEG z udokumentowanym rzeczywistym ΔT | format `thermo_iot.lab`, co najmniej 3 punkty, `evidence_type=measured` |
| `pmic_profile.csv` | Zarejestrowany cold-start i prądy/napięcia pięciu kanałów SCPI/DAQ | format `thermo_iot.pmic`, `measured`, VSTORE od ≤0,1 V do ≥3,0 V |
| `rf_attempt.json` | Komendy AT Wio-E5 wraz ze znacznikiem próby i czasem | struktura programu `thermo_iot.lorawan_fieldtest` |
| `ttn_uplink.json` | Niezależnie wyeksportowany rzeczywisty pakiet The Things Stack | zgodność app/device, FPort 10, 8 B/challenge, fCnt, czas serwera |
| `active_pcb_drc.txt` | Raport KiCad dla **docelowej aktywnej PCB** | zero zgłoszonych naruszeń i zero niepołączonych padów; sam tekst da się sfałszować |
| `firmware_flash.log` | Log flash SWD/identyfikacji fizycznego MCU | niepusty plik i SHA-256; treść/urządzenie wymaga przeglądu człowieka |
| `autonomous_energy_trace.csv` | Szereg rejestracji rzeczywistego generatora przy pracy | format `thermo_iot.trace`, `measured`, ≥604800 s, **≥169 próbek i odstępy ≤3600 s**; wciąż nie dowodzi autentyczności ani pracy bez zewnętrznego zasilania |

**Uwaga:** wyniki testów automatycznych i przykłady `synthetic` nie spełniają tych bramek; nie wolno podmieniać oznaczeń `synthetic` na `measured`. Sama etykieta `measured` także nie dowodzi kalibracji, autorstwa ani pochodzenia pomiaru.

## Procedura operatora

1. Po konsultacji ochrony IP przygotować katalog lokalny, do którego dostęp mają wyłącznie upoważnione osoby, np. `private/mvp-evidence` w lokalnym klonie (w `.gitignore`) lub w zaszyfrowanej przestrzeni poza Git. Nie dodawać plików do issue, Pull Request, CI artifacts, publicznego Google Drive ani do wiadomości bez weryfikacji uprawnień.
2. Przeprowadzić rzeczywiste próby. Zapisać surowe dane i metadane: daty UTC, numery seryjne przyrządów, kalibrację, warunki termiczne, zdjęcia stanowiska, konstrukcję montażu zgodnie z ochroną IP, numer PCB, numer Wio-E5, parametry RF i źródło otrzymania danych TTN.
3. Zarchiwizować oryginały pod siedmioma udokumentowanymi nazwami. **Nie tworzyć ani nie uzupełniać przez AI „rzeczywistych wyników”**, których fizycznie nie uzyskano.
4. Gdy siedem plików istnieje, uruchomić:

```bash
python -m thermo_iot.mvp_acceptance --root private/mvp-evidence --create-manifest
python -m thermo_iot.mvp_acceptance --root private/mvp-evidence
```

5. Pierwsza komenda tworzy manifest SHA-256 (bez nadpisywania). Druga odrzuca brakujące/zmodyfikowane pliki, błędne formaty i niespełnione warunki podstawowe.
6. **Oddzielny przegląd człowieka:** potwierdzić autentyczność plików, metrologię i niepewność, kompletną listę części BOM, fabrykację/montaż, pracę MCU na płytce, zasilanie wyłącznie TEG, lokalną zgodność radiową, niezależny serwer TTN, siedem dni bez zasilania zewnętrznego i brak istotnych przerw. Ostateczne GO/NO-GO wymaga protokołu podpisanego przez odpowiedzialne osoby; moduł nie wydaje takiej decyzji.

## Wymagana interpretacja wyniku

Raport `verification_level: documentary_consistency_only` z `physically_validated: false` oznacza **wyłącznie** spójność przekazanej teczki. Nigdy nie oznacza automatycznej kwalifikacji TRL, patentowalności, bezawaryjności, certyfikacji, pomiaru sprawności PMIC ani rzeczywistej autonomii urządzenia. Fizycznego testu nie da się przeprowadzić na serwerze CI bez laboratorium.

## Uzupełniająca analiza radiowa (niewliczana automatycznie do siedmiu plików)

Przy dłuższym doświadczeniu zapisywać niezależny eksport TTN jako `ttn-uplinks.jsonl` w **prywatnej lokalizacji**. Uruchomić `python -m thermo_iot.rf_audit --file private/mvp-evidence/ttn-uplinks.jsonl --app-id thermo-lab --device-id pipe-1`. Raport pokazuje jedynie obserwowaną serię ramek i parametry odbioru; nie stanowi potwierdzenia PDR ani fizycznego nadawania bez innych danych (log TX, czas/energię, niezależny TTN). [Dokumentacja RF](RF_FIELD_AUDIT.md).
