from pathlib import Path

from appdirs import user_config_dir

from src.settings import LanguageLearningMethodSettings


class ConfigManager:
    def __init__(self) -> None:
        self.config_dir = Path(user_config_dir(appname="language-learning-method"))
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True)

    @property
    def settings_path(self) -> Path:
        return self.config_dir / "settings.json"

    def read_settings(self) -> LanguageLearningMethodSettings:
        if not self.settings_path.exists():
            return LanguageLearningMethodSettings()

        with open(self.config_dir / "settings.json", "r") as file:
            return LanguageLearningMethodSettings.model_validate_json(file.read())

    def write_settings(self, settings: LanguageLearningMethodSettings) -> None:
        with open(self.settings_path, "w") as file:
            file.write(settings.model_dump_json(indent=4))
