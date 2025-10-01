import sqlite3
import os
from pathlib import Path

class GestorEtiquetasSQLite:
    def __init__(self):
        self.db_path = Path.home() / '.local' / 'share' / 'nemo-etiquetas' / 'etiquetas.db'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.inicializar_db()
    
    def inicializar_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS archivos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ruta TEXT UNIQUE NOT NULL,
                    ultima_modificacion REAL NOT NULL
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS etiquetas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE NOT NULL,
                    color TEXT DEFAULT '#3498db'
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS archivo_etiqueta (
                    archivo_id INTEGER,
                    etiqueta_id INTEGER,
                    PRIMARY KEY (archivo_id, etiqueta_id),
                    FOREIGN KEY (archivo_id) REFERENCES archivos(id) ON DELETE CASCADE,
                    FOREIGN KEY (etiqueta_id) REFERENCES etiquetas(id) ON DELETE CASCADE
                )
            ''')
            
            # Índices para búsquedas rápidas
            conn.execute('CREATE INDEX IF NOT EXISTS idx_archivo_ruta ON archivos(ruta)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_etiqueta_nombre ON etiquetas(nombre)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_archivo_etiqueta_a ON archivo_etiqueta(archivo_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_archivo_etiqueta_e ON archivo_etiqueta(etiqueta_id)')
            
            conn.commit()
    
    def _obtener_o_crear_archivo(self, conn, ruta_archivo):
        """Obtiene ID de archivo o lo crea si no existe"""
        cursor = conn.execute(
            'SELECT id FROM archivos WHERE ruta = ?',
            (ruta_archivo,)
        )
        resultado = cursor.fetchone()
        
        if resultado:
            return resultado[0]
        else:
            cursor = conn.execute(
                'INSERT INTO archivos (ruta, ultima_modificacion) VALUES (?, ?)',
                (ruta_archivo, os.path.getmtime(ruta_archivo))
            )
            return cursor.lastrowid

    def _obtener_o_crear_etiqueta(self, conn, nombre_etiqueta):
        """Obtiene ID de etiqueta o la crea si no existe"""
        cursor = conn.execute(
            'SELECT id FROM etiquetas WHERE nombre = ?',
            (nombre_etiqueta,)
        )
        resultado = cursor.fetchone()
        
        if resultado:
            return resultado[0]
        else:
            cursor = conn.execute(
                'INSERT INTO etiquetas (nombre) VALUES (?)',
                (nombre_etiqueta,)
            )
            return cursor.lastrowid

    def agregar_etiquetas(self, ruta_archivo, etiquetas):
        """Añade etiquetas a un archivo"""
        print(f"💾 Gestor: Guardando {len(etiquetas)} etiquetas para {ruta_archivo}")
        
        with sqlite3.connect(self.db_path) as conn:
            # Primero limpiar etiquetas existentes para este archivo
            archivo_id = self._obtener_o_crear_archivo(conn, ruta_archivo)
            
            # Eliminar relaciones existentes
            conn.execute('DELETE FROM archivo_etiqueta WHERE archivo_id = ?', (archivo_id,))
            
            # Añadir nuevas etiquetas
            for etiqueta_nombre in etiquetas:
                etiqueta_id = self._obtener_o_crear_etiqueta(conn, etiqueta_nombre)
                
                # Relacionar archivo con etiqueta
                conn.execute(
                    'INSERT OR IGNORE INTO archivo_etiqueta VALUES (?, ?)',
                    (archivo_id, etiqueta_id)
                )
                print(f"  ✅ Etiqueta añadida: {etiqueta_nombre}")
            
            conn.commit()
        print("💾 Gestor: Guardado completado")

    def obtener_etiquetas_archivo(self, ruta_archivo):
        """Obtiene todas las etiquetas de un archivo"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT t.nombre, t.color 
                    FROM etiquetas t
                    JOIN archivo_etiqueta ae ON t.id = ae.etiqueta_id
                    JOIN archivos a ON a.id = ae.archivo_id
                    WHERE a.ruta = ?
                ''', (ruta_archivo,))
                
                return [{'nombre': row[0], 'color': row[1]} for row in cursor]
        except:
            return []

    def obtener_todas_etiquetas(self):
        """Obtiene todas las etiquetas del sistema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT nombre, color FROM etiquetas ORDER BY nombre')
                return [{'nombre': row[0], 'color': row[1]} for row in cursor]
        except:
            return []

    def buscar_por_etiquetas(self, etiquetas, operador='AND'):
        """Busca archivos que tengan ciertas etiquetas"""
        with sqlite3.connect(self.db_path) as conn:
            placeholders = ','.join(['?'] * len(etiquetas))
            
            if operador == 'AND':
                # Archivos que tienen TODAS las etiquetas
                query = f'''
                    SELECT a.ruta 
                    FROM archivos a
                    WHERE (
                        SELECT COUNT(*) 
                        FROM archivo_etiqueta ae 
                        JOIN etiquetas e ON e.id = ae.etiqueta_id 
                        WHERE ae.archivo_id = a.id 
                        AND e.nombre IN ({placeholders})
                    ) = ?
                '''
                cursor = conn.execute(query, etiquetas + [len(etiquetas)])
            
            else:  # OR - Archivos que tienen AL MENOS UNA etiqueta
                query = f'''
                    SELECT DISTINCT a.ruta 
                    FROM archivos a
                    JOIN archivo_etiqueta ae ON a.id = ae.archivo_id
                    JOIN etiquetas e ON e.id = ae.etiqueta_id
                    WHERE e.nombre IN ({placeholders})
                '''
                cursor = conn.execute(query, etiquetas)
            
            return [row[0] for row in cursor]

    def limpiar_archivos_inexistentes(self):
        """Elimina archivos que ya no existen del sistema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT id, ruta FROM archivos')
            for archivo_id, ruta in cursor:
                if not os.path.exists(ruta):
                    conn.execute('DELETE FROM archivos WHERE id = ?', (archivo_id,))
            conn.commit()
    
    def obtener_todas_etiquetas_archivo(self, ruta_archivo):
        """Obtiene todas las etiquetas de un archivo con mejor manejo de errores"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT t.nombre, t.color 
                    FROM etiquetas t
                    JOIN archivo_etiqueta ae ON t.id = ae.etiqueta_id
                    JOIN archivos a ON a.id = ae.archivo_id
                    WHERE a.ruta = ?
                ''', (ruta_archivo,))
                
                resultado = [{'nombre': row[0], 'color': row[1]} for row in cursor]
                print(f"🔍 Obtenidas {len(resultado)} etiquetas para {os.path.basename(ruta_archivo)}")
                return resultado
        except Exception as e:
            print(f"❌ Error obteniendo etiquetas: {e}")
            return []
