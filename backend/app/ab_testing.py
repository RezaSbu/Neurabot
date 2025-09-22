import random
import hashlib
from typing import Dict, Any, Optional

class ABTesting:
    def __init__(self):
        self.experiments = {
            "retrieval_method": {
                "A": "vector_search",
                "B": "hybrid_search"
            },
            "model_selection": {
                "A": "fixed_model",
                "B": "adaptive_model"
            },
            "response_generation": {
                "A": "standard",
                "B": "with_reflection"
            }
        }

    def get_variant(self, experiment_name: str, user_id: str = None) -> str:
        """تخصیص کاربر به گروه A یا B"""
        if user_id:
            # استفاده از هش برای تخصیص ثابت
            hash_value = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
            if hash_value % 100 < 50:
                return "A"
            else:
                return "B"
        else:
            return random.choice(["A", "B"])

    def get_config(self, experiment_name: str, variant: str) -> Any:
        """دریافت پیکربندی برای یک آزمایش و گروه خاص"""
        return self.experiments.get(experiment_name, {}).get(variant)

    async def record_experiment_result(self, experiment_name: str, variant: str, metric_name: str, value: float):
        """ثبت نتیجه آزمایش"""
        await metrics_collector.record_metric(
            f"ab_test:{experiment_name}:{variant}:{metric_name}",
            value,
            {"experiment": experiment_name, "variant": variant}
        )

ab_testing = ABTesting()