import pytest
from backend.app.models.bkt import BKTModel

def test_bkt_model_initialization():
    """Test BKT model initialization with default parameters"""
    model = BKTModel()
    assert model.p_init == 0.2
    assert model.p_transit == 0.15
    assert model.p_slip == 0.1
    assert model.p_guess == 0.2
    assert model.mastery_prob == 0.2

def test_bkt_model_update_correct():
    """Test BKT model update with correct answer"""
    model = BKTModel()
    initial_prob = model.get_mastery_prob()
    new_prob = model.update(True)  # Correct answer
    assert new_prob != initial_prob
    assert 0.0 <= new_prob <= 1.0

def test_bkt_model_update_incorrect():
    """Test BKT model update with incorrect answer"""
    model = BKTModel()
    initial_prob = model.get_mastery_prob()
    new_prob = model.update(False)  # Incorrect answer
    assert new_prob != initial_prob
    assert 0.0 <= new_prob <= 1.0

def test_bkt_model_serialization():
    """Test BKT model serialization and deserialization"""
    # Create model with custom parameters
    params = {
        'p_init': 0.3,
        'p_transit': 0.2,
        'p_slip': 0.15,
        'p_guess': 0.25
    }
    model = BKTModel(params)
    
    # Update the model a few times
    model.update(True)
    model.update(False)
    model.update(True)
    
    # Serialize to dict
    model_dict = model.to_dict()
    
    # Deserialize from dict
    restored_model = BKTModel.from_dict(model_dict)
    
    # Check that parameters are preserved
    assert restored_model.p_init == model.p_init
    assert restored_model.p_transit == model.p_transit
    assert restored_model.p_slip == model.p_slip
    assert restored_model.p_guess == model.p_guess
    assert restored_model.mastery_prob == model.mastery_prob

def test_bkt_model_probability_bounds():
    """Test that BKT model keeps probabilities within bounds"""
    model = BKTModel()
    
    # Update many times with correct answers
    for _ in range(100):
        model.update(True)
    
    # Mastery probability should not exceed 1.0
    assert model.get_mastery_prob() <= 1.0
    
    # Update many times with incorrect answers
    for _ in range(100):
        model.update(False)
    
    # Mastery probability should not go below 0.0
    assert model.get_mastery_prob() >= 0.0