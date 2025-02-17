from typing import TypeVar

T = TypeVar("T")  # Declare type variable


def get_all_subclasses(cls: type[T]) -> list[type[T]]:
    all_subclasses = []

    for subclass in cls.__subclasses__():
        all_subclasses.append(subclass)
        all_subclasses.extend(get_all_subclasses(subclass))

    return all_subclasses


def get_subclass(root_class: type[T], child_class_name: str) -> type[T]:
    """Returns the subclass with the given name (any level deep)"""
    for subclass in get_all_subclasses(root_class):
        if subclass.__name__ == child_class_name:
            return subclass
    raise ValueError(f"Unknown subclass: {child_class_name} of {root_class.__name__}")
