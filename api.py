from pathlib import Path
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel,Field
from src.db import init_db,seed_if_empty,get_materials,get_usage_features
from src.ml import classify_inventory

app=FastAPI(title="Smart Inventory Firaza API",version="1.0.0",description="REST inference API for inventory stock classification")
init_db(); seed_if_empty()
class PredictionInput(BaseModel):
    current_stock:float=Field(ge=0); minimum_stock:float=Field(ge=0); usage_7d:float=Field(ge=0); usage_30d:float=Field(ge=0); lead_time_days:int=Field(ge=1)
@app.get("/health")
def health(): return {"status":"ok","service":"Smart Inventory Firaza API"}
@app.post("/predict")
def predict(data:PredictionInput):
    try: return classify_inventory(data.current_stock,data.minimum_stock,data.usage_7d,data.usage_30d,data.lead_time_days)
    except Exception as e: raise HTTPException(status_code=500,detail=str(e))
@app.get("/inventory/predictions")
def inventory_predictions():
    usage=get_usage_features(); out=[]
    for m in get_materials():
        u=usage.get(m['material_id'],{'usage_7d':0,'usage_30d':0})
        out.append({"sku":m['sku'],"material_name":m['material_name'],**classify_inventory(m['current_stock'],m['minimum_stock'],u['usage_7d'],u['usage_30d'],m['lead_time_days'])})
    return {"count":len(out),"items":out}
