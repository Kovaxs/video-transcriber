"""Connect approved backend identifiers to their speech adapters."""

from collections.abc import Mapping
from types import MappingProxyType

from video_transcriber.adapters.fermion import FermionAdapter
from video_transcriber.errors import TranscriberError
from video_transcriber.models import BackendId
from video_transcriber.ports import SpeechBackend

_BACKENDS: Mapping[BackendId, SpeechBackend] = MappingProxyType(
    {BackendId.FERMION: FermionAdapter()}
)


def get_backend(backend_id: BackendId) -> SpeechBackend:
    """Return an approved speech adapter without model or network access."""
    try:
        return _BACKENDS[backend_id]
    except KeyError as error:
        raise TranscriberError(
            f"Unsupported speech backend: {backend_id}. "
            "A maintainer must register its adapter."
        ) from error
