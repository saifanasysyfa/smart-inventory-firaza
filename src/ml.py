from pathlib import Path
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score,classification_report,confusion_matrix,f1_score
from sklearn.model_selection import train_test_split

ROOT=Path(__file__).resolve().parents[1]
MODEL_PATH=ROOT/"models"/"stock_classifier.joblib"
LABELS={0:"Safe",1:"Need Attention",2:"Restock Priority"}
FEATURES=["current_stock","minimum_stock","usage_7d","usage_30d","lead_time_days"]

def rule_label(stock,minimum,usage7,usage30,lead):
    daily=usage30/30
    days_cover=stock/max(daily,0.1)
    ratio=stock/max(minimum,1)
    if stock<=minimum or days_cover<=lead: return 2
    if ratio<=1.5 or days_cover<=lead*2: return 1
    return 0

def generate_training_data(n=3000,seed=42):
    rng=np.random.default_rng(seed)
    minimum=rng.integers(5,101,n); lead=rng.integers(1,15,n)
    usage30=rng.integers(0,181,n); usage7=np.maximum(0,np.round(usage30/30*7*rng.uniform(.5,1.8,n)))
    stock=rng.integers(0,251,n)
    y=np.array([rule_label(*v) for v in zip(stock,minimum,usage7,usage30,lead)])
    X=np.column_stack([stock,minimum,usage7,usage30,lead])
    return X,y

def train_model():
    X,y=generate_training_data()
    Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=.2,random_state=42,stratify=y)
    model=RandomForestClassifier(n_estimators=160,max_depth=12,class_weight="balanced",random_state=42)
    model.fit(Xtr,ytr); pred=model.predict(Xte)
    MODEL_PATH.parent.mkdir(parents=True,exist_ok=True); joblib.dump(model,MODEL_PATH)
    return model, Xte,yte,pred

def load_model():
    if not MODEL_PATH.exists(): train_model()
    return joblib.load(MODEL_PATH)

def classify_inventory(stock,minimum,usage7,usage30,lead):
    model=load_model(); x=np.array([[stock,minimum,usage7,usage30,lead]],dtype=float)
    pred=int(model.predict(x)[0]); probs=model.predict_proba(x)[0]
    return {"status":LABELS[pred],"confidence":float(probs[pred]),"days_of_cover":round(float(stock/max(usage30/30,.1)),1)}

def evaluate_model():
    _,Xte,yte,pred=train_model()
    names=[LABELS[i] for i in range(3)]
    report=classification_report(yte,pred,labels=[0,1,2],target_names=names,output_dict=True,zero_division=0)
    return {"accuracy":float(accuracy_score(yte,pred)),"macro_f1":float(f1_score(yte,pred,average="macro")),"test_samples":int(len(yte)),"report":report,"confusion_matrix":confusion_matrix(yte,pred,labels=[0,1,2]).tolist(),"labels":names,"model_path":str(MODEL_PATH)}
