# Dashboard empresarial KOBO + Streamlit

Aplicación web pública para consultar resultados empresariales usando nombre de empresa + código de acceso. La app está pensada para leer datos desde KOBO, Excel, CSV o una URL de exportación.

## 1. Archivos incluidos

- `app.py`: aplicación principal en Streamlit.
- `requirements.txt`: dependencias para Streamlit Cloud.
- `.streamlit/config.toml`: estilo visual de la app.
- `.streamlit/secrets.toml.example`: ejemplo de configuración privada.
- `scripts/generar_codigos.py`: utilidad local para crear códigos de acceso por encuesta.

## 2. Fuente de datos recomendada

La app puede funcionar de dos maneras:

### Opción A: KOBO directo

Configurar estos secretos en Streamlit Cloud:

```toml
KOBO_DATA_URL = "https://eu.kobotoolbox.org/api/v2/assets/.../data.xlsx"
KOBO_TOKEN = "PEGAR_TOKEN_DE_KOBO_AQUI"
```

El token se envía como encabezado:

```text
Authorization: Token <token>
```

### Opción B: Excel/CSV manual

Mientras se valida la estructura, se puede entrar a la app y cargar un Excel o CSV desde la barra lateral.

## 3. Columnas necesarias

La app intenta detectar las columnas automáticamente, pero para evitar errores se recomienda tener:

| Uso | Nombre recomendado |
|---|---|
| Empresa | `nombre_empresa` |
| Código de acceso | `codigo_acceso` |
| Fecha de envío | `_submission_time` |
| Calificación general | `puntaje_general` |
| Nivel de avance | `nivel_avance` |
| Lectura para plan | `lectura_para_plan` |

Si las columnas tienen otros nombres, se pueden configurar en secretos:

```toml
COMPANY_COLUMN = "nombre real de la columna"
ACCESS_CODE_COLUMN = "nombre real de la columna"
GENERAL_SCORE_COLUMN = "nombre real de la columna"
LEVEL_COLUMN = "nombre real de la columna"
READING_COLUMN = "nombre real de la columna"
```

Para controlar los puntajes por principio/dimensión:

```toml
SCORE_COLUMNS = "puntaje_p1,puntaje_p2,puntaje_p3,puntaje_p4,puntaje_p5,puntaje_p6,puntaje_p7"
```

## 4. Publicación gratis en Streamlit Community Cloud

1. Crear un repositorio en GitHub.
2. Subir estos archivos al repositorio.
3. Entrar a Streamlit Community Cloud.
4. Crear una nueva app apuntando a `app.py`.
5. En `Advanced settings` o `Secrets`, pegar las variables privadas del archivo `.streamlit/secrets.toml.example`.
6. Desplegar la app.

No subir un archivo `secrets.toml` real con el token de KOBO al repositorio.

## 5. Seguridad mínima

- La vista pública solo muestra agregados generales.
- La vista empresarial exige nombre de empresa + código.
- La columna del código se oculta en la vista filtrada.
- El token de KOBO debe guardarse en secretos, no en el código.

Nota: esto no sustituye un sistema formal de autenticación empresarial. Para un nivel más alto de seguridad se recomienda agregar login con cuentas o mover la validación a una API/backend propio.

## 6. Problema frecuente con enlaces KOBO

Si una URL de KOBO devuelve `404`, `401` o `403`, normalmente significa que:

- el enlace no es público;
- el export cambió o ya no existe;
- falta token de KOBO;
- el enlace solo funciona con sesión iniciada en el navegador;
- se requiere una exportación síncrona/named export activa.

En ese caso, configure `KOBO_TOKEN` y confirme que la URL corresponde al export vigente.
