import pytest
from fastapi.testclient import TestClient
from fastapi import status
import uuid
import greenlet

# SQLAlchemy 2.0のgreenlet対応のためのヘルパー関数
def run_in_greenlet(fn, *args, **kwargs):
    """
    greenletコンテキスト内で関数を実行するためのヘルパー関数
    """
    from sqlalchemy.ext.asyncio import AsyncEngine
    
    # SQLAlchemyのgreenlet設定
    def setup_greenlet_for_sqlalchemy():
        # SQLAlchemyのエンジンにgreenlet_spawnを設定
        import inspect
        import sys
        
        # 現在のフレームのローカル変数を取得
        frame = inspect.currentframe()
        try:
            for module_name, module in sys.modules.items():
                if module_name.startswith('sqlalchemy'):
                    for name, obj in inspect.getmembers(module):
                        if isinstance(obj, AsyncEngine):
                            if hasattr(obj, 'sync_engine'):
                                obj.sync_engine.greenlet_spawn = greenlet.greenlet
        finally:
            del frame
    
    # 結果を格納するリスト
    result = [None, None]
    
    # greenlet内で実行する関数
    def greenlet_runner():
        try:
            # SQLAlchemyのgreenlet設定
            setup_greenlet_for_sqlalchemy()
            # 関数を実行
            result[0] = fn(*args, **kwargs)
        except Exception as e:
            result[1] = e
    
    # greenletを作成して実行
    g = greenlet.greenlet(greenlet_runner)
    g.switch()
    
    # エラーがあれば再スロー
    if result[1] is not None:
        raise result[1]
    
    return result[0]

class TestUserSearch:
    @pytest.mark.asyncio
    async def test_search_users_by_username(self, client: TestClient, api_test_dependencies, db_test_user):
        """ユーザー名によるユーザー検索テスト"""
        def make_request():
            return client.get(f"/api/v1/search/users?username={db_test_user.username[:4]}")
        
        response = run_in_greenlet(make_request)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(user["username"] == db_test_user.username for user in data)
    
    @pytest.mark.asyncio
    async def test_search_users_by_fullname(self, client: TestClient, api_test_dependencies, db_test_user):
        """フルネームによるユーザー検索テスト"""
        def make_request():
            return client.get(f"/api/v1/search/users?fullname={db_test_user.fullname[:4]}")
        
        response = run_in_greenlet(make_request)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(user["fullname"] == db_test_user.fullname for user in data)
    
    @pytest.mark.asyncio
    async def test_search_users_by_admin_flag(self, client: TestClient, api_test_dependencies, db_test_admin):
        """管理者フラグによるユーザー検索テスト"""
        def make_request():
            return client.get("/api/v1/search/users?is_admin=true")
        
        response = run_in_greenlet(make_request)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(user["username"] == db_test_admin.username for user in data)
    
    @pytest.mark.asyncio
    async def test_search_users_by_active_flag(self, client: TestClient, api_test_dependencies, db_test_user, db_session):
        """アクティブフラグによるユーザー検索テスト"""
        # ユーザーを非アクティブに設定
        db_test_user.is_active = False
        await db_session.commit()
        
        def make_request():
            return client.get("/api/v1/search/users?is_active=false")
        
        response = run_in_greenlet(make_request)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(user["username"] == db_test_user.username for user in data)
    
    @pytest.mark.asyncio
    async def test_search_users_combined(self, client: TestClient, api_test_dependencies, db_test_admin):
        """複合条件によるユーザー検索テスト"""
        def make_request():
            return client.get(f"/api/v1/search/users?username={db_test_admin.username[:4]}&is_admin=true")
        
        response = run_in_greenlet(make_request)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(user["username"] == db_test_admin.username for user in data)
    
    @pytest.mark.asyncio
    async def test_search_users_no_results(self, client: TestClient, api_test_dependencies):
        """検索結果なしのテスト"""
        def make_request():
            return client.get("/api/v1/search/users?username=nonexistentuser")
        
        response = run_in_greenlet(make_request)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


class TestUserSync:
    @pytest.mark.asyncio
    async def test_sync_user_create(self, client: TestClient, api_test_dependencies):
        """ユーザー同期（新規作成）テスト"""
        user_id = str(uuid.uuid4())
        sync_data = {
            "user_id": user_id,
            "username": "syncuser",
            "fullname": "Sync User",
            "is_admin": False,
            "is_active": True
        }
        
        def make_request():
            return client.post("/api/v1/sync/user", json=sync_data)
        
        response = run_in_greenlet(make_request)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["username"] == sync_data["username"]
        assert data["fullname"] == sync_data["fullname"]
        assert data["is_admin"] == sync_data["is_admin"]
        assert data["is_active"] == sync_data["is_active"]
        assert str(data["user_id"]) == user_id
    
    @pytest.mark.asyncio
    async def test_sync_user_update(self, client: TestClient, api_test_dependencies, db_session):
        """ユーザー同期（更新）テスト"""
        # 最初にユーザーを作成
        user_id = uuid.uuid4()
        from app.models.user import User
        sync_user = User(
            username="syncuserupdate",
            fullname="Sync User Update",
            is_admin=False,
            is_active=True,
            user_id=user_id
        )
        db_session.add(sync_user)
        await db_session.commit()
        await db_session.refresh(sync_user)
        
        # 同期APIで更新
        sync_data = {
            "user_id": str(user_id),
            "username": "syncuserupdated",
            "fullname": "Sync User Updated",
            "is_admin": True,
            "is_active": False
        }
        
        def make_request():
            return client.post("/api/v1/sync/user", json=sync_data)
        
        response = run_in_greenlet(make_request)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["username"] == sync_data["username"]
        assert data["fullname"] == sync_data["fullname"]
        assert data["is_admin"] == sync_data["is_admin"]
        assert data["is_active"] == sync_data["is_active"]
        assert str(data["user_id"]) == str(user_id)
    
    @pytest.mark.asyncio
    async def test_sync_user_without_fullname(self, client: TestClient, api_test_dependencies):
        """フルネームなしでのユーザー同期テスト"""
        user_id = str(uuid.uuid4())
        sync_data = {
            "user_id": user_id,
            "username": "syncusernofullname",
            "is_admin": False,
            "is_active": True
        }
        
        def make_request():
            return client.post("/api/v1/sync/user", json=sync_data)
        
        response = run_in_greenlet(make_request)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["username"] == sync_data["username"]
        assert data["fullname"] is None
        assert data["is_admin"] == sync_data["is_admin"]
        assert data["is_active"] == sync_data["is_active"]
        assert str(data["user_id"]) == user_id
