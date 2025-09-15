# TrinityEd_app/utils/risk_calculator.py
class RiskCalculator:
    def __init__(self):
        self.thresholds = self._get_default_thresholds()

    def _get_default_thresholds(self):
        return {
            'attendance': 70,
            'performance': 60,
            'alerts': 5
        }

    # Other methods...