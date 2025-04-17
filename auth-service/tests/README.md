# Auth Serviceテストガイド

このドキュメントでは、Auth Serviceのテスト実行方法について説明します。

## テストの構成

テストは以下のディレクトリ構造で整理されています：

```
tests/
├── api/            - APIエンドポイントのテスト
│   └── v1/         - v1 APIのテスト
│       └── test_auth.py - 認証関連エンドポイントのテスト
├── core/           - コア機能のテスト
│   └── test_security.py - セキュリティ関連機能のテスト
├── crud/           - CRUDオペレーションのテスト
│   └── user/       - ユーザー関連CRUDのテスト
│       └── conftest.py - ユーザーテスト用のフィクスチャ
└── conftest.py     - テスト全体で共有されるフィクスチャ
```

## テスト環境の設定

テストはDocker Composeを使用して専用のテスト環境で実行されます。テスト用の設定ファイルは以下の通りです：

- `.env.test` - テスト環境の環境変数設定
- `docker-compose.test.yml` - テスト用のDockerコンテナ設定

## テストの実行方法

### Dockerを使用したテスト実行（推奨）

テスト用のコンテナを起動し、テストを実行します：

```bash
# テスト用のコンテナを起動
docker-compose -f docker-compose.test.yml up -d

# テスト実行
docker-compose -f docker-compose.test.yml exec auth_test_app pytest -v

# 特定のテストのみ実行する場合
docker-compose -f docker-compose.test.yml exec auth_test_app pytest -v tests/api/v1/test_auth.py

# カバレッジレポートを生成する場合
docker-compose -f docker-compose.test.yml exec auth_test_app pytest --cov=app --cov-report=term-missing

# テスト終了後にコンテナを停止
docker-compose -f docker-compose.test.yml down
```

### テスト実行オプション

pytestコマンドに以下のオプションを追加できます：

- `-v` または `--verbose` - 詳細な出力
- `-s` - 標準出力の表示（print文の出力を表示）
- `--cov=app` - カバレッジの測定対象（アプリケーションコード）
- `--cov-report=term-missing` - カバレッジレポートの形式（ターミナル表示、未カバーの行を表示）
- `-k "keyword"` - キーワードでテストをフィルタリング
- `-m "marker"` - マーカーでテストをフィルタリング

## テスト用フィクスチャ

主要なフィクスチャ：

- `db_session` - テスト用のデータベースセッション
- `create_test_user` - テスト用の一般ユーザー
- `create_admin_user` - テスト用の管理者ユーザー
- `token_headers` - 一般ユーザーの認証ヘッダー
- `admin_token_headers` - 管理者ユーザーの認証ヘッダー
- `user_tokens` - 一般ユーザーのアクセストークンとリフレッシュトークン
- `admin_tokens` - 管理者ユーザーのアクセストークンとリフレッシュトークン

## テストファイルの追加方法

新しいテストを追加する場合は、適切なディレクトリに`test_`プレフィックスを持つPythonファイルを作成してください。
テストクラスには`Test`プレフィクスを、テスト関数には`test_`プレフィクスを使用してください。

非同期テストを追加する場合は、`@pytest.mark.asyncio`デコレータを使用してください。
