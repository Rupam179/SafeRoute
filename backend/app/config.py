from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    database_url: str = "postgresql://saferoute:saferoute@db:5432/saferoute"
    osrm_base_url: str = "https://router.project-osrm.org"
    ai_service_url: str = "http://localhost:8500"

    secret_key: str = "change-this-in-production-please"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    weight_road_damage: float = 0.35
    weight_accident: float = 0.30
    weight_safety: float = 0.20
    weight_time_of_day: float = 0.15

    risk_search_radius_m: int = 60
    route_sample_spacing_m: int = 150

    cors_origins_str: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins(self) -> List[str]:
        return [x.strip() for x in self.cors_origins_str.split(",") if x.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
