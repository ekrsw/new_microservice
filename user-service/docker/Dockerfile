FROM python:3.12.9-slim

# 作業ディレクトリの設定
WORKDIR /workdir

# 必要な環境変数を設定
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 依存関係のインストール
COPY ./requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# アプリケーションコードのコピー
COPY ./app /workdir/app

# RSA鍵ファイルのコピー
COPY ./keys/ /workdir/keys/

# 非rootユーザーを作成して実行（セキュリティ向上）
RUN adduser --disabled-password --gecos "" appuser && \
    # ボリュームマウントポイントの所有権を変更
    mkdir -p /workdir/.pytest_cache && \
    # 公開鍵のパーミッションを設定
    chmod 644 /workdir/keys/public.pem && \
    chown -R appuser:appuser /workdir

# Uvicornでアプリケーションを起動（ワーカー数を制限）
# 環境変数からホストとポートを取得するようにエントリポイントスクリプトを使用
COPY ./docker/scripts /workdir/scripts
RUN chmod +x ./scripts/entrypoint.sh

USER appuser
ENTRYPOINT ["./scripts/entrypoint.sh"]
