import asyncio
import tkinter as tk
from tkinter import ttk
import threading
import time
import sys
from datetime import datetime

from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.server import StartTcpServer
from pymodbus.client import ModbusTcpClient

# -------------------------------------------
# Globale Variablen / Datastore
# -------------------------------------------

# Unser Data-Store für den lokalen Server:
#   di -> Discrete Inputs
#   co -> Coils
#   hr -> Holding Registers
#   ir -> Input Registers
store = ModbusSlaveContext(
    di=ModbusSequentialDataBlock(0, [0] * 100),
    co=ModbusSequentialDataBlock(0, [0] * 100),
    hr=ModbusSequentialDataBlock(0, [0] * 100),
    ir=ModbusSequentialDataBlock(0, [0] * 100),
)
context = ModbusServerContext(slaves=store, single=True)


class ModbusApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Modbus Server/Client GUI")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Variablen für Server
        self.server_thread = None
        self.server_running = False
        self.server_instance = None  # Hier speichern wir später das ModbusTcpServer-Objekt

        # Variablen für Client
        self.client_thread = None
        self.client_running = False
        self.client_instance = None

        # Standardwerte für externen Slave
        self.ip_var = tk.StringVar(value="192.168.122.173")
        self.port_var = tk.IntVar(value=5020)
        self.unit_id_var = tk.IntVar(value=1)

        # Für GUI-Anzeige der Inputs und Coils (je 8 Bits)
        self.digital_inputs = [tk.BooleanVar(value=False) for _ in range(8)]
        self.coil_outputs = [tk.BooleanVar(value=False) for _ in range(8)]

        self.create_widgets()

    # ---------------------------------------------------------
    # GUI Layout
    # ---------------------------------------------------------
    def create_widgets(self):
        # Frame: Server Start/Stop
        server_frame = ttk.LabelFrame(self, text="Lokaler Modbus-Server")
        server_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.server_button = ttk.Button(server_frame, text="Server Starten", command=self.toggle_server)
        self.server_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # Frame: Client-Verbindung (IP, Port, Unit)
        client_frame = ttk.LabelFrame(self, text="Externer Modbus-Slave")
        client_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        ttk.Label(client_frame, text="IP-Adresse:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        ip_entry = ttk.Entry(client_frame, textvariable=self.ip_var)
        ip_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        ttk.Label(client_frame, text="Port:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        port_entry = ttk.Entry(client_frame, textvariable=self.port_var)
        port_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        ttk.Label(client_frame, text="Unit ID:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        unit_entry = ttk.Entry(client_frame, textvariable=self.unit_id_var)
        unit_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        self.client_button = ttk.Button(client_frame, text="Polling Starten", command=self.toggle_client)
        self.client_button.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        # Frame: Eingänge (extern)
        inputs_frame = ttk.LabelFrame(self, text="Gelesene Eingänge (Remote)")
        inputs_frame.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        for i in range(8):
            cb = tk.Checkbutton(inputs_frame,
                                text=f"DI {i}",
                                variable=self.digital_inputs[i],
                                state="disabled")
            cb.grid(row=i // 4, column=i % 4, padx=5, pady=5, sticky="w")

        # Frame: Ausgänge (Coils), die wir direkt auf dem externen Slave setzen
        coil_frame = ttk.LabelFrame(self, text="Coil-Ausgänge (Remote)")
        coil_frame.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")
        for i in range(8):
            cb = tk.Checkbutton(coil_frame,
                                text=f"Coil {i}",
                                variable=self.coil_outputs[i],
                                command=lambda idx=i: self.on_coil_toggled(idx))
            cb.grid(row=i // 4, column=i % 4, padx=5, pady=5, sticky="w")

    # ---------------------------------------------------------
    # Lokalen Server Starten/Stoppen
    # ---------------------------------------------------------
    def toggle_server(self):
        if not self.server_running:
            self.start_modbus_server()
        else:
            self.stop_modbus_server()

    def start_modbus_server(self):
        """Erzeugt den ModbusTcpServer und startet ihn in einem Thread."""
        self.server_button.config(text="Server Stoppen")
        self.server_running = True

        def run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            print("🚀 Lokaler Modbus-Server gestartet auf Port 5020.")
            try:
                loop.run_until_complete(StartTcpServer(context, address=("0.0.0.0", 5020)))
            except Exception as e:
                print(f"❌ Serverfehler: {e}")
            finally:
                loop.close()
            print("❌ Server-Thread beendet.")

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

    def stop_modbus_server(self):
        """Stoppt den lokalen Server (shutdown/close)."""
        self.server_button.config(text="Server Starten")
        self.server_running = False
        if self.server_instance is not None:
            try:
                print("❌ Stopping local Modbus server ...")
                self.server_instance.shutdown()      # Stoppt serve_forever()
                self.server_instance.server_close()  # Schließt den Socket
            except Exception as e:
                print(f"Fehler beim Stoppen des Servers: {e}")
            self.server_instance = None

    # ---------------------------------------------------------
    # Externen Client Polling Starten/Stoppen
    # ---------------------------------------------------------
    def toggle_client(self):
        if not self.client_running:
            self.start_client_poll()
        else:
            self.stop_client_poll()

    def start_client_poll(self):
        """Erzeugt den Client (Master), verbindet sich und pollt die Eingänge im Hintergrund."""
        self.client_button.config(text="Polling Stoppen")
        self.client_running = True

        def poll_thread():
            ip = self.ip_var.get()
            port = self.port_var.get()
            unit_id = self.unit_id_var.get()

            # Modbus Client erstellen und verbinden
            self.client_instance = ModbusTcpClient(host=ip, port=port, timeout=3, framer="rtu")

            if not self.client_instance.connect():
                print(f"❌ Konnte nicht verbinden: {ip}:{port}")
                self.client_running = False
                self.client_button.config(text="Polling Starten")
                return

            print(f"✅ Verbunden mit externem Modbus-Slave: {ip}:{port} (Unit {unit_id})")

            while self.client_running:
                # 1) Discrete Inputs abfragen
                resp_di = self.client_instance.read_discrete_inputs(address=0, count=8, slave=unit_id)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                if not resp_di.isError():
                    bits = resp_di.bits
                    print(f"{timestamp} 📥 Eingänge (DI): {bits}")
                    # GUI aktualisieren
                    self.after(0, lambda b=bits: self.update_inputs(b))
                    # Auch lokal im Server speichern
                    for i, val in enumerate(bits):
                        context[0x00].setValues(1, i, [int(val)])  # 1 = Discrete Inputs
                else:
                    print(f"{timestamp} ❌ Fehler beim Lesen der Discrete Inputs")

                time.sleep(1)

            # Client-Verbindung schließen
            self.client_instance.close()
            print("❌ Client-Polling beendet.")

        self.client_thread = threading.Thread(target=poll_thread, daemon=True)
        self.client_thread.start()

    def stop_client_poll(self):
        """Stoppt das Polling des externen Clients."""
        self.client_button.config(text="Polling Starten")
        self.client_running = False

    # ---------------------------------------------------------
    # Eingänge / Ausgänge aktualisieren
    # ---------------------------------------------------------
    def update_inputs(self, bits):
        """Setzt die Digital Inputs in der GUI."""
        for i, val in enumerate(bits):
            self.digital_inputs[i].set(val)

    def on_coil_toggled(self, coil_index):
        """
        Wird aufgerufen, wenn im GUI die Checkbutton
        für einen Coil geändert werden.
        Setzt den Coil direkt auf dem externen Slave.
        Speichert den Wert auch lokal im Server.
        """
        if not self.client_instance or not self.client_instance.connected:
            print("❌ Kein Client verbunden oder Verbindung unterbrochen.")
            return

        unit_id = self.unit_id_var.get()
        value = self.coil_outputs[coil_index].get()
        print(f"Setze Coil {coil_index} (Remote) auf {value} ...")

        # Coil beim externen Slave setzen
        try:
            result = self.client_instance.write_coil(coil_index, value, slave=unit_id)
            if result.isError():
                print(f"❌ Fehler beim Schreiben Coil {coil_index}")
            else:
                print(f"✅ Coil {coil_index} erfolgreich gesetzt auf {value}")
        except Exception as e:
            print(f"❌ Ausnahme beim Schreiben auf Coil {coil_index}: {e}")

        # Auch im lokalen Server abbilden
        # 0x01 = Coils in Modbus-Konvention
        context[0x00].setValues(0x01, coil_index, [int(value)])

    # ---------------------------------------------------------
    # Fenster schließen
    # ---------------------------------------------------------
    def on_closing(self):
        """Beim Schließen des Fensters alles sauber herunterfahren."""
        # Client stoppen
        self.stop_client_poll()
        if self.client_thread is not None:
            self.client_thread.join(timeout=1)

        # Server stoppen
        self.stop_modbus_server()
        if self.server_thread is not None:
            self.server_thread.join(timeout=1)

        self.destroy()


if __name__ == "__main__":
    app = ModbusApp()
    app.mainloop()
    sys.exit(0)
