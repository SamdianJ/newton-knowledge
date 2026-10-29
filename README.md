# Newton Knowledge MCP 本地发布包

这是可复制、解压或通过 Git 获取的只读 Newton 知识库服务，包含当前知识快照、锁定的 Newton 源码、实验记录及可选本地浏览网站。无需安装 Newton 仿真环境、GPU 驱动或提供模型 API Key。运行物理实验和重新生成知识库属于原开发项目的工作，本包提供已经生成的结果。

## 安装与验证

先安装 Python 3.12（含 venv、pip 和 SQLite FTS5），然后在本目录打开终端：

```console
python manage.py install
python manage.py doctor
python manage.py smoke
python manage.py config --format json
```

Windows 可将上述 `python` 替换为 `py -3.12`。首次安装需要联网下载锁定依赖；之后读取知识库和实验结果不依赖网络。管理工具也接受较新的 Python，但发布验收以 Python 3.12 / Windows 为准，其他组合需自行执行 doctor 和 smoke。

`config` 会打印本目录对应的客户端配置，将它合并到支持 stdio MCP 的客户端配置中。需要 TOML 时使用 `python manage.py config --format toml`。工具不会修改全局配置。客户端负责启动服务；也可用 `python manage.py mcp` 启动协议进程，其标准输出专供 MCP 消息。

六个只读工具：`search_knowledge`、`get_parameter`、`get_experiment`、`get_document`、`get_source`、`get_relations`。`smoke` 会通过真实 stdio 会话验证工具、全部 48 个实验、118 个归档程序及文件引用，并把结果写入 `.validation/`。

## 可选实验网站

```console
python manage.py site
```

在浏览器打开 http://127.0.0.1:18448/。网站仅监听本机，包含保存的实验曲线、物体轮廓回放和证据链接。MCP 使用 stdio；网站地址不是 MCP 接口地址。

若端口已占用，可选择另一端口，并让 MCP 返回相应的网页链接：

```console
python manage.py site --port 18449
python manage.py config --format json --site-url http://127.0.0.1:18449
```

## 打包、Git 与迁移

本目录就是发布或 Git 仓库的根目录。`.gitignore` 排除安装生成的虚拟环境、测试输出和网站运行状态；`.gitattributes` 保留文件原始字节，防止 Windows 自动转换换行导致证据哈希失效。提交时保留隐藏文件和 `package-manifest.json`，不要对知识快照、源码或实验数据进行格式化。

接收者克隆或解压后执行上面的安装命令。不要分发 `.venv`：虚拟环境含本机路径，移动安装目录后应在新目录重新创建环境并重新生成客户端配置。最方便的升级方式是解压新版到新目录并安装。

Windows 建议使用较短的安装目录，例如 `C:\NewtonMCP`。包内实验记录最长相对路径为 181 个字符；未启用系统长路径支持时，请将发布根目录绝对路径控制在 70 个字符以内，避免解压或安装失败。Git 接收者同样应选择较短的克隆目录。

```text
manage.py                 安装、校验、配置与启动入口
requirements.lock.txt     固定运行依赖
package-manifest.json     发布文件 SHA-256 清单与省略资源记录
knowledge-base/           保留原相对路径的知识库数据
.venv/                    本机安装生成，不随包分发
.validation/              本机验收生成，不随包分发
```

`python manage.py verify` 无需安装依赖即可检查发布文件和知识快照的一致性。清单用于发现缺失和意外改动，不是发布者身份签名。`knowledge-base/` 内的 README、报告及历史环境路径属于原项目资料，本包的安装方式以本 README 为准。

默认包不附带论文原件，保留论文映射、引用、来源链接和原件哈希清单；相应本地 PDF 链接可能不可打开。Newton 源码许可证和前端第三方许可证保留在原目录。权利说明见 `THIRD_PARTY_NOTICES.md`。

## 离线安装

在与目标机器匹配的操作系统和 Python 版本上准备 wheelhouse：

```console
python -m pip download -r requirements.lock.txt -d wheelhouse
```

将 wheelhouse 一同带到目标机器后运行：

```console
python manage.py install --wheelhouse wheelhouse
```

目标机器仍需提前安装 Python。只读运行无需互联网；在线官方文档和论文链接需要网络。
