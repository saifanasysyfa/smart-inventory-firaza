import tempfile
from pathlib import Path
import pytest
from src.ml import rule_label,generate_training_data,train_model,classify_inventory

def test_rule_label_priority_when_stock_below_minimum():
    assert rule_label(5,10,4,20,5)==2

def test_rule_label_safe():
    assert rule_label(200,10,2,8,2)==0

def test_training_data_shape():
    X,y=generate_training_data(100)
    assert X.shape==(100,5) and len(y)==100

def test_model_prediction_has_expected_fields():
    result=classify_inventory(5,10,4,20,5)
    assert result['status'] in {'Safe','Need Attention','Restock Priority'}
    assert 0<=result['confidence']<=1
