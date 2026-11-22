from pathlib import Path
import csv,random
from src.db import init_db,seed_if_empty,get_materials,get_usage_features
ROOT=Path(__file__).resolve().parent
init_db(); seed_if_empty()
with (ROOT/'data'/'materials.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f); w.writerow(['sku','material_name','category','unit','current_stock','minimum_stock','lead_time_days','supplier'])
    for m in get_materials(): w.writerow([m['sku'],m['material_name'],m['category'],m['unit'],m['current_stock'],m['minimum_stock'],m['lead_time_days'],m['supplier']])
with (ROOT/'data'/'usage_features.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f); w.writerow(['material_id','usage_7d','usage_30d'])
    for mid,u in get_usage_features().items(): w.writerow([mid,u['usage_7d'],u['usage_30d']])
print('Synthetic demo CSV files generated in data/.')
