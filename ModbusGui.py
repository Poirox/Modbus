import tkinter as tk
from tkinter import ttk
import threading
import time
import sys
from datetime import datetime

from pymodbus.client import ModbusTcpClient
from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext

# --------------------
# Global variables
# --------------------
running = True
server_thread = None
client_thread = None

# Default values
DEFAULT_SERVER_IP = "192.168.122.173"
DEFAULT_PORT = 5020
DEFAULT_UNIT_ID = 1

# ------------------------------------------------------------------------------
# Create a data store for the local Modbus server
# ------------------------------------------------------------------------------
store = ModbusSlaveContext(
    di=ModbusSequentialDataBlock(0, [0] * 100),  # Discrete Inputs
    co=ModbusSequentialDataBlock(0, [0] * 100),  # Coils
    hr=ModbusSequentialDataBlock(0, [0] * 100),  # Holding Registers
    ir=ModbusSequentialDataBlock(0, [0] * 100),  # Input Registers
)

context = ModbusServerContext(slaves=store, single=True)

# ------------------------------------------------------------------------------
# GUI Application
# ------------------------------------------------------------------------------
class ModbusApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Modbus Server/Client GUI")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Variables for user input
        self.ip_var = tk.StringVar(value=DEFAULT_SERVER_IP)
        self.port_var = tk.IntVar(value=DEFAULT_PORT)
        self.unit_id_var = tk.IntVar(value=DEFAULT_UNIT_ID)

        # Variables to display digital inputs
        self.digital_inputs = [tk.BooleanVar(value=False) for _ in range(8)]
        
        # Variables to display/drive coil outputs
        self.coil_outputs = [tk.BooleanVar(value=False) for _ in range(8)]

        # Build the GUI layout
        self.create_widgets()

        # Flags to track server/client threads
        self.server_running = False
        self.client_running = False

    def create_widgets(self):
        """
        Create and arrange tkinter widgets.
        """
        # Frame for Server Controls
        server_frame = ttk.LabelFrame(self, text="Local Modbus Server")
        server_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.server_button = ttk.Button(server_frame, text="Start Server", command=self.toggle_server)
        self.server_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # Frame for Client Controls
        client_frame = ttk.LabelFrame(self, text="External Modbus Slave")
        client_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        ttk.Label(client_frame, text="IP Address:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        ip_entry = ttk.Entry(client_frame, textvariable=self.ip_var)
        ip_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(client_frame, text="Port:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        port_entry = ttk.Entry(client_frame, textvariable=self.port_var)
        port_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(client_frame, text="Unit ID:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        unit_entry = ttk.Entry(client_frame, textvariable=self.unit_id_var)
        unit_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        self.client_button = ttk.Button(client_frame, text="Start Polling", command=self.toggle_client)
        self.client_button.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        # Frame for Discrete Inputs
        inputs_frame = ttk.LabelFrame(self, text="Digital Inputs (External Slave)")
        inputs_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        # Create 8 labels/check buttons (read-only style) for the 8 inputs
        for i in range(8):
            cb = tk.Checkbutton(
                inputs_frame, 
                text=f"Input {i}", 
                variable=self.digital_inputs[i], 
                state="disabled"
            )
            cb.grid(row=i // 4, column=i % 4, padx=5, pady=5, sticky="w")

        # Frame for Coil Outputs
        coil_frame = ttk.LabelFrame(self, text="Coil Outputs (Local or External)")
        coil_frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")

        # Create 8 checkbuttons for controlling coil outputs
        for i in range(8):
            cb = tk.Checkbutton(
                coil_frame, 
                text=f"Coil {i}", 
                variable=self.coil_outputs[i],
                command=lambda idx=i: self.set_coil_state(idx)
            )
            cb.grid(row=i // 4, column=i % 4, padx=5, pady=5, sticky="w")

    def toggle_server(self):
        """Start or stop the Modbus server."""
        global server_thread

        if not self.server_running:
            self.server_button.config(text="Stop Server")
            self.server_running = True
            server_thread = threading.Thread(target=self.start_modbus_server, daemon=True)
            server_thread.start()
        else:
            self.server_button.config(text="Start Server")
            self.server_running = False
            # The server started by StartTcpServer is a blocking call.
            # In a real scenario, you'd gracefully shut down the server 
            # (pymodbus doesn't provide an official stop function for the synchronous server).
            # For a quick example, we rely on forcibly stopping the application,
            # or using a workaround (not included here).
            print("Stopping server is not straightforward with StartTcpServer. "
                  "You might need to kill the process or implement an asynchronous server.")
    
    def start_modbus_server(self):
        """Function that starts the local Modbus server."""
        print("🚀 Starting local Modbus server on 0.0.0.0:5020 ...")
        try:
            # This call blocks until the program is interrupted/killed
            StartTcpServer(context, address=("0.0.0.0", 5020))
        except KeyboardInterrupt:
            print("❌ Modbus server interrupted.")
        except Exception as e:
            print(f"❌ Error in Modbus server: {e}")

    def toggle_client(self):
        """Start or stop polling the external Modbus slave."""
        global client_thread

        if not self.client_running:
            self.client_button.config(text="Stop Polling")
            self.client_running = True
            client_thread = threading.Thread(target=self.poll_modbus_client, daemon=True)
            client_thread.start()
        else:
            self.client_button.config(text="Start Polling")
            self.client_running = False
    
    def poll_modbus_client(self):
        """Continuously poll the external Modbus slave for digital inputs."""
        host = self.ip_var.get()
        port = self.port_var.get()
        unit_id = self.unit_id_var.get()

        client = ModbusTcpClient(
            host=host,
            port=port,
            timeout=3
        )

        if not client.connect():
            print(f"❌ Could not connect to Modbus slave at {host}:{port}")
            self.client_running = False
            self.client_button.config(text="Start Polling")
            return

        print(f"✅ Connected to external Modbus slave at {host}:{port}")

        while self.client_running:
            response = client.read_discrete_inputs(address=0, count=8, unit=unit_id)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if not response.isError():
                bits = response.bits
                print(f"{timestamp} 📥 Inputs read: {bits}")

                # Update GUI in the main thread (use .after or thread-safe approach)
                self.update_inputs(bits)
                
                # Optionally store these in the local server's discrete inputs
                for i, value in enumerate(bits):
                    context[0x00].setValues(1, i, [int(value)])
            else:
                print(f"{timestamp} ❌ Error reading discrete inputs")

            time.sleep(1)

        client.close()
        print("❌ Client polling stopped.")
    
    def update_inputs(self, bits):
        """Update the checkbuttons for digital inputs (thread-safe scheduling)."""
        def _update():
            for i, val in enumerate(bits):
                self.digital_inputs[i].set(val)
        self.after(0, _update)

    def set_coil_state(self, coil_index):
        """
        Write the local coil state in the local context or,
        if desired, also to an external device.
        """
        value = self.coil_outputs[coil_index].get()
        print(f"Setting coil {coil_index} to {value}.")

        # You could also write to the external device with the client if you want:
        # client.write_coil(coil_index, value, unit=UNIT_ID)

        # For local server, simply store in coil register:
        context[0x00].setValues(0, coil_index, [int(value)])

    def on_closing(self):
        """Handle the window closing event."""
        global running
        running = False
        self.server_running = False
        self.client_running = False
        self.destroy()

# ------------------------------------------------------------------------------
# Main Entry Point
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    app = ModbusApp()
    app.mainloop()
    sys.exit(0)
