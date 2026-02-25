# Operacion local y acceso remoto

Guia practica para operar Gym Tracker en local, medir recursos y abrir acceso remoto seguro.

## 1) Receta Docker opcional

Nota: Docker es opcional. El flujo principal del proyecto sigue siendo Python local.

### 1.1 Dockerfile minimo

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir flask werkzeug
EXPOSE 5050
ENV TRACKER_HOST=0.0.0.0
ENV TRACKER_PORT=5050
CMD ["python", "app.py"]
```

### 1.2 Build y run

```bash
docker build -t gym-tracker:local .
docker run --rm -p 5050:5050 -v "$PWD/static/uploads:/app/static/uploads" -v "$PWD/tracker.db:/app/tracker.db" gym-tracker:local
```

## 2) Perfilado rapido CPU/RAM

Medicion de referencia tomada el 2026-02-16 en entorno local, levantando la app en puerto temporal y haciendo 200 lecturas a `/api/state?limit=30`.

- RSS base: `46788 KB` (~45.7 MB)
- RSS tras carga: `48264 KB` (~47.1 MB)
- CPU instantaneo base: `3.3%`
- CPU instantaneo tras carga: `1.7%`

Interpretacion rapida:
- El consumo de RAM se mantuvo bajo y estable (subida aproximada +1.4 MB).
- CPU sin picos sostenidos en una carga de lectura corta.

## 3) Tailscale seguro (uso personal)

### 3.1 Correr app en IP Tailscale

```bash
cd /ruta/a/gymtracker
source .venv/bin/activate
TRACKER_HOST=<TU_IP_TAILSCALE_PC> TRACKER_PORT=5050 python app.py
```

### 3.2 ACL minima recomendada (grants)

```json
{
  "grants": [
    {
      "src": ["<IP_TAILSCALE_CELULAR>"],
      "dst": ["<IP_TAILSCALE_PC>"],
      "ip": ["tcp:5050"]
    }
  ],
  "ssh": []
}
```

### 3.3 Capa app (auth local)

Recomendado para cerrar acceso incluso dentro de la red Tailscale:

- `TRACKER_AUTH_ENABLED=1`
- `TRACKER_AUTH_PASSWORD_HASH=scrypt:...`
- `TRACKER_SECRET_KEY=<valor_aleatorio_largo>`

## 4) Hosting compartido: limites reales

- En hosting compartido tipo Bluehost, Flask persistente y workers custom suelen estar limitados.
- Para este proyecto local-first, Tailscale suele ser opcion mas simple y controlable.
- Si en futuro publicas online, evaluar VPS/Platform-as-a-Service en lugar de shared hosting clasico.

## 5) Checklist operativo rapido

1. Verifica que la app responda (`/` y `/api/state?limit=1`).
2. Comprueba login si auth esta activo.
3. Haz backup antes de cambios grandes.
4. Si algo falla, usa `Reportar bug` desde el footer y conserva ese bloque diagnostico.
