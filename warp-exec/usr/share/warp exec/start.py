#!/usr/bin/env python3
import gi
import subprocess
import threading
import time

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk

class WarpControllerApp(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="1.1.1.1 Warp VPN")
        self.set_border_width(10)
        self.set_default_size(300, 100)
        self.set_resizable(False)
        
        # Establecer el CSS para el interruptor
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            switch:checked {
                background-color: #2196F3;
            }
            
            switch {
                background-color: #ccc;
                border-radius: 15px;
            }
        """)
        
        screen = Gdk.Screen.get_default()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        
        # Crear el contenedor principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(main_box)
        
        # Crear la caja para el switch y el estado
        control_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        main_box.pack_start(control_box, True, True, 0)
        
        # Etiqueta de estado
        self.status_label = Gtk.Label(label="Estado: Verificando...")
        control_box.pack_start(self.status_label, True, True, 0)
        
        # Switch para encender/apagar Warp
        self.switch = Gtk.Switch()
        self.switch.connect("notify::active", self.on_switch_activated)
        self.switch.set_sensitive(False)  # Deshabilitar hasta verificar estado inicial
        control_box.pack_start(self.switch, False, False, 0)
        
        # Etiqueta para mostrar conectado/desconectado
        self.connection_label = Gtk.Label(label="Desconectado")
        main_box.pack_start(self.connection_label, True, True, 0)
        
        # Iniciar thread para verificar estado inicial
        threading.Thread(target=self.check_warp_status, daemon=True).start()
        
        # Configurar una actualización periódica del estado
        GLib.timeout_add_seconds(5, self.periodic_status_check)
    
    def periodic_status_check(self):
        threading.Thread(target=self.check_warp_status, daemon=True).start()
        return True  # Mantener la llamada periódica
    
    def check_warp_status(self):
        try:
            # Ejecutar curl para verificar estado de Warp
            result = subprocess.run(
                ["curl", "-s", "https://www.cloudflare.com/cdn-cgi/trace/"],
                capture_output=True, text=True
            )
            
            output = result.stdout
            
            # Buscar la línea warp= en la salida
            warp_status = "off"
            for line in output.splitlines():
                if line.startswith("warp="):
                    warp_status = line.split("=")[1].strip()
                    break
            
            is_connected = warp_status == "on"
            
            # Actualizar UI desde el thread principal
            GLib.idle_add(self.update_ui, is_connected)
        except Exception as e:
            GLib.idle_add(self.update_status_label, f"Error: {str(e)}")
    
    def update_ui(self, is_connected):
        self.switch.set_active(is_connected)
        self.switch.set_sensitive(True)
        
        if is_connected:
            self.connection_label.set_text("Conectado")
            self.update_status_label("Estado: Warp conectado")
        else:
            self.connection_label.set_text("Desconectado")
            self.update_status_label("Estado: Warp desconectado")
    
    def update_status_label(self, text):
        self.status_label.set_text(text)
    
    def on_switch_activated(self, switch, gparam):
        # Deshabilitar el switch mientras se procesa la acción
        self.switch.set_sensitive(False)
        self.update_status_label("Estado: Cambiando conexión...")
        
        # Ejecutar comando en un hilo separado para no bloquear la UI
        if switch.get_active():
            command = "warp-cli connect"
            threading.Thread(target=self.execute_command, args=(command,), daemon=True).start()
        else:
            command = "warp-cli disconnect"
            threading.Thread(target=self.execute_command, args=(command,), daemon=True).start()
    
    def execute_command(self, command):
        try:
            # Ejecutar el comando warp-cli
            subprocess.run(command.split(), check=True)
            
            # Esperar un momento para que el cambio tenga efecto
            time.sleep(2)
            
            # Verificar el nuevo estado
            self.check_warp_status()
        except subprocess.CalledProcessError as e:
            GLib.idle_add(self.update_status_label, f"Error al ejecutar {command}: {e}")
            self.switch.set_sensitive(True)

def main():
    app = WarpControllerApp()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()