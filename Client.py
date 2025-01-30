from pymodbus.client import ModbusTcpClient
import time
from datetime import datetime

# IP-Adresse des Python-Servers
MODBUS_SERVER_IP = "192.168.122.163"  # IP-Adresse deines Servers
MODBUS_PORT = 5020  # Port deines Python-Servers
UNIT_ID = 1  # Slave ID des Servers
ADDRESS = 0  # Adresse des ersten Coils
QUANTITY = 8  # Anzahl der Coils (gelesene digitale Eingänge)

# Modbus-TCP Client erstellen
client = ModbusTcpClient(MODBUS_SERVER_IP, port=MODBUS_PORT, timeout=3)

print(f"🔄 Verbindung zu {MODBUS_SERVER_IP}:{MODBUS_PORT} wird getestet...")

first_connection = True

try:
    while True:
        if client.connect():
            if first_connection:
                print("✅ Verbindung erfolgreich!")
                first_connection = False

            # Lese 8 Coil-Werte (entspricht digitalen Eingängen des Servers)
            response = client.read_coils(address=ADDRESS, count=QUANTITY, slave=UNIT_ID)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if response.isError():
                print(f"{timestamp} ❌ Fehler beim Lesen der Coils!")
            else:
                print(f"{timestamp} 📥 Eingänge: {response.bits}")

        else:
            print("❌ Verbindung fehlgeschlagen!")

        time.sleep(1)  # Warte 1 Sekunde vor der nächsten Abfrage

except KeyboardInterrupt:
    print("🔴 Abfrage durch Benutzer abgebrochen!")

finally:
    client.close()
    print("🔒 Verbindung geschlossen.")