# Generated by the dsdl parser. DO NOT EDIT!

from dsdl.types import *
from enum import Enum


class MyClassDom(Enum):
    DOG = "dog"
    CAT = "cat"
    FISH = "fish"
    TIGER = "tiger"


class ImageClassificationSample(Struct):
    i_list = ListField(ele_type=IntField())
    item_list = ListField(ele_type=ListField(ele_type=IntField()), ordered=True)
    image = ImageField()
    label = LabelField(dom=MyClassDom)
    valid = BoolField()
    val = NumField()
    i_val = IntField()
    p = CoordField()
    date = DateField(fmt="%Y-%m-%d")
    label_list = ListField(ele_type=LabelField(dom=MyClassDom))
