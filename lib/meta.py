from enum import Enum


class DevType(Enum):
    ALPHA = "alpha"
    BETA = "beta"
    RELEASE = "release"


class Version(Enum):
    PATCH = 0
    MINOR = 4
    MAJOR = 0
    DEV = DevType.ALPHA

    def __str__(self):
        return f"{self.MAJOR.value}.{self.MINOR.value}.{self.PATCH.value}-{self.DEV.value.value}"
