## 开发环境设置

为了确保有一个统一且无误的开发体验，请根据使用的IDE完成以下一次性配置。这将解决所有关于模块导入（`ImportError`）的问题。

### VS Code

**无需任何手动操作。**

本项目已包含 `.vscode/settings.json` 配置文件。当您使用VS Code打开项目时，它将自动被识别。该配置会自动将 `./backend` 目录添加到Python模块的搜索路径中，确保所有从 `app` 开始的导入都能被正确解析。

### PyCharm 

**请执行一次手动配置。**

需要将后端的 `backend` 目录标记为“源代码根目录”(Sources Root)。步骤如下：

1.  在项目视图 (Project View) 中，找到项目根目录下的 `backend` 目录。
2.  右键点击 `backend` 目录。
3.  在弹出的菜单中，选择 **"Mark Directory as"** -> **"Sources Root"**。

操作完成后，`backend` 目录的图标会变为蓝色，表示PyCharm已经将其识别为源代码的起点。从此以后，所有从 `app` 开始的绝对路径导入都将正常工作。

---


## 启动

```zsh
docker-compose up -d --build
```

## 关闭docker

```zsh
docker-compose down
```

## 查看日志

```zsh
docker-compose logs <这里写具体的name>
```

具体的name可以看docker-compose.yml

比如我现在需要看celery-chat-worker的日志
那么我可以这样做：
```zsh
docker-compose logs celery-chat-worker
```

