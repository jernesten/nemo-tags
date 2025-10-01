import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GObject, Pango
import os
import sqlite3

class DialogoEtiquetas(Gtk.Dialog):
    def __init__(self, parent, gestor_etiquetas, ruta_archivo):
        # Si parent es None, crear diálogo sin padre
        if parent is None:
            super().__init__(
                title="Gestionar Etiquetas",
                modal=True
            )
        else:
            super().__init__(
                title="Gestionar Etiquetas",
                transient_for=parent,
                modal=True
            )
        
        self.gestor = gestor_etiquetas
        self.ruta_archivo = ruta_archivo
        self.archivo_nombre = os.path.basename(ruta_archivo)
        
        self.set_default_size(400, 500)
        self.set_border_width(10)
        
        self.construir_interfaz()
        self.cargar_etiquetas_actuales()
    
    def construir_interfaz(self):
        box = self.get_content_area()
        
        # Header con nombre del archivo
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        label_archivo = Gtk.Label()
        label_archivo.set_markup(f"<b>Archivo:</b> {self.archivo_nombre}")
        label_archivo.set_halign(Gtk.Align.START)
        header_box.pack_start(label_archivo, False, False, 0)
        
        # Separador
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.pack_start(separator, False, False, 10)
        
        box.pack_start(header_box, False, False, 0)
        
        # Área de añadir nueva etiqueta
        self.construir_entrada_nueva_etiqueta(box)
        
        # Lista de etiquetas actuales
        self.construir_lista_etiquetas(box)
        
        # Etiquetas disponibles
        self.construir_etiquetas_disponibles(box)
        
        self.show_all()
    
    def construir_entrada_nueva_etiqueta(self, parent):
        box_entrada = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        box_entrada.set_margin_top(10)
        box_entrada.set_margin_bottom(10)
        
        self.entry_etiqueta = Gtk.Entry()
        self.entry_etiqueta.set_placeholder_text("Escribe una nueva etiqueta...")
        self.entry_etiqueta.set_hexpand(True)
        self.entry_etiqueta.connect("activate", self.on_anadir_etiqueta)
        
        btn_anadir = Gtk.Button.new_with_label("Añadir")
        btn_anadir.connect("clicked", self.on_anadir_etiqueta)
        
        box_entrada.pack_start(self.entry_etiqueta, True, True, 0)
        box_entrada.pack_start(btn_anadir, False, False, 0)
        
        parent.pack_start(box_entrada, False, False, 0)
    
    def construir_lista_etiquetas(self, parent):
        frame = Gtk.Frame()
        frame.set_label("Etiquetas actuales")
        frame.set_margin_bottom(10)
        
        # Scrolled window para la lista
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(150)
        
        # ListBox para etiquetas
        self.listbox_etiquetas = Gtk.ListBox()
        self.listbox_etiquetas.set_selection_mode(Gtk.SelectionMode.NONE)
        
        scrolled.add(self.listbox_etiquetas)
        frame.add(scrolled)
        parent.pack_start(frame, True, True, 0)
    
    def construir_etiquetas_disponibles(self, parent):
        frame = Gtk.Frame()
        frame.set_label("Etiquetas disponibles")
        frame.set_margin_bottom(10)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(120)
        
        # FlowBox para etiquetas disponibles (como chips)
        self.flowbox_etiquetas = Gtk.FlowBox()
        self.flowbox_etiquetas.set_max_children_per_line(3)
        self.flowbox_etiquetas.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flowbox_etiquetas.set_homogeneous(True)
        
        scrolled.add(self.flowbox_etiquetas)
        frame.add(scrolled)
        parent.pack_start(frame, True, True, 0)
        
        # Botones de acción
        self.construir_botones(parent)
    
    def construir_botones(self, parent):
        box_botones = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box_botones.set_margin_top(10)
        box_botones.set_halign(Gtk.Align.END)
        
        btn_guardar = Gtk.Button.new_with_label("Guardar")
        btn_guardar.connect("clicked", self.on_guardar)
        btn_guardar.get_style_context().add_class("suggested-action")
        
        btn_cancelar = Gtk.Button.new_with_label("Cancelar")
        btn_cancelar.connect("clicked", self.on_cancelar)
        
        box_botones.pack_start(btn_cancelar, False, False, 0)
        box_botones.pack_start(btn_guardar, False, False, 0)
        
        parent.pack_start(box_botones, False, False, 0)
    
    def cargar_etiquetas_actuales(self):
        """Carga las etiquetas actuales del archivo"""
        print(f"🔍 Cargando etiquetas actuales para {self.archivo_nombre}")
        
        # Limpiar listas
        for widget in self.listbox_etiquetas.get_children():
            self.listbox_etiquetas.remove(widget)
        
        for widget in self.flowbox_etiquetas.get_children():
            self.flowbox_etiquetas.remove(widget)
        
        # Cargar etiquetas actuales del archivo
        self.etiquetas_actuales = self.gestor.obtener_etiquetas_archivo(self.ruta_archivo)
        print(f"📁 Etiquetas cargadas: {[e['nombre'] for e in self.etiquetas_actuales]}")
        
        for etiqueta in self.etiquetas_actuales:
            self.agregar_fila_etiqueta_actual(etiqueta)
        
        # Cargar todas las etiquetas disponibles del sistema
        self.cargar_etiquetas_disponibles()
    
    def agregar_fila_etiqueta_actual(self, etiqueta):
        """Añade una etiqueta a la lista de etiquetas actuales"""
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_top(5)
        box.set_margin_bottom(5)
        box.set_margin_start(10)
        box.set_margin_end(10)
        
        # Label con la etiqueta
        label = Gtk.Label(label=etiqueta['nombre'])
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        
        # Botón eliminar
        btn_eliminar = Gtk.Button()
        btn_eliminar.set_image(Gtk.Image.new_from_icon_name("edit-delete", Gtk.IconSize.BUTTON))
        btn_eliminar.set_tooltip_text("Eliminar etiqueta")
        btn_eliminar.connect("clicked", self.on_eliminar_etiqueta, etiqueta['nombre'])
        
        box.pack_start(label, True, True, 0)
        box.pack_start(btn_eliminar, False, False, 0)
        
        row.add(box)
        self.listbox_etiquetas.add(row)
    
    def cargar_etiquetas_disponibles(self):
        """Carga todas las etiquetas del sistema"""
        todas_etiquetas = self.gestor.obtener_todas_etiquetas()
        
        # Filtrar etiquetas que ya están asignadas
        etiquetas_actuales_nombres = [e['nombre'] for e in self.etiquetas_actuales]
        etiquetas_disponibles = [e for e in todas_etiquetas if e['nombre'] not in etiquetas_actuales_nombres]
        
        for etiqueta in etiquetas_disponibles:
            self.agregar_chip_etiqueta(etiqueta)
    
    def agregar_chip_etiqueta(self, etiqueta):
        """Añade una etiqueta como chip en la sección de disponibles"""
        # Crear botón con estilo de chip
        btn = Gtk.Button()
        btn.set_label(etiqueta['nombre'])
        btn.set_relief(Gtk.ReliefStyle.NONE)
        
        # Aplicar estilo de chip
        ctx = btn.get_style_context()
        ctx.add_class("chip")
        ctx.add_class("suggested-action")
        
        btn.connect("clicked", self.on_chip_seleccionado, etiqueta['nombre'])
        btn.set_tooltip_text("Clic para añadir esta etiqueta")
        
        self.flowbox_etiquetas.add(btn)
    
    def on_anadir_etiqueta(self, widget):
        """Añade una nueva etiqueta desde el entry"""
        texto = self.entry_etiqueta.get_text().strip()
        if texto:
            # Verificar si ya existe
            etiquetas_existentes = [e['nombre'] for e in self.etiquetas_actuales]
            if texto not in etiquetas_existentes:
                nueva_etiqueta = {'nombre': texto, 'color': '#3498db'}
                self.etiquetas_actuales.append(nueva_etiqueta)
                self.agregar_fila_etiqueta_actual(nueva_etiqueta)
                
                # Limpiar y actualizar
                self.entry_etiqueta.set_text("")
                self.actualizar_vista()
            
            self.entry_etiqueta.grab_focus()
    
    def on_eliminar_etiqueta(self, widget, nombre_etiqueta):
        """Elimina una etiqueta de la lista actual"""
        self.etiquetas_actuales = [e for e in self.etiquetas_actuales if e['nombre'] != nombre_etiqueta]
        self.actualizar_vista()
    
    def on_chip_seleccionado(self, widget, nombre_etiqueta):
        """Añade una etiqueta desde los chips disponibles"""
        etiqueta = {'nombre': nombre_etiqueta, 'color': '#3498db'}
        self.etiquetas_actuales.append(etiqueta)
        self.agregar_fila_etiqueta_actual(etiqueta)
        self.actualizar_vista()
    
    def actualizar_vista(self):
        """Actualiza toda la vista"""
        self.listbox_etiquetas.show_all()
        self.cargar_etiquetas_disponibles()
        self.flowbox_etiquetas.show_all()
    
    def on_guardar(self, widget):
        """Guarda los cambios en la base de datos"""
        try:
            etiquetas_nombres = [e['nombre'] for e in self.etiquetas_actuales]
            print(f"💾 Guardando etiquetas: {etiquetas_nombres} para {self.archivo_nombre}")
            
            # Guardar en la base de datos
            self.gestor.agregar_etiquetas(self.ruta_archivo, etiquetas_nombres)
            print("✅ Etiquetas guardadas correctamente")
            
            self.response(Gtk.ResponseType.OK)
            self.destroy()
        except Exception as e:
            print(f"❌ Error guardando etiquetas: {e}")
            import traceback
            traceback.print_exc()
    
    def on_cancelar(self, widget):
        """Cierra el diálogo sin guardar"""
        self.response(Gtk.ResponseType.CANCEL)
        self.destroy()
