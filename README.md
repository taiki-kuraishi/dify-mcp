# dify-mcp

## 概要

dify-mcpは、Dify Workflow DSL YAMLファイルを検証するためのMCP（Model Context Protocol）サーバーです。
FastMCPを使用して、Dify Workflowの定義ファイルの妥当性をチェックすることができます。

## 開発に必要なツール

- [mise](https://mise.jdx.dev/)

miseを使用することで、必要な開発ツール（uv、dprint、bun、lefthookなど）が自動的に管理されます。

## ディレクトリ構造

```text
.
├── .mise-tasks/          # miseタスク定義ファイル
│   ├── install           # 環境セットアップ
│   ├── format            # コードフォーマット
│   ├── lint              # コードリント
│   ├── update-git-submodule  # Git submodule更新
│   └── run/              # 実行タスク
│       ├── dify-mcp/     # dify-mcp実行タスク
│       └── mcp-inspector # MCPインスペクター起動
├── apps/
│   └── dify-mcp/         # MCPサーバー実装
│       ├── src/          # ソースコード
│       ├── tests/        # テストコード
│       └── pyproject.toml
├── dify/                 # Difyのサブモジュール
├── .mcp.json             # MCP設定ファイル
├── .mise.toml            # mise設定ファイル
├── pyproject.toml        # ワークスペース設定
├── ruff.toml             # Ruff設定
├── dprint.jsonc          # dprint設定
└── lefthook.yml          # Gitフック設定
```

## mise tasks

### `mise run install`

プロジェクトの開発環境をセットアップします。miseでツールをインストールし、uvで依存関係を同期、lefthookでGitフックを設定します。

### `mise run format`

コードを自動フォーマットします。dprintでファイルをフォーマットし、ruffでPythonコードを修正します。

### `mise run lint`

コードの静的解析を実行します。ruffでコードをチェックし、mypyで型チェックを行います。

### `mise run update-git-submodule`

Gitサブモジュール（dify）を最新の状態に更新します。

### `mise run dify-mcp`

dify-mcp開発サーバーをデフォルト設定で起動します。

### `mise run dify-mcp:stdio`

dify-mcp開発サーバーをstdio transportモードで起動します。

### `mise run dify-mcp:streamable-http`

dify-mcp開発サーバーをStreamable HTTP transportモードで起動します。

### `mise run mcp-inspector`

MCPインスペクターデバッグツールを起動します。MCPサーバーの動作確認に使用できます。
