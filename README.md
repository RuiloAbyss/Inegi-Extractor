# INEGI Extractor

Proyecto de extracción y análisis de datos INEGI con interfaz gráfica en Python.

## ¿De qué se trata?

`inegi_extractor` es una aplicación de escritorio que permite cargar matrices de datos del INEGI, limpiar y preparar los datos geográficos, y realizar análisis demográficos y económicos. El software está diseñado para trabajar con archivos de Censos de Población y Censos Económicos/SAIC en formatos CSV y Excel.

La aplicación identifica automáticamente si el archivo es de población o económico, extrae códigos y municipios, y construye tableros de análisis que ayudan a comparar datos por estado y municipio.

## Tecnologías usadas

- Python 3.x
- Pandas
- Openpyxl
- Tkinter

## Estructura del proyecto

- `main.py`: punto de entrada de la aplicación.
- `requirements.txt`: dependencias necesarias.
- `core/file_manager.py`: lógica de lectura de archivos, parser de datos y apertura de archivos en el sistema.
- `processors/`: módulo con las transformaciones y cálculos principales.
  - `location_manager.py`: limpieza de códigos geográficos y extracción de estados/municipios.
  - `working_age_calculator.py`: cálculo de población por rango etario.
  - `economic_calculator.py`: análisis jerárquico de datos económicos y extracción de municipios/años.
  - `cluster_calculator.py`: cálculo de clusters e indicadores económicos.
  - `population_interpolator.py`: extrapolación de población entre años usando crecimiento lineal/exponencial.
- `ui/main_window.py`: interfaz gráfica con Tkinter.
- `resources/`: ejemplos o datos de prueba.

## Requisitos

- Python 3.8 o superior
- Las siguientes librerías Python están en `requirements.txt`:
  - `pandas`
  - `openpyxl`

## Instalación

1. Abre una terminal en la carpeta del proyecto:

```powershell
cd d:\ITT\Delfin2026\Project\inegi_extractor
```

2. Instala las dependencias:

```powershell
pip install -r requirements.txt
```

## Cómo usar el software

### Paso 1: Ejecutar la aplicación

Ejecuta el archivo principal:

```powershell
python main.py
```

Se abrirá la ventana de la aplicación `INEGI Data Processor - Análisis de Clusters y CAGR`.

### Paso 2: Cargar los archivos INEGI

En la sección `1. Carga de Matrices de Datos`:

- Haz clic en `Añadir Archivo INEGI`.
- Selecciona un archivo `.csv`, `.xlsx` o `.xls` con datos del INEGI.
- La aplicación detectará si el archivo es de `Población` o `Económico`.
- Verás un estado de carga en la interfaz y podrás abrir el archivo con `👁 Último` o `👁 Ver`.

### Paso 3: Preparar el entorno y analizar

1. En la sección `2. Preparación de Entorno`: haz clic en `Preparar Entorno`.
   - Se limpia la información geográfica.
   - Se cruza el catálogo de estados/municipios.
   - Se construyen las pestañas de análisis.

2. En la sección `3. Filtro Geográfico Maestro`:
   - Selecciona el `Estado` deseado.
   - Opcionalmente, selecciona el `Municipio`.
   - Haz clic en `Analizar y Construir`.

3. Navega entre las pestañas:
   - `Análisis Demográfico` para datos poblacionales.
   - `Censos Económicos` para datos económicos.
   - `Cálculos (Clusters)` para resultados de clusterización.

## Descripción de los pasos principales

1. **Carga de archivos**
   - El componente `core/file_manager.py` detecta automáticamente el tipo de archivo.
   - `PopulationParser` lee matrices de población.
   - `EconomicParser` lee matrices económicas/SAIC.

2. **Preparación del entorno**
   - `location_manager.py` limpia códigos y nombres de estado/municipio.
   - Extrae entidades y municipios con códigos de 2 y 5 dígitos.
   - Cuando hay datos de población y económicos, el modo estricto puede cruzar solo intersecciones válidas.

3. **Análisis y cálculo**
   - `working_age_calculator.py` calcula población por rangos de edad en cada municipio.
   - `economic_calculator.py` extrae jerarquías económicas y valores de unidades económicas y personal ocupado.
   - `cluster_calculator.py` calcula indicadores `Kc`, `Ks`, `Ki` y determina si hay cluster.
   - `population_interpolator.py` extrapola resultados entre años para proyecciones.

## Archivos de ejemplo

- `resources/INEGI_exporta_JALISCO_2010.csv`
- `resources/INEGI_exporta_JALISCO_2020.csv`
- `resources/SAIC_Exporta_2026627_131852686 TEXTIL-JALISCO.csv`

## Notas importantes

- Los archivos deben contener columnas con encabezados reconocibles de INEGI, como `H001A`, `ACTIVIDAD ECON`, `UE`, `AÑO CENSAL` o columnas de edad.
- Las tablas deben tener códigos de entidad municipal con números claros para que la limpieza geográfica funcione correctamente.
- Si la aplicación no reconoce la estructura, mostrará un error indicando que el formato es incompatible.
