# Project generator

## 说明
（这是一个中文版的项目改进说明）
project_generator将会支持整个项目构建，各种嵌入式模块管理等，让嵌入式项目管理更简单。


## 修改部分
Date: 2018/08/02
Author: Gene Kong
1. 工具链的描述应该更加直接，make_gcc_arm 修改为gcc_arm；
2. 不同内核不同文件，都是使用core_xx开始，例如cortex-m0才有的文件放到core_cortex-m0下面；
