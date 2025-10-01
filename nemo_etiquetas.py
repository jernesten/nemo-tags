#!/usr/bin/env python3

import gi
gi.require_version('Nemo', '3.0')
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')

from gi.repository import Nemo, GObject, Gtk, Gdk
import os
import sys
import subprocess

# IMPORTANTE: Añade la ruta a la carpeta nemo-etiquetas donde están los otros módulos
extension_dir = os.path.join(os.path.dirname(__file__), 'nemo-etiquetas')
sys.path.insert(0, extension_dir)

try:
    from gestor_etiquetas import GestorEtiquetasSQLite
    from dialogo_etiquetas import DialogoEtiquetas
    MODULOS_CARGADOS = True
    print("✅ ETIQUETAS: Módulos cargados correctamente")
except ImportError as e:
    print(f"❌ ETIQUETAS: Error importando módulos: {e}")
    MODULOS_CARGADOS = False

class EtiquetasExtension(GObject.GObject, Nemo.MenuProvider):
    def __init__(self):
        print("Inicializando extensión de etiquetas...")
        self.gestor = GestorEtiquetasSQLite()
        self.cargar_estilos()
        self.limpiar_cache_antiguo()
    
    def cargar_estilos(self):
        """Carga los estilos CSS para la aplicación"""
        css = """
        .chip {
            border-radius: 12px;
            padding: 4px 12px;
            margin: 2px;
            border: 1px solid @theme_selected_bg_color;
            font-size: 0.9em;
        }
        .chip:hover {
            background-color: alpha(@theme_selected_bg_color, 0.2);
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
    def get_file_items(self, window, files):
        """Proporciona items del menú para archivos"""
        if not MODULOS_CARGADOS:
            return []
            
        if len(files) != 1:
            return []
        
        # Solo mostrar para archivos regulares, no directorios
        file = files[0]
        if file.is_directory():
            return []
        
        print(f"✅ ETIQUETAS: Creando menú para {file.get_name()}")
        
        item = Nemo.MenuItem(
            name="EtiquetasExtension::GestionarEtiquetas",
            label="🏷️ Gestionar Etiquetas",
            tip="Añadir o quitar etiquetas del archivo"
        )
        # Pasar la ventana como parámetro adicional
        item.connect('activate', self.mostrar_dialogo_etiquetas, window, files[0])
        return [item]
    
    def get_background_items(self, window, file):
        """Items del menú para fondo del directorio"""
        if not MODULOS_CARGADOS:
            return []
        
        # SOLO el menú de búsqueda
        item_buscar = Nemo.MenuItem(
            name="EtiquetasExtension::BuscarEtiquetas",
            label="🔍 Buscar por Etiquetas", 
            tip="Buscar archivos por etiquetas"
        )
        item_buscar.connect('activate', self.mostrar_buscador_etiquetas, window, file)
        
        return [item_buscar]
    
    def mostrar_dialogo_etiquetas(self, menu, window, file):
        """Muestra el diálogo de gestión de etiquetas"""
        try:
            ruta = file.get_location().get_path()
            print(f"✅ ETIQUETAS: Abriendo diálogo para {ruta}")
            
            # SOLUCIÓN ROBUSTA: Manejar cuando window es None
            parent = None
            if window is not None:
                # Verificar que window sea realmente una ventana Gtk
                from gi.repository import Gtk
                if isinstance(window, Gtk.Window):
                    parent = window
                else:
                    print("⚠️  ETIQUETAS: Window no es una ventana Gtk válida")
            
            # Si no tenemos ventana padre, buscar entre las ventanas abiertas
            if parent is None:
                from gi.repository import Gtk
                for w in Gtk.Window.list_toplevels():
                    title = w.get_title()
                    if title and ("nemo" in title.lower() or "Nemo" in title):
                        parent = w
                        break
            
            if parent is None:
                print("⚠️  ETIQUETAS: Abriendo diálogo sin ventana padre")
            else:
                print(f"✅ ETIQUETAS: Usando ventana padre: {parent.get_title()}")
            
            dialogo = DialogoEtiquetas(parent, self.gestor, ruta)
            response = dialogo.run()
            
            if response == Gtk.ResponseType.OK:
                print("✅ ETIQUETAS: Diálogo cerrado con Guardar")
            else:
                print("✅ ETIQUETAS: Diálogo cerrado con Cancelar")
                
        except Exception as e:
            print(f"❌ ETIQUETAS: Error mostrando diálogo: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback: intentar abrir el diálogo sin ventana padre
            try:
                print("🔄 ETIQUETAS: Intentando fallback sin ventana padre...")
                dialogo = DialogoEtiquetas(None, self.gestor, ruta)
                dialogo.run()
            except Exception as e2:
                print(f"❌ ETIQUETAS: Fallback también falló: {e2}")
    
    
    def buscar_archivos_por_etiqueta(self, etiqueta):
        """Busca archivos que tengan una etiqueta específica"""
        try:
            archivos = self.gestor.buscar_por_etiquetas([etiqueta], operador='OR')
            print(f"🔍 Encontrados {len(archivos)} archivos con etiqueta '{etiqueta}':")
            for archivo in archivos:
                print(f"  📄 {os.path.basename(archivo)}")
            return archivos
        except Exception as e:
            print(f"❌ Error buscando archivos: {e}")
            return []

    def mostrar_buscador_etiquetas(self, menu, window, file):
        """Muestra el diálogo de búsqueda por etiquetas con filtro en tiempo real"""
        try:
            print("🔍 Abriendo buscador de etiquetas mejorado...")
            
            # Obtener todas las etiquetas disponibles
            self.todas_etiquetas = self.gestor.obtener_todas_etiquetas()
            print(f"🔍 Etiquetas disponibles: {[e['nombre'] for e in self.todas_etiquetas]}")
            
            # Crear diálogo de búsqueda
            dialogo_busqueda = Gtk.Dialog(
                title="Buscar Archivos por Etiquetas",
                transient_for=window,
                modal=True
            )
            dialogo_busqueda.set_default_size(500, 500)
            
            content_area = dialogo_busqueda.get_content_area()
            
            # Campo de búsqueda para filtrar etiquetas
            box_busqueda = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            box_busqueda.set_margin_top(10)
            box_busqueda.set_margin_bottom(10)
            box_busqueda.set_margin_start(10)
            box_busqueda.set_margin_end(10)
            
            label_buscar = Gtk.Label(label="🔍 Filtrar:")
            self.entry_buscar = Gtk.Entry()
            self.entry_buscar.set_placeholder_text("Escribe para filtrar etiquetas...")
            self.entry_buscar.set_hexpand(True)
            self.entry_buscar.connect("changed", self.on_filtrar_etiquetas)
            
            box_busqueda.pack_start(label_buscar, False, False, 0)
            box_busqueda.pack_start(self.entry_buscar, True, True, 0)
            content_area.pack_start(box_busqueda, False, False, 0)
            
            # Frame para la lista de etiquetas
            frame_etiquetas = Gtk.Frame()
            frame_etiquetas.set_label("Etiquetas disponibles")
            frame_etiquetas.set_margin_start(10)
            frame_etiquetas.set_margin_end(10)
            frame_etiquetas.set_margin_bottom(10)
            
            # ListBox para etiquetas (ahora con doble clic para buscar)
            self.listbox_etiquetas = Gtk.ListBox()
            self.listbox_etiquetas.set_selection_mode(Gtk.SelectionMode.SINGLE)
            self.listbox_etiquetas.connect("row-activated", self.on_etiqueta_seleccionada)
            
            # Llenar la lista inicial
            self.actualizar_lista_etiquetas(self.todas_etiquetas)
            
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scrolled.set_min_content_height(200)
            scrolled.add(self.listbox_etiquetas)
            frame_etiquetas.add(scrolled)
            content_area.pack_start(frame_etiquetas, True, True, 0)
            
            # Botón de búsqueda múltiple
            box_botones = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            box_botones.set_margin_bottom(10)
            box_botones.set_margin_start(10)
            box_botones.set_margin_end(10)
            box_botones.set_halign(Gtk.Align.END)
            
            btn_buscar_multiple = Gtk.Button.new_with_label("Búsqueda Avanzada")
            btn_buscar_multiple.connect('clicked', self.on_busqueda_avanzada)
            
            btn_cerrar = Gtk.Button.new_with_label("Cerrar")
            btn_cerrar.connect('clicked', lambda w: dialogo_busqueda.response(Gtk.ResponseType.CLOSE))
            
            box_botones.pack_start(btn_buscar_multiple, False, False, 0)
            box_botones.pack_start(btn_cerrar, False, False, 0)
            content_area.pack_start(box_botones, False, False, 0)
            
            dialogo_busqueda.show_all()
            response = dialogo_busqueda.run()
            dialogo_busqueda.destroy()
            
        except Exception as e:
            print(f"❌ Error mostrando buscador: {e}")
            import traceback
            traceback.print_exc()

    def actualizar_lista_etiquetas(self, etiquetas):
        """Actualiza la lista de etiquetas en el diálogo de búsqueda"""
        # Limpiar lista actual
        for widget in self.listbox_etiquetas.get_children():
            self.listbox_etiquetas.remove(widget)
        
        # Añadir etiquetas filtradas
        for etiqueta in etiquetas:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            box.set_margin_top(5)
            box.set_margin_bottom(5)
            box.set_margin_start(10)
            box.set_margin_end(10)
            
            # Icono de etiqueta
            icono = Gtk.Image.new_from_icon_name("tag-symbolic", Gtk.IconSize.BUTTON)
            
            label_etiqueta = Gtk.Label(label=etiqueta['nombre'])
            label_etiqueta.set_halign(Gtk.Align.START)
            label_etiqueta.set_hexpand(True)
            
            # Contador de archivos (opcional)
            label_contador = Gtk.Label(label="? archivos")
            label_contador.get_style_context().add_class("dim-label")
            
            box.pack_start(icono, False, False, 0)
            box.pack_start(label_etiqueta, True, True, 0)
            box.pack_start(label_contador, False, False, 0)
            row.add(box)
            
            # Guardar el nombre de la etiqueta en la fila
            row.etiqueta_nombre = etiqueta['nombre']
            
            self.listbox_etiquetas.add(row)
        
        self.listbox_etiquetas.show_all()

    def on_filtrar_etiquetas(self, entry):
        """Filtra la lista de etiquetas en tiempo real"""
        texto = entry.get_text().lower().strip()
        
        if texto == "":
            # Mostrar todas las etiquetas
            etiquetas_filtradas = self.todas_etiquetas
        else:
            # Filtrar etiquetas que contengan el texto
            etiquetas_filtradas = [
                e for e in self.todas_etiquetas 
                if texto in e['nombre'].lower()
            ]
        
        self.actualizar_lista_etiquetas(etiquetas_filtradas)
        print(f"🔍 Filtrado: '{texto}' -> {len(etiquetas_filtradas)} etiquetas")

    def on_etiqueta_seleccionada(self, listbox, row):
        """Cuando se hace doble clic en una etiqueta, buscar archivos"""
        if hasattr(row, 'etiqueta_nombre'):
            etiqueta_nombre = row.etiqueta_nombre
            print(f"🔍 Buscando archivos con etiqueta: {etiqueta_nombre}")
            archivos = self.gestor.buscar_por_etiquetas([etiqueta_nombre], operador='OR')
            
            if archivos:
                print(f"✅ Encontrados {len(archivos)} archivos con '{etiqueta_nombre}':")
                for archivo in archivos:
                    print(f"   📄 {os.path.basename(archivo)}")
                
                # Mostrar resultados en un diálogo
                self.mostrar_resultados_busqueda(archivos, etiqueta_nombre)
            else:
                print(f"❌ No se encontraron archivos con la etiqueta '{etiqueta_nombre}'")
                
                # Mostrar mensaje de no resultados
                dialog = Gtk.MessageDialog(
                    transient_for=listbox.get_toplevel(),
                    modal=True,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    text=f"No se encontraron archivos con la etiqueta '{etiqueta_nombre}'"
                )
                dialog.run()
                dialog.destroy()

    def on_busqueda_avanzada(self, widget):
        """Diálogo para búsqueda avanzada con múltiples etiquetas"""
        try:
            print("🔍 Iniciando búsqueda avanzada...")
            
            # Diálogo de búsqueda avanzada
            dialog = Gtk.Dialog(
                title="Búsqueda Avanzada por Etiquetas",
                modal=True,
                default_width=500,
                default_height=400
            )
            
            content_area = dialog.get_content_area()
            
            # Instrucciones
            label_instrucciones = Gtk.Label()
            label_instrucciones.set_markup(
                "<b>Selecciona múltiples etiquetas para buscar:</b>\n"
                "• <b>AND</b>: Archivos que tienen TODAS las etiquetas seleccionadas\n"  
                "• <b>OR</b>: Archivos que tienen AL MENOS UNA etiqueta seleccionada"
            )
            label_instrucciones.set_margin_bottom(10)
            label_instrucciones.set_line_wrap(True)
            content_area.pack_start(label_instrucciones, False, False, 0)
            
            # Lista de etiquetas con checkboxes
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scrolled.set_min_content_height(200)
            
            self.lista_checks_avanzada = Gtk.ListBox()
            self.lista_checks_avanzada.set_selection_mode(Gtk.SelectionMode.NONE)
            
            for etiqueta in self.todas_etiquetas:
                row = Gtk.ListBoxRow()
                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                box.set_margin_top(5)
                box.set_margin_bottom(5)
                box.set_margin_start(10)
                box.set_margin_end(10)
                
                check = Gtk.CheckButton()
                label = Gtk.Label(label=etiqueta['nombre'])
                label.set_halign(Gtk.Align.START)
                label.set_hexpand(True)
                
                box.pack_start(check, False, False, 0)
                box.pack_start(label, True, True, 0)
                row.add(box)
                
                # Guardar referencia al checkbox
                row.checkbox = check
                row.etiqueta_nombre = etiqueta['nombre']
                
                self.lista_checks_avanzada.add(row)
            
            scrolled.add(self.lista_checks_avanzada)
            content_area.pack_start(scrolled, True, True, 0)
            
            # Controles de búsqueda
            box_controles = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            box_controles.set_margin_top(10)
            box_controles.set_margin_bottom(10)
            
            # Selector de operador
            box_operador = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            label_operador = Gtk.Label(label="Tipo de búsqueda:")
            self.combo_operador = Gtk.ComboBoxText()
            self.combo_operador.append_text("AND - Debe tener TODAS las etiquetas")
            self.combo_operador.append_text("OR - Debe tener AL MENOS UNA etiqueta")  
            self.combo_operador.set_active(0)
            
            box_operador.pack_start(label_operador, False, False, 0)
            box_operador.pack_start(self.combo_operador, False, False, 0)
            
            # Botones
            btn_buscar = Gtk.Button.new_with_label("🔍 Ejecutar Búsqueda")
            btn_buscar.connect('clicked', self.on_ejecutar_busqueda_avanzada, dialog)
            
            btn_limpiar = Gtk.Button.new_with_label("🗑️ Limpiar Selección")
            btn_limpiar.connect('clicked', self.on_limpiar_seleccion_avanzada)
            
            btn_cerrar = Gtk.Button.new_with_label("Cerrar")
            btn_cerrar.connect('clicked', lambda w: dialog.response(Gtk.ResponseType.CLOSE))
            
            box_controles.pack_start(box_operador, True, True, 0)
            box_controles.pack_start(btn_limpiar, False, False, 0)
            box_controles.pack_start(btn_buscar, False, False, 0)
            box_controles.pack_start(btn_cerrar, False, False, 0)
            content_area.pack_start(box_controles, False, False, 0)
            
            dialog.show_all()
            response = dialog.run()
            dialog.destroy()
            
        except Exception as e:
            print(f"❌ Error en búsqueda avanzada: {e}")
            import traceback
            traceback.print_exc()

    def on_limpiar_seleccion_avanzada(self, widget):
        """Limpia todos los checkboxes de la búsqueda avanzada"""
        for row in self.lista_checks_avanzada.get_children():
            if hasattr(row, 'checkbox'):
                row.checkbox.set_active(False)

    def on_ejecutar_busqueda_avanzada(self, widget, dialog):
        """Ejecuta la búsqueda avanzada con las etiquetas seleccionadas"""
        try:
            # Obtener etiquetas seleccionadas
            etiquetas_seleccionadas = []
            for row in self.lista_checks_avanzada.get_children():
                if hasattr(row, 'checkbox') and row.checkbox.get_active():
                    etiquetas_seleccionadas.append(row.etiqueta_nombre)
            
            if not etiquetas_seleccionadas:
                # Mostrar mensaje de error
                error_dialog = Gtk.MessageDialog(
                    transient_for=dialog,
                    modal=True,
                    message_type=Gtk.MessageType.WARNING,
                    buttons=Gtk.ButtonsType.OK,
                    text="Por favor selecciona al menos una etiqueta para buscar"
                )
                error_dialog.run()
                error_dialog.destroy()
                return
            
            # Determinar operador
            operador = 'AND' if self.combo_operador.get_active() == 0 else 'OR'
            
            print(f"🔍 Búsqueda avanzada ejecutando: {etiquetas_seleccionadas} ({operador})")
            
            # Ejecutar búsqueda
            archivos = self.gestor.buscar_por_etiquetas(etiquetas_seleccionadas, operador=operador)
            
            # Cerrar diálogo actual
            dialog.response(Gtk.ResponseType.OK)
            
            if archivos:
                print(f"✅ Encontrados {len(archivos)} archivos con búsqueda {operador}")
                
                # Mostrar resultados en Nemo
                descripcion = f"{operador}: {', '.join(etiquetas_seleccionadas)}"
                self.mostrar_resultados_busqueda(archivos, descripcion)
            else:
                print("❌ No se encontraron archivos")
                
                # Mostrar mensaje
                msg_dialog = Gtk.MessageDialog(
                    transient_for=dialog,
                    modal=True,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    text=f"No se encontraron archivos con la combinación de etiquetas:\n\n{operador}: {', '.join(etiquetas_seleccionadas)}"
                )
                msg_dialog.run()
                msg_dialog.destroy()
                
        except Exception as e:
            print(f"❌ Error ejecutando búsqueda avanzada: {e}")
            import traceback
            traceback.print_exc()

    def mostrar_resultados_busqueda(self, archivos, etiqueta_nombre):
        """Sistema de cache inteligente que reutiliza resultados existentes"""
        try:
            if not archivos:
                dialog = Gtk.MessageDialog(
                    transient_for=None,
                    modal=True,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    text=f"No se encontraron archivos con la etiqueta '{etiqueta_nombre}'"
                )
                dialog.run()
                dialog.destroy()
                return
            
            print(f"📂 Buscando en cache o creando vista para {len(archivos)} archivos...")
            
            # Crear directorio cache si no existe
            cache_dir = os.path.expanduser("~/.cache/nemo-etiquetas")
            os.makedirs(cache_dir, exist_ok=True)
            
            # Generar hash único de esta búsqueda
            import hashlib
            contenido_hash = f"{','.join(sorted(archivos))}:{etiqueta_nombre}"
            hash_busqueda = hashlib.md5(contenido_hash.encode('utf-8')).hexdigest()[:12]
            
            # Buscar carpeta existente con el mismo hash
            carpeta_existente = None
            for item in os.listdir(cache_dir):
                item_path = os.path.join(cache_dir, item)
                if os.path.isdir(item_path) and hash_busqueda in item:
                    # Verificar que los enlaces aún sean válidos
                    if self.verificar_enlaces_validos(item_path, archivos):
                        carpeta_existente = item_path
                        print(f"  🔍 Cache encontrado: {carpeta_existente}")
                        break
            
            if carpeta_existente:
                # Reutilizar cache existente
                carpeta_resultados = carpeta_existente
                print(f"  ✅ Reutilizando cache existente")
                
                # Actualizar timestamp para mantenerlo "fresco"
                os.utime(carpeta_resultados, None)
                
            else:
                # Crear nueva carpeta de resultados
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                nombre_carpeta = f"busqueda_{timestamp}_{hash_busqueda}"
                carpeta_resultados = os.path.join(cache_dir, nombre_carpeta)
                os.makedirs(carpeta_resultados, exist_ok=True)
                
                print(f"  📁 Nueva carpeta cache: {carpeta_resultados}")
                
                # Crear enlaces simbólicos
                archivos_procesados = self.crear_enlaces_simbolicos(carpeta_resultados, archivos)
                
                if archivos_procesados == 0:
                    print("❌ No se pudieron crear enlaces")
                    dialog = Gtk.MessageDialog(
                        transient_for=None,
                        modal=True,
                        message_type=Gtk.MessageType.ERROR,
                        buttons=Gtk.ButtonsType.OK,
                        text="Error: No se pudieron crear enlaces a los archivos encontrados"
                    )
                    dialog.run()
                    dialog.destroy()
                    return
                
                # Crear metadata de la búsqueda
                self.crear_metadata_busqueda(carpeta_resultados, archivos, etiqueta_nombre, hash_busqueda)
            
            # Abrir la carpeta en Nemo
            self.abrir_carpeta_nemo(carpeta_resultados)
            
            # Mostrar información al usuario
            self.mostrar_info_usuario(archivos, etiqueta_nombre, carpeta_resultados, bool(carpeta_existente))
            
            # Limpiar cache antiguo periódicamente
            if not carpeta_existente:  # Solo limpiar cuando creamos nueva carpeta
                self.limpiar_cache_antiguo()
            
        except Exception as e:
            print(f"❌ Error en mostrar_resultados_busqueda: {e}")
            import traceback
            traceback.print_exc()

    def verificar_enlaces_validos(self, carpeta, archivos_esperados):
        """Verifica que todos los enlaces en la carpeta apunten a los archivos esperados"""
        try:
            archivos_esperados_set = set(archivos_esperados)
            archivos_encontrados = set()
            
            for item in os.listdir(carpeta):
                item_path = os.path.join(carpeta, item)
                
                # Saltar el archivo de metadata
                if item == "metadata.json":
                    continue
                    
                if os.path.islink(item_path):
                    try:
                        objetivo = os.readlink(item_path)
                        if objetivo in archivos_esperados_set:
                            archivos_encontrados.add(objetivo)
                        else:
                            return False  # Enlace apunta a archivo incorrecto
                    except:
                        return False  # Enlace roto
                else:
                    return False  # Archivo que no es enlace
            
            # Verificar que tenemos todos los archivos esperados
            return archivos_encontrados == archivos_esperados_set
            
        except Exception as e:
            print(f"❌ Error verificando enlaces: {e}")
            return False

    def crear_enlaces_simbolicos(self, carpeta_destino, archivos):
        """Crea enlaces simbólicos optimizados"""
        archivos_procesados = 0
        
        for archivo_original in archivos:
            try:
                nombre_archivo = os.path.basename(archivo_original)
                nombre_base, extension = os.path.splitext(nombre_archivo)
                
                # Generar nombre único para el enlace
                contador = 1
                nombre_enlace = nombre_archivo
                ruta_enlace = os.path.join(carpeta_destino, nombre_enlace)
                
                while os.path.exists(ruta_enlace):
                    # Si ya existe un enlace que apunta al mismo archivo, reutilizarlo
                    if os.path.islink(ruta_enlace) and os.readlink(ruta_enlace) == archivo_original:
                        break
                    nombre_enlace = f"{nombre_base}_{contador}{extension}"
                    ruta_enlace = os.path.join(carpeta_destino, nombre_enlace)
                    contador += 1
                
                # Solo crear enlace si no existe
                if not os.path.exists(ruta_enlace):
                    os.symlink(archivo_original, ruta_enlace)
                    archivos_procesados += 1
                    print(f"  🔗 Enlace creado: {nombre_enlace}")
                    
            except Exception as e:
                print(f"  ❌ Error creando enlace para {archivo_original}: {e}")
        
        return archivos_procesados

    def crear_metadata_busqueda(self, carpeta, archivos, etiqueta_nombre, hash_busqueda):
        """Crea archivo de metadata para tracking y reutilización"""
        import json
        from datetime import datetime
        
        metadata = {
            "hash_busqueda": hash_busqueda,
            "etiqueta": etiqueta_nombre,
            "total_archivos": len(archivos),
            "fecha_creacion": datetime.now().isoformat(),
            "archivos": archivos
        }
        
        metadata_path = os.path.join(carpeta, "metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def abrir_carpeta_nemo(self, carpeta):
        """Abre la carpeta en Nemo"""
        try:
            subprocess.Popen(['nemo', carpeta])
            print(f"✅ Nemo abierto en: {carpeta}")
        except Exception as e:
            print(f"❌ Error abriendo Nemo: {e}")
            try:
                os.system(f"nemo '{carpeta}' &")
            except:
                pass

    def mostrar_info_usuario(self, archivos, etiqueta_nombre, carpeta_resultados, cache_reutilizado):
        """Muestra información al usuario sobre la búsqueda"""
        if cache_reutilizado:
            estado_cache = "✅ (Resultados reutilizados del cache)"
        else:
            estado_cache = "🆕 (Nueva búsqueda)"
        
        mensaje = f"""✅ Búsqueda completada {estado_cache}

    📊 Resultados:
    • Etiqueta: {etiqueta_nombre}
    • Archivos encontrados: {len(archivos)}
    • Ubicación: {carpeta_resultados}

    💡 Características del sistema:
    • Cache inteligente que reutiliza resultados idénticos
    • Los enlaces son seguros y no modifican los originales
    • Limpieza automática de búsquedas antiguas
    • Optimizado para uso eficiente de espacio

    Los archivos se están abriendo en Nemo..."""
        
        dialog = Gtk.MessageDialog(
            transient_for=None,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=mensaje
        )
        dialog.set_default_size(550, 400)
        dialog.run()
        dialog.destroy()


    def limpiar_cache_antiguo(self):
        """Limpia búsquedas temporales manteniendo las más usadas recientemente"""
        try:
            cache_dir = os.path.expanduser("~/.cache/nemo-etiquetas")
            if not os.path.exists(cache_dir):
                return
            
            import time
            import json
            
            ahora = time.time()
            carpeta_info = []
            
            # Recolectar información de todas las carpetas de cache
            for item in os.listdir(cache_dir):
                item_path = os.path.join(cache_dir, item)
                if os.path.isdir(item_path) and item.startswith("busqueda_"):
                    try:
                        # Leer metadata si existe
                        metadata_path = os.path.join(item_path, "metadata.json")
                        if os.path.exists(metadata_path):
                            with open(metadata_path, 'r') as f:
                                metadata = json.load(f)
                                fecha_creacion = metadata.get('fecha_creacion', '')
                        else:
                            fecha_creacion = ''
                        
                        # Obtener tiempo de última modificación (uso)
                        mtime = os.path.getmtime(item_path)
                        dias_antiguedad = (ahora - mtime) / (24 * 60 * 60)
                        
                        carpeta_info.append({
                            'path': item_path,
                            'mtime': mtime,
                            'dias_antiguedad': dias_antiguedad,
                            'metadata': fecha_creacion,
                            'nombre': item
                        })
                        
                    except Exception as e:
                        print(f"❌ Error procesando {item}: {e}")
            
            # Ordenar por antigüedad (más antiguas primero)
            carpeta_info.sort(key=lambda x: x['mtime'])
            
            # Mantener máximo 10 carpetas y eliminar las > 30 días
            max_carpetas = 10
            eliminadas = 0
            
            for i, info in enumerate(carpeta_info):
                if i < len(carpeta_info) - max_carpetas or info['dias_antiguedad'] > 30:
                    try:
                        import shutil
                        shutil.rmtree(info['path'])
                        eliminadas += 1
                        print(f"🗑️ Limpiada carpeta cache: {info['nombre']} ({info['dias_antiguedad']:.1f} días)")
                    except Exception as e:
                        print(f"❌ Error limpiando {info['nombre']}: {e}")
            
            if eliminadas > 0:
                print(f"📊 Cache limpiado: {eliminadas} carpetas eliminadas")
                
        except Exception as e:
            print(f"❌ Error en limpiar_cache_antiguo: {e}")
