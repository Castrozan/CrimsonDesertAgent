from hypothesis import settings

settings.register_profile("without_wall_clock_deadline", deadline=None)
settings.load_profile("without_wall_clock_deadline")
