"""Simple modeling test script to test probability engine."""

import numpy as np
from polysniff.model import ProbabilityEngine, FeatureExtractor
from polysniff.strategy import EVCalculator


def create_mock_market_data() -> dict:
    """Create mock market data for testing."""
    return {
        "market_id": "test_market_1",
        "yes_price": 0.65,
        "no_price": 0.35,
        "volume_24h": 10000.0,
        "liquidity": 5000.0,
        "timestamp": "2024-01-01T00:00:00Z",
    }


def test_feature_extraction():
    """Test feature extraction."""
    print("=" * 60)
    print("Testing Feature Extraction")
    print("=" * 60)
    
    extractor = FeatureExtractor(lookback_hours=24)
    market_data = create_mock_market_data()
    
    feature_set = extractor.extract(market_data)
    
    if feature_set:
        print(f"\n✓ Feature extraction successful")
        print(f"  Market ID: {feature_set.market_id}")
        print(f"  Features shape: {feature_set.features.shape}")
        print(f"  Feature names: {feature_set.feature_names}")
        print(f"  Feature values: {feature_set.features}")
        return feature_set
    else:
        print("\n✗ Feature extraction failed")
        return None


def test_probability_engine(feature_set):
    """Test probability engine."""
    print("\n" + "=" * 60)
    print("Testing Probability Engine")
    print("=" * 60)
    
    engine = ProbabilityEngine()
    
    if feature_set:
        prediction = engine.predict(
            feature_set.market_id,
            feature_set.features,
            feature_set.timestamp
        )
        
        if prediction:
            print(f"\n✓ Probability prediction successful")
            print(f"  Market ID: {prediction.market_id}")
            print(f"  Fair Probability: {prediction.fair_probability:.4f}")
            print(f"  Confidence: {prediction.confidence:.4f}")
            print(f"  Model Type: {prediction.model_type}")
            return prediction
        else:
            print("\n✗ Probability prediction failed")
            return None
    else:
        print("\n✗ Skipping - no feature set available")
        return None


def test_ev_calculator(prediction, market_data):
    """Test EV calculator."""
    print("\n" + "=" * 60)
    print("Testing EV Calculator")
    print("=" * 60)
    
    calculator = EVCalculator()
    
    if prediction:
        opportunity = calculator.calculate_ev(
            market_data["market_id"],
            prediction.fair_probability,
            market_data["yes_price"],
            market_data["no_price"],
        )
        
        if opportunity:
            print(f"\n✓ EV calculation successful")
            print(f"  Market ID: {opportunity.market_id}")
            print(f"  Side: {opportunity.side}")
            print(f"  Entry Price: {opportunity.entry_price:.4f}")
            print(f"  Fair Prob: {opportunity.fair_probability:.4f}")
            print(f"  Implied Prob: {opportunity.implied_probability:.4f}")
            print(f"  EV %: {opportunity.ev_percentage:.2f}%")
            print(f"  Kelly Fraction: {opportunity.kelly_fraction:.4f}")
            print(f"  Position Size: {opportunity.position_size:.4f}")
            return opportunity
        else:
            print("\n✗ No EV opportunity (below threshold)")
            return None
    else:
        print("\n✗ Skipping - no prediction available")
        return None


def main():
    """Run all modeling tests."""
    print("\n" + "=" * 60)
    print("PolySniff Modeling Test Suite")
    print("=" * 60)
    
    # Test 1: Feature extraction
    feature_set = test_feature_extraction()
    
    # Test 2: Probability engine
    prediction = test_probability_engine(feature_set)
    
    # Test 3: EV calculator
    market_data = create_mock_market_data()
    opportunity = test_ev_calculator(prediction, market_data)
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Feature Extraction: {'✓' if feature_set else '✗'}")
    print(f"Probability Engine: {'✓' if prediction else '✗'}")
    print(f"EV Calculator: {'✓' if opportunity else '✗'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
