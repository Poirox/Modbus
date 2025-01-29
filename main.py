from pymodbus.server import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
import logging

# Logging konfigurieren
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

# Speicherblock mit Dummy-Werten
store = ModbusSlaveContext(
    di=ModbusSequentialDataBlock(0, [0] * 100),  # Diskrete Eingänge
    co=ModbusSequentialDataBlock(0, [0] * 100),  # Coil-Register
    hr=ModbusSequentialDataBlock(0, [10] * 100),  # Holding-Register (z. B. Sensorwerte)
    ir=ModbusSequentialDataBlock(0, [0] * 100),  # Eingangsregister
)

context = ModbusServerContext(slaves=store, single=True)

# Server starten (Standardport 5020, da 502 Root-Rechte benötigt)
print("Starte Modbus-Server auf Port 5020...")
StartTcpServer(context, address=("0.0.0.0", 5020))