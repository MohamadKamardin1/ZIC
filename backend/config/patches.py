from django.template.context import BaseContext


def _patched_base_context_copy(self):
    cls = type(self)
    duplicate = cls.__new__(cls)
    if hasattr(duplicate, '__dict__'):
        duplicate.__dict__.update(self.__dict__)
    duplicate.dicts = self.dicts[:]
    return duplicate


def apply_patches():
    BaseContext.__copy__ = _patched_base_context_copy
