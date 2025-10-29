from typing import TypeVar, cast

_T = TypeVar('_T')

_instances: dict[type[object], object] = {}
_initialized: set[type[object]] = set()


def singleton(original_cls: type[_T]) -> type[_T]:
    """
    Singleton decorator that ensures only one instance of a class exists.

    Usage:
        @singleton
        class MyClass:
            pass
    """
    original_new = original_cls.__new__
    original_init = original_cls.__init__

    def new_new(cls: type[_T], *args: object, **kwargs: object) -> _T:
        if original_cls not in _instances:
            if original_new is object.__new__:
                instance = original_new(cls)
            else:
                instance = original_new(cls, *args, **kwargs)
            _instances[original_cls] = instance
        return cast(_T, _instances[original_cls])

    def new_init(self: _T, *args: object, **kwargs: object) -> None:
        if original_cls not in _initialized:
            original_init(self, *args, **kwargs)
            _initialized.add(original_cls)

    original_cls.__new__ = new_new  # type: ignore[method-assign,assignment]
    original_cls.__init__ = new_init  # type: ignore[method-assign]
    return original_cls
