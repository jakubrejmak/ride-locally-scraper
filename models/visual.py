from typing import Literal, TypedDict


class Point(TypedDict):
    x: float
    y: float


class Square(TypedDict):
    p1: Point
    p2: Point


Direction = Literal["horizontal", "vertical"]