"""
一个命令的实现例子

Examples:
    $python cli.py example --show tell me the truth
    >> Namespace(show=["'tell", 'me', 'the', "truth'"], command_handler=<bound method Example.cmd_entry of <commands.example.Example object at 0x0000017E6FD1DB40>>)
    >> ["'tell", 'me', 'the', "truth'"]
"""
import os

from commands.cmdbase import CmdBase
from commands.const import DSDL_CLI_DATASET_NAME
from commons.argument_parser import EnvDefaultVar
from tabulate import tabulate
from rich.tree import Tree
from rich import print as rprint
from utils import admin, query, plot
from utils.oss_ops import ops
import yaml

aws_access_key_id = query.aws_access_key_id
aws_secret_access_key = query.aws_secret_access_key
endpoint_url = query.endpoint_url
region_name = query.region_name
default_bucket = query.default_bucket


class Inspect(CmdBase):
    """
    Example command
    """

    def init_parser(self, subparsers):
        """
        Initialize the parser for the command
        document : https://docs.python.org/zh-cn/3/library/argparse.html#

        Args:
            subparsers:

        Returns:

        """
        inspect_parser = subparsers.add_parser(
            "inspect",
            help="Inspect dataset info",
            example="inspect.example",
            description="Inspect dataset info",
        )  # example 样例文件位于resources/下，普通的文本文件，每个命令写一个

        inspect_parser.add_argument(
            "dataset_name",
            action=EnvDefaultVar,
            envvar=DSDL_CLI_DATASET_NAME,
            type=str,
            help="Dataset name. The arg is optional only when the default dataset name was set by cd command.",
            metavar="",
        )

        inspect_parser.add_argument(
            "--split-name",
            type=str,
            help='The split name of the dataset, such as train/test/validation split.',
            metavar=''
        )

        group = inspect_parser.add_mutually_exclusive_group()

        group.add_argument(
            "-d",
            "--description",
            action="store_true",
            help="The split name of the dataset, such as train/test/unlabeled or user self-defined split.",
        )
        group.add_argument(
            "-s",
            "--statistics",
            action="store_true",
            help="Some statistics of the dataset.",
        )
        group.add_argument(
            "-m",
            "--metadata",
            action="store_true",
            help="Show metadata of the dataset.",
        )
        group.add_argument(
            "--schema",
            action="store_true",
            help="Show schema of the dataset.",
        )
        group.add_argument(
            "--preview",
            action="store_true",
            help="Preview of the dataset.",
        )

        return inspect_parser

    def cmd_entry(self, cmdargs, config, *args, **kwargs):
        """
        Entry point for the command

        Args:
            self:
            cmdargs:
            config:

        Returns:

        """

        dataset_name = cmdargs.dataset_name
        description = cmdargs.description
        statistics = cmdargs.statistics
        schema = cmdargs.schema
        metadata = cmdargs.metadata
        preview = cmdargs.preview
        split_name = cmdargs.split_name

        s3_client = ops.OssClient(endpoint_url=endpoint_url, aws_access_key_id=aws_access_key_id,
                                  aws_secret_access_key=aws_secret_access_key, region_name=region_name)
        db_client = admin.DBClient()
        remote_dataset_list = [x.replace('/', '') for x in s3_client.get_dir_list(default_bucket, '')]

        if dataset_name not in remote_dataset_list:
            print("there is no dataset named %s in remote repo" % dataset_name)
            exit()

        if db_client.is_dataset_local_exist(dataset_name):
            dataset_dict = query.get_dataset_info(dataset_name)
        else:
            parquet_key = '/'.join([dataset_name, 'parquet', 'dataset.yaml'])
            dataset_dict = yaml.safe_load(s3_client.read_file(default_bucket, parquet_key))

        if description:
            print("dataset description".center(100, "="))
            print(dataset_dict["dsdl_meta"]["dataset"]["meta"]["description"])

        if statistics:
            print("dataset statistics".center(100, "="))
            print("# " + "basic indicators")
            print(
                tabulate(
                    [dataset_dict["statistics"]["dataset_stat"]],
                    headers="keys",
                    tablefmt="plain",
                )
            )

            plot_list = dataset_dict["statistics"]["plots"]

            for p in plot_list:
                if p["type"] == "bar":
                    name = p["name"]
                    labels = p["data"]["x_data"]
                    y_data = p["data"]["y_data"]
                    data = list(zip(*[x["data"] for x in y_data]))
                    y_categories = [x["name"] for x in y_data]
                    y_colors = [x["color"] for x in y_data]
                    y_label = p["data"]["y_label"]
                    plot.plt_cmd_bar(
                        name, labels, data, y_categories, y_colors, y_label
                    )

        if schema:
            print("dataset schema".center(100, "="))
            schema_dict = dataset_dict["dsdl_meta"]["struct"]
            dsdl_version = schema_dict["$dsdl-version"]
            fields = schema_dict["Sample"]["$fields"]
            optional = schema_dict["Sample"]["$optional"]
            schema_tree = Tree(dataset_name)
            for k, v in fields.items():
                field_str = "%s: %s" % (k, v)
                if k in optional:
                    field_str = field_str + " (Optional)"
                schema_tree.add(field_str)

            print("# dsdl version: " + dsdl_version)
            rprint(schema_tree)

        if metadata:
            print("dataset metadata".center(100, "="))
            dataset_meta = dataset_dict["dsdl_meta"]["dataset"]["meta"]
            for k, v in dataset_meta.items():
                print(k + ": " + v)
            class_dict = dataset_dict["dsdl_meta"]["class_dom"]

            for k, v in class_dict.items():
                if not str(k).startswith("$"):
                    print(k + ":")
                    print(v["classes"])

        # if preview:
        #     print("Previewing the dataset...")
        #     from utils.views.view import View
        #
        #     view = View(dataset_name, inspect=True)
        #
        #     from utils.admin import DBClient
        #
        #     dbcli = DBClient()
        #     local_exists = dbcli.is_dataset_local_exist(dataset_name)
        #
        #     if local_exists is True:
        #         view.view_from_inspect(split_name)
        #     else:
        #         print(f"Dataset {dataset_name} is not exists on local.")
