# ⚡ Pstryk – integracja z systemem Home Assistant

Integracja **Pstryk** umożliwia połączenie Twojego konta [Pstryk Energy](https://pstryk.pl) z Home Assistant.  
Dzięki niej możesz monitorować **zużycie energii, sprzedaż prądu, bilans dobowy oraz koszty energii** bezpośrednio w panelu HA

> 🛠️ Projekt rozwijany — aktualnie stabilny i w pełni funkcjonalny! Docelowo funkcjonalność będzie podobna do oficjalnej aplikacji mobilnej

---

## 🧩 Funkcje

- 🔐 Konfiguracja przez login i hasło
- 🔐 Aktualizacje przez tokeny
- ⚙️ Pobieranie listy liczników (meters) przypisanych do konta
- ⏰ Automatyczne odświeżanie danych co godzinę (o `xx:59:30`)
- ⚡ Sensory energii (kWh):
  - Dzisiejsze zużycie (`fae_total_usage`)
  - Dzisiejsza sprzedaż (`rae_total`)
  - Dzisiejszy bilans (`energy_balance`)
- 💰 Sensory kosztów (PLN):
  - Dzisiejszy koszt (`fae_total_cost`)
  - Atrybuty z rozbiciem kosztów: VAT, dystrybucja, energia z serwisem
- 👤 Sensory diagnostyczne:
  - ID użytkownika
  - ID licznika (`meter_id`)
  - Adres IP licznika (`details.device.ip`)
  - Timestamp ostatniego odświeżenia danych z API

---

## ⚙️ Instalacja

### 🔹 1. Instalacja przez HACS (zalecana)
1. Otwórz **HACS → Integrations → Custom repositories**
2. Dodaj repozytorium:
   ```
   https://github.com/aLAN-LDZ/Pstryk_HA
   ```
3. Typ: `Integration`
4. Po zainstalowaniu restartuj Home Assistant.

### 🔹 2. Instalacja ręczna
1. Sklonuj repozytorium lub pobierz paczkę ZIP:
2. Skopiuj folder do:
   ```
   config/custom_components/pstryk
   ```
3. Uruchom ponownie Home Assistant.

---

## 🕒 Odświeżanie danych

Koordynator danych (`PstrykCoordinator`) odświeża dane:
- co godzinę o `XX:59:30`
