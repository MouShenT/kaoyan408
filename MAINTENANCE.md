# 资料维护

需要 Python 3.10+、Git 和 Git LFS。首次下载原件：

```sh
git lfs install
git lfs pull
python -m pip install -r requirements.txt
python scripts/library.py search "关键词"
python scripts/library.py page MATERIAL_ID 12
```

`MATERIAL_ID` 来自 catalog/materials.json；图片输出到 .cache，使用看图工具核对。

添加或修订材料后：

```sh
python scripts/library.py build
python -m pip install -r requirements-ocr.txt
python scripts/ocr_library.py
python scripts/library.py build
python -m unittest discover -s tests -v
```

OCR 仅在本地执行；.cache 保存按文件哈希绑定的逐页缓存，可中断续跑。机器识别不能取代公式/图表核验。提交前检查 catalog 与 knowledge 的变化，原件通过 Git LFS 上传。

原文件名、目录结构在 materials 内保留。SHA-256 用于一致性检查，不证明版本权威或答案正确。原件内容权利归原权利人，代码和索引不改变原件权利。

学习记录默认写入被忽略的 private/。不要在公开 Issues、提交信息或知识库中放真实照片、聊天和个人信息。所有样例必须标为虚构。
