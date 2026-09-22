# 手机聊天与拍题

在手机 ChatGPT 中连接 GitHub 并授权 `MouShenT/kaoyan408`。能否在普通聊天中调用 GitHub 取决于账号、工作区和产品界面；仓库上传不会自动启用连接或永久记忆。

第一次聊天可以复制：

> 请通过 GitHub 读取 MouShenT/kaoyan408 的 CHAT_INSTRUCTIONS.md、catalog/README.md 和 knowledge/ 中与本题有关的内容，按仓库规则作为我的408 计算机学科专业基础学习助手。我会聊天和拍题；围绕当次问题、我的解题步骤和错题即时反馈，不制定详细长期计划。引用实际读到的资料页；没找到时明确说没找到。现在先处理我发的题。

然后发照片、原句或作文即可。可说“只给第一步提示”“完整讲解”“看我哪一步错了”“给两道同类练习”。

普通 ChatGPT 不保证自动执行 AGENTS.md，所以要明确让它读取 CHAT_INSTRUCTIONS.md。GitHub 应用读取的是授权文件，并不自动训练出一个新模型；PDF/LFS 原件也不能代替可检索的 `knowledge` 文本。

如果 GitHub 在当前聊天不可用，可直接把 CHAT_INSTRUCTIONS.md 的内容与题目照片放进聊天；这时助手只能依据实际提供的内容，不能声称已检索整个仓库。需要原书依据时附对应原页。

错题保存到 Notion“考研错题简记”：只记题目、科目、知识点，不记错题原因。请在手机当前聊天连接 Notion，并让助手读取 `NOTION.md`、检索该数据库；成功写入后应返回页面链接。不可用时生成简记供复制。

官方说明：[连接 GitHub 到 ChatGPT](https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt)。如使用手机 Remote 连接电脑，则电脑需要在线，且功能可用性取决于账号；它不是普通 GitHub 只读连接。[Remote 文档](https://learn.chatgpt.com/docs/remote)。

学习方式见 [真题与理解](LEARNING_METHOD.md)。可直接说：“先围绕这道真题讲清必要知识，讲完把题目和知识点记到 Notion，不记错题原因。”

手机 ChatGPT 项目使用：[可复制项目指令](PROJECT_INSTRUCTIONS.md)。
