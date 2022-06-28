# DSDL-SDK

基于DSDL的开发工具包，包含：
1. 基于DSDL的数据集描述
2. 对应DSDL语法解析器

## 安装

python 环境3.8及以上
```bash
$ python setup.py install
```

parser入口

```bash
$ dsdl parse --yaml tests/helloworld_config.yaml
```
其他可以尝试的例子：
```bash
$ dsdl parse --yaml tests/coco_demo1_config.yaml
```
```bash
$ dsdl parse --yaml tests/coco_demo2_config.yaml
```
## Acknowledgments

* Field & Model Design inspired by [Django ORM](https://www.djangoproject.com/) and [jsonmodels](https://github.com/jazzband/jsonmodels)

