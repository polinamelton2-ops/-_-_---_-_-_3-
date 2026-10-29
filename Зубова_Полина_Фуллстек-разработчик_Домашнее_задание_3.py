"""Система доставки."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


# ---------- Доменные исключения ----------
class DeliveryError(Exception):
    """Любая ошибка сценария доставки."""


class MissingProductError(DeliveryError):
    pass


class CapacityError(DeliveryError):
    pass


class UniqueLimitError(DeliveryError):
    pass


# ---------- Базовое хранилище ----------
class Storage(ABC):
    def __init__(self, items: dict, capacity: int):
        self._items = {k: v for k, v in items.items() if v > 0}
        self._capacity = capacity

    @abstractmethod
    def add(self, name: str, amount: int) -> None:
        ...

    @abstractmethod
    def remove(self, name: str, amount: int) -> None:
        ...

    def get_free_space(self) -> int:
        return self._capacity - sum(self._items.values())

    def get_items(self) -> dict:
        return self._items.copy()

    def get_unique_items_count(self) -> int:
        return len(self._items)

    # dunder
    def __len__(self):
        return sum(self._items.values())

    def __contains__(self, name):
        return self._items.get(name, 0) > 0

    def __getitem__(self, name):
        return self._items.get(name, 0)

    def __repr__(self):
        return f"<{type(self).__name__} {self._items} / {self._capacity}>"

    def __str__(self):
        return ", ".join(f"{k}={v}" for k, v in self._items.items()) or "пусто"


class Store(Storage):
    def __init__(self, items: dict, capacity: int = 100):
        super().__init__(items, capacity)

    def add(self, name: str, amount: int) -> None:
        if amount <= 0:
            raise DeliveryError("Количество должно быть > 0.")
        if amount > self.get_free_space():
            raise CapacityError("На складе нет столько свободного места.")
        self._items[name] = self._items.get(name, 0) + amount

    def remove(self, name: str, amount: int) -> None:
        if amount <= 0:
            raise DeliveryError("Количество должно быть > 0.")
        if self._items.get(name, 0) < amount:
            raise MissingProductError(f"На складе недостаточно '{name}'.")
        self._items[name] -= amount
        if not self._items[name]:
            del self._items[name]


class Shop(Storage):
    LIMIT_UNIQUE = 5

    def __init__(self, items: dict, capacity: int = 20):
        super().__init__(items, capacity)

    def add(self, name: str, amount: int) -> None:
        if amount <= 0:
            raise DeliveryError("Количество должно быть > 0.")
        new_product = name not in self._items
        if new_product and self.get_unique_items_count() >= self.LIMIT_UNIQUE:
            raise UniqueLimitError(
                f"В магазине уже {self.LIMIT_UNIQUE} видов товаров."
            )
        if amount > self.get_free_space():
            raise CapacityError("В магазине нет столько свободного места.")
        self._items[name] = self._items.get(name, 0) + amount

    def remove(self, name: str, amount: int) -> None:
        if amount <= 0:
            raise DeliveryError("Количество должно быть > 0.")
        if self._items.get(name, 0) < amount:
            raise MissingProductError(f"В магазине недостаточно '{name}'.")
        self._items[name] -= amount
        if not self._items[name]:
            del self._items[name]


# ---------- Запрос ----------
@dataclass
class Request:
    amount: int
    product: str
    from_point: str
    to_point: str

    @classmethod
    def parse(cls, raw: str) -> "Request":
        tokens = raw.split()
        if len(tokens) != 7:
            raise ValueError("Нужно ровно 7 слов: Доставить N товар из X в Y.")
        verb, amount, product, prep_out, src, prep_in, dst = tokens
        if verb.lower() != "доставить":
            raise ValueError("Запрос должен начинаться со слова 'Доставить'.")
        if prep_out.lower() != "из" or prep_in.lower() != "в":
            raise ValueError("Ожидается 'из ... в ...'.")
        if not amount.isdigit() or int(amount) <= 0:
            raise ValueError("Количество должно быть целым положительным числом.")
        return cls(int(amount), product, src.lower(), dst.lower())

    def __str__(self) -> str:
        return (f"Доставить {self.amount} {self.product} "
                f"из {self.from_point} в {self.to_point}")


# ---------- Сценарий доставки ----------
def make_world():
    store = Store({"печеньки": 10, "собачки": 10, "коробки": 10,
                   "конфеты": 10, "игрушки": 10})
    shop = Shop({"собачки": 2, "коробки": 5})
    return {"склад": store, "магазин": shop}


def validate(storages: dict, req: Request) -> tuple[Storage, Storage]:
    if req.from_point == req.to_point:
        raise DeliveryError("Источник и приёмник совпадают.")
    src = storages.get(req.from_point)
    dst = storages.get(req.to_point)
    if src is None or dst is None:
        raise DeliveryError("Неизвестное хранилище. Допустимы: 'склад', 'магазин'.")
    if req.product not in src:
        raise MissingProductError(
            f"В '{req.from_point}' нет товара '{req.product}'."
        )
    if src[req.product] < req.amount:
        raise MissingProductError(
            f"Не хватает '{req.product}' в '{req.from_point}': "
            f"есть {src[req.product]}, нужно {req.amount}."
        )
    if req.amount > dst.get_free_space():
        raise CapacityError(
            f"В '{req.to_point}' недостаточно места "
            f"(свободно {dst.get_free_space()}, нужно {req.amount})."
        )
    if isinstance(dst, Shop) and req.product not in dst:
        if dst.get_unique_items_count() >= Shop.LIMIT_UNIQUE:
            raise UniqueLimitError(
                f"В магазине уже {Shop.LIMIT_UNIQUE} видов товаров."
            )
    return src, dst


def execute(storages: dict, req: Request) -> None:
    src, dst = validate(storages, req)
    print(f"Курьер забирает {req.amount} {req.product} из {req.from_point}.")
    src.remove(req.product, req.amount)
    print(f"Курьер везёт {req.amount} {req.product} "
          f"из {req.from_point} в {req.to_point}.")
    dst.add(req.product, req.amount)
    print(f"Курьер доставил {req.amount} {req.product} в {req.to_point}.")


def dump(storages: dict) -> None:
    print("\nТекущие запасы:")
    for name, storage in storages.items():
        print(f"  {name.capitalize()}: {storage}")


def main() -> None:
    storages = make_world()
    print("Система доставки. Для выхода введите 'стоп' или 'выход'.")
    while True:
        dump(storages)
        raw = input(
            "\n> Доставить <кол-во> <товар> из <откуда> в <куда>\n"
            "  (стоп/выход — завершить)\n-> "
        ).strip()

        if raw.lower() in {"стоп", "выход"}:
            print("До встречи!")
            return

        try:
            req = Request.parse(raw)
            execute(storages, req)
        except (ValueError, DeliveryError) as exc:
            print(f"Не удалось выполнить: {exc}")
        except Exception as exc:  # защита от непредвиденного
            print(f"Что-то пошло не так: {exc}")


if __name__ == "__main__":
    main()