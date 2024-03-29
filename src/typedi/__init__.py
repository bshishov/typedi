__version_info__ = 0, 6, 0
__version__ = ".".join(map(str, __version_info__))

from typedi.container import Container
from typedi.resolution import ResolutionError
from typedi.object_proxy import ObjectProxy

__all__ = [
    "Container",
    "ResolutionError",
    "ObjectProxy",
]
