# 给 Gemini 的最小代码包（推荐方式）

目标：避免“文件太多无法处理”，把关键代码合并为 1 个文件：GEMINI_CODE.md。

## 1. 生成 GEMINI_CODE.md

在项目根目录打开 PowerShell，执行：

```powershell
.\make_gemini_bundle.ps1 -OutDir .\gemini_bundle
```

执行后会生成：

- `gemini_bundle/GEMINI_CODE.md`

这个文件包含后端与前端的核心代码片段（按文件分段），适合直接丢给 Gemini 做论文/改进建议。

## 2. 上传到 GitHub（推荐：新建一个“只放 GEMINI_CODE.md”的仓库）

为了避免把整个项目推上去导致体积过大、Gemini 也读不动，建议新建一个小仓库，例如：

- 仓库名：`bishi-gemini-bundle`
- 类型：Private（私有）

把 `gemini_bundle` 文件夹里的 `GEMINI_CODE.md` 上传即可（GitHub 网页端也能上传）。

### 网页上传（最稳，不用命令）

1. 打开你的仓库页面
2. 点击 **Add file** → **Upload files**
3. 把 `gemini_bundle/GEMINI_CODE.md` 拖进去
4. 提交（Commit changes）

## 3. 交给 Gemini

你可以把 `GEMINI_CODE.md`：

- 直接上传给 Gemini（文件上传）
- 或者把 GitHub 仓库链接发给 Gemini

建议你在提问里加一句：

- “请你根据该项目代码，帮我按毕业论文模板完善/纠错，并指出系统亮点与不足。”

