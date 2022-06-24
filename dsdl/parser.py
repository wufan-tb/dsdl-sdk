import click
from abc import ABC, abstractmethod
from yaml import load as yaml_load
from .exception import StructHasDefinedError, DefineSyntaxError, DefineTypeError
import networkx as nx
from .types.field import Field
from .types.struct import Struct

try:
    from yaml import CSafeLoader as YAMLSafeLoader
except ImportError:
    from yaml import SafeLoader as YAMLSafeLoader


class Parser(ABC):
    @abstractmethod
    def parse(self, input_file):
        pass

    @abstractmethod
    def generate(self, output_file):
        pass

    def process(self, input_file, output_file):
        self.parse(input_file)
        self.generate(output_file)


class DSDLParser(Parser):
    def __init__(self):
        self.define_map = dict()
        self.TYPES_WITHOUT_PARS = [
            "Bool",
            "Num",
            "Int",
            "Str",
            "Coord",
            "Coord3D",
            "Interval",
            "BBox",
            "Polygon",
            "Image",
        ]
        self.TYPES_WITH_PARS = ["Date", "Label", "Time"]
        self.TYPES_WITH_PARS_SP = ["List"]

    def parse(self, input_file):
        with open(input_file, "r") as f:
            desc = yaml_load(f, Loader=YAMLSafeLoader)

        for define in desc["defs"].items():
            define_name = define[0]
            define_type = define[1]["$def"]
            if not define_name.isidentifier():
                continue
            if define_name in self.define_map:
                raise StructHasDefinedError(f"{define_name} has defined.")

            define_info = {"name": define_name}
            if define_type == "struct":
                define_info["type"] = "struct"
                define_info["field_list"] = []
                for raw_field in define[1]["$fields"].items():
                    if not raw_field[0].isidentifier():
                        continue
                    define_info["field_list"].append(
                        {"name": raw_field[0], "type": self.parse_struct_field(raw_field[1].replace(" ", "")), }
                    )

            if define_type == "class_domain":
                define_info["type"] = "class_domain"
                define_info["class_list"] = []
                for class_name in define[1]["classes"]:
                    if not class_name.isidentifier():
                        continue
                    define_info["class_list"].append(
                        {"name": class_name, }
                    )

            self.define_map[define_info["name"]] = define_info

    def generate(self, output_file):
        # WIP: check define cycles.
        define_graph = nx.DiGraph()
        define_graph.add_nodes_from(self.define_map.keys())
        for key, val in self.define_map.items():
            if val["type"] != "struct":
                continue
            for field in val["field_list"]:
                for k in self.define_map.keys():
                    if k in field["type"]:
                        define_graph.add_edge(k, key)
        if not nx.is_directed_acyclic_graph(define_graph):
            raise "define cycle found."

        with open(output_file, "w") as of:
            print("# Generated by the dsdl parser. DO NOT EDIT!\n", file=of)
            print("from dsdl.types import *\nfrom enum import Enum\n\n", file=of)
            ordered_keys = list(nx.topological_sort(define_graph))
            for idx, key in enumerate(ordered_keys):
                val = self.define_map[key]
                if val["type"] == "struct":
                    print(f"class {key}(Struct):", file=of)
                    for field in val["field_list"]:
                        print(f"""    {field["name"]} = {field["type"]}""", file=of)
                if val["type"] == "class_domain":
                    print(f"class {key}(Enum):", file=of)
                    for item in val["class_list"]:
                        class_name = item["name"]
                        print(f'''    {class_name.upper()} = "{class_name}"''', file=of)
                if idx != len(ordered_keys) - 1:
                    print("\n", file=of)

    def parse_list_filed(self, raw: str) -> str:
        """
        处理List类型的field
        """
        def sanitize_etype(val: str) -> str:
            """
            验证List类型中的etype是否存在（必须存在）且是否为合法类型
            """
            return self.parse_struct_field(val)

        def all_subclasses(cls):
            """
            返回某个类的所有子类：like[<class '__main__.Bar'>, <class '__main__.Baz'>...]
            """
            return cls.__subclasses__() + [g for s in cls.__subclasses__() for g in all_subclasses(s)]

        def rreplace(s, old, new, occurrence):
            """
            从右向左的替换函数，类似replace,不过是反着的
            """
            li = s.rsplit(old, occurrence)
            return new.join(li)

        def sanitize_ordered(val: str) -> str:
            if val.lower() in ["true", "false"]:
                if val.lower() == "true":
                    return "True"
                else:
                    return "False"
            else:
                raise DefineSyntaxError(f"invalid value {val} in ordered of List {raw}.")

        field_type = "List"

        raw = rreplace(raw.replace(f"{field_type}[", "", 1), "]", "", 1)
        param_list = raw.split(",")
        ele_type, ordered = None, None
        if len(param_list) == 2:
            ele_type = param_list[0]
            ordered = param_list[1]
        elif len(param_list) == 1:
            ele_type = param_list[0]
        else:
            raise DefineSyntaxError(f"invalid parameters {raw} in List.")

        ele_type = ele_type.split("=")
        if len(ele_type) == 2:
            if ele_type[0].strip() != "etype":
                raise DefineSyntaxError(f"List types must contains parameters `etype`.")
            ele_type = ele_type[1]
        elif len(ele_type) == 1:
            ele_type = ele_type[0]
        else:
            raise DefineSyntaxError(f"invalid parameters {raw} in List.")

        res = field_type + "Field("
        if ele_type:
            ele_type = sanitize_etype(ele_type)
            res += "ele_type=" + ele_type
        else:
            raise DefineSyntaxError(f"List types must contains parameters `etype`.")
        if ordered:
            ordered = ordered.split("=")[-1]
            ordered = sanitize_ordered(ordered)
            res += ", ordered=" + ordered
        return res + ")"

    @staticmethod
    def parse_struct_field_with_params(raw: str) -> str:  # Label, Time, Date类型的解析器
        def sanitize_dom(val: str) -> str:
            if not val.isidentifier():
                raise DefineSyntaxError(f"invalid dom: {val}")
            return val

        def sanitize_fmt(val: str) -> str:
            val = val.strip("\"'")
            return f'"{val}"'

        field_map = {
            "Label": {"dom": sanitize_dom},
            "Date": {"fmt": sanitize_fmt},
            "Time": {"fmt": sanitize_fmt},
        }
        field_type = ""
        for k in field_map.keys():
            if raw.startswith(k):
                field_type = k
        if field_type == "":
            raise "Unknown field"

        raw = raw.replace(f"{field_type}[", "").replace("]", "")
        param_list = raw.split(",")
        valid_param_list = []
        for param in param_list:
            parts = param.split("=")
            # 需要考虑参数省略的情况，因为dom经常省略
            if len(parts) == 2:
                field_para = parts[0]
                field_var = parts[1]
            elif len(parts) == 1:
                field_para = next(iter(field_map[field_type]))
                field_var = parts[0]
            else:
                raise DefineSyntaxError(f"invalid parameters {raw} in List.")
            sanitized = field_map[field_type][field_para](field_var)
            valid_param_list.append(f"{field_para}={sanitized}")
        return field_type + "Field(" + ",".join(valid_param_list) + ")"

    def parse_struct_field(self, raw_field_type: str) -> str:
        if raw_field_type in self.TYPES_WITHOUT_PARS:
            return raw_field_type + "Field()"
        elif raw_field_type.startswith(tuple(self.TYPES_WITH_PARS_SP)):
            return self.parse_list_filed(raw_field_type)
        elif raw_field_type.startswith(tuple(self.TYPES_WITH_PARS)):
            return DSDLParser.parse_struct_field_with_params(raw_field_type)
        else:
            raise DefineTypeError(f"No type {raw_field_type} in DSDL.")


@click.command()
@click.option(
    "-y", "--yaml", "dsdl_yaml", type=str, required=True,
)
def parse(dsdl_yaml):
    output_file = dsdl_yaml.replace(".yaml", ".py")
    dsdl_parser = DSDLParser()
    dsdl_parser.process(dsdl_yaml, output_file)
