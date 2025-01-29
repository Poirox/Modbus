from pymodbus.client import ModbusTcpClient

# Verbindung zum Server auf Port 5020
client = ModbusTcpClient("192.168.122.142", port=5020)

# Verbindung prüfen
if client.connect():
    print("✅ Verbindung erfolgreich!")
    
    # Register 1-5 lesen
    response = client.read_holding_registers(address=1, count=5)
    if response.isError():
        print("❌ Fehler beim Lesen")
    else:
        print(f"📊 Werte: {response.registers}")

    # Verbindung schließen
    client.close()
else:
    print("❌ Verbindung fehlgeschlagen")
