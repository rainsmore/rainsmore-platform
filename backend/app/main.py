from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os, random, xarray as xr
from datetime import datetime

app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Templates et fichiers statiques
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "..", "static")), name="static")

# Dossier des fichiers NetCDF
DATA_DIR = os.path.join(BASE_DIR, "data")
if not os.path.exists(DATA_DIR):
    raise RuntimeError(f"Dossier de données introuvable : {DATA_DIR}")

files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith(".nc")])
if not files:
    raise RuntimeError(f"Aucun fichier .nc trouvé dans {DATA_DIR}")

# Lecture des fichiers NetCDF
def read_raincells(nc_path, min_mm=0.0, max_mm=9999.0, max_points=200):
    try:
        with xr.open_dataset(nc_path) as ds:
            if "Rainfall" not in ds.variables:
                return [], None
            rain = ds["Rainfall"].values
            lats = ds["lat"].values
            lons = ds["lon"].values
            timestamp = str(ds.time.values[0])[:19]
            points = []
            for i in range(len(lats)):
                for j in range(len(lons)):
                    value = float(rain[0, i, j])
                    if min_mm <= value <= max_mm:
                        points.append({
                            "lat": float(lats[i]),
                            "lon": float(lons[j]),
                            "mm": round(value, 2)
                        })
            # Limiter le nombre de points
            if len(points) > max_points:
                points = random.sample(points, max_points)
            return points, timestamp
    except Exception as e:
        print(f"Erreur lecture NetCDF : {e}")
        return [], None

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/map", response_class=HTMLResponse)
async def map_page(request: Request):
    return templates.TemplateResponse("map.html", {"request": request})

@app.get("/raincells")
async def raincells(min_mm: float = 0.0, max_mm: float = 9999.0):
    try:
        filename = random.choice(files)
        file_path = os.path.join(DATA_DIR, filename)
        data, timestamp = read_raincells(file_path, min_mm, max_mm)
        return {
            "file": filename,
            "timestamp": timestamp,
            "data": data
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})