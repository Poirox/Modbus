from pymodbus.client import ModbusTcpClient
from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
import threading
import time
import sys

# Globale Variable für sicheres Beenden
running = True

# Modbus-Server (als Slave) Konfiguration
store = ModbusSlaveContext(
    di=ModbusSequentialDataBlock(0, [0] * 100),  # Digitale Eingänge
    co=ModbusSequentialDataBlock(0, [0] * 100),  # Coil-Register
    hr=ModbusSequentialDataBlock(0, [10] * 100),  # Holding-Register
    ir=ModbusSequentialDataBlock(0, [0] * 100),  # Eingangsregister
)
context = ModbusServerContext(slaves=store, single=True)

# Modbus-Client (als Master) Konfiguration
MODBUS_CLIENT_IP = "192.168.122.173"  # IP-Adresse des externen Modbus-Slaves (SPS, I/O-Modul)
MODBUS_PORT = 5020  # Falls 5020 nicht funktioniert, versuche 502
UNIT_ID = 1  # Die Slave-ID des externen Geräts
client = ModbusTcpClient(
    host=MODBUS_CLIENT_IP,
    port=MODBUS_PORT,
    timeout=3,
    framer="rtu"  # **Modbus RTU over TCP**
)

# Funktion, die als Client (Master) die Eingänge eines externen Modbus-Slaves ausliest
def poll_modbus_client():
    global running
    if not client.connect():
        print("❌ Verbindung zum externen Modbus-Client fehlgeschlagen!")
        return

    while running:
        response = client.read_discrete_inputs(address=0, count=8, slave=UNIT_ID)
        if not response.isError():
            digital_inputs = response.bits
            print(f"📥 Gelesene Eingänge: {digital_inputs}")

            # Speichere die gelesenen Werte im lokalen Modbus-Server (als Digitale Eingänge)
            for i, value in enumerate(digital_inputs):
                context[0x00].setValues(1, i, [int(value)])
        else:
            print("❌ Fehler beim Lesen der Eingänge!")

        time.sleep(1)  # Alle 1 Sekunde abfragen

    client.close()
    print("❌ Client gestoppt.")

# Funktion zum Starten des Modbus-Servers
def start_modbus_server():
    print("🚀 Starte Modbus-Server auf Port 5020...")
    try:
        StartTcpServer(context, address=("0.0.0.0", 5020))
    except KeyboardInterrupt:
        print("❌ Modbus-Server gestoppt.")

# Threads starten
server_thread = threading.Thread(target=start_modbus_server, daemon=True)
client_thread = threading.Thread(target=poll_modbus_client, daemon=True)

server_thread.start()
client_thread.start()

# Sichere Beendigung mit CTRL + C
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n❌ Beende das Programm...")
    running = False  # Stoppe Client-Thread
    client_thread.join()
    sys.exit(0)
