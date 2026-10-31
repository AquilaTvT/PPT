"""Assemble every section into one Edit."""
import importlib

from . import core
from .edit import Edit

SECTIONS = ['intro', 'hook', 'chorus1', 'verse', 'chorus2', 'bridge1', 'chorus3', 'bridge2', 'chorus4', 'outro']


def _post(img, t, fi):
    return core.finish(img, fi, paper=0.05, grain=0.0, vignette=24)


def build(sections=None):
    shots, trans = [], {}
    for name in sections or SECTIONS:
        try:
            m = importlib.import_module(f'.shots.{name}', __package__)
        except ModuleNotFoundError as e:
            if f'shots.{name}' in str(e):
                continue
            raise
        for sh, tr in m.shots():
            shots.append(sh)
            trans[len(shots) - 1] = tr
    return Edit(shots, trans, post=_post)
