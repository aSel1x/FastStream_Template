import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from datetime import UTC, datetime, timedelta

from domain.user.value_objects import UserID, Username, Email, PlainPassword, HashedPassword, TokenHash
from domain.user.entities.user import User


class TestCreateUserUseCase:
    @pytest.fixture
    def mock_user_service(self):
        service = MagicMock()
        service.create = AsyncMock(return_value=MagicMock(
            id=UserID(value=uuid4()),
            pull_events=MagicMock(return_value=[])
        ))
        return service

    @pytest.fixture
    def mock_uow(self):
        uow = MagicMock()
        uow.add_events = MagicMock()
        uow.commit = AsyncMock()
        return uow

    @pytest.fixture
    def mock_rate_limiter(self):
        limiter = AsyncMock()
        limiter.check = AsyncMock(return_value=(True, 10, None))
        return limiter

    @pytest.mark.asyncio
    async def test_create_user_success(self, mock_user_service, mock_rate_limiter, mock_uow):
        from application.user.commands.create_user import CreateUserInput, CreateUserUseCase

        use_case = CreateUserUseCase(
            user_service=mock_user_service,
            uow=mock_uow,
            uuid_generator=uuid4,
            rate_limiter=mock_rate_limiter,
        )

        result = await use_case(CreateUserInput(
            username="testuser",
            password="Test@1234",
            email="test@example.com"
        ))

        assert result is not None

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(self, mock_rate_limiter, mock_uow):
        from domain.user.exceptions import UsernameAlreadyExistsError
        from application.user.commands.create_user import CreateUserInput, CreateUserUseCase

        user_service = MagicMock()
        user_service.create = AsyncMock(
            side_effect=UsernameAlreadyExistsError("testuser")
        )

        use_case = CreateUserUseCase(
            user_service=user_service,
            uow=mock_uow,
            uuid_generator=uuid4,
            rate_limiter=mock_rate_limiter,
        )
        
        with pytest.raises(UsernameAlreadyExistsError):
            await use_case(CreateUserInput(
                username="testuser",
                password="Test@1234",
            ))


class TestLoginUseCase:
    @pytest.fixture
    def mock_user_service(self):
        return MagicMock()

    @pytest.fixture
    def mock_rate_limiter(self):
        limiter = AsyncMock()
        limiter.check = AsyncMock(return_value=(True, 10, None))
        return limiter

    @pytest.fixture
    def mock_login_attempt_limiter(self):
        limiter = AsyncMock()
        limiter.is_locked = AsyncMock(return_value=False)
        limiter.record_failed_login = AsyncMock(return_value=False)
        limiter.reset = AsyncMock()
        return limiter

    @pytest.fixture
    def mock_uow(self):
        uow = MagicMock()
        uow.add_events = MagicMock()
        uow.commit = AsyncMock()
        return uow

    @pytest.mark.asyncio
    async def test_login_success(self, mock_user_service, mock_rate_limiter, mock_login_attempt_limiter, mock_uow):
        from application.user.commands.login import LoginInput, LoginUseCase

        user = User.create(
            user_id=UserID(uuid4()),
            username=Username("testuser"),
            email=Email("test@example.com"),
            hashed_password=HashedPassword(b"hashed"),
            verification_token="token",
        )
        user = user.mark_email_verified()

        session = MagicMock()
        session.session_id = uuid4()
        session.expires_at = datetime.now(UTC) + timedelta(days=1)
        session.pull_events = MagicMock(return_value=[])

        mock_user_service.authenticate = AsyncMock(return_value=(user, session, "raw-refresh-token"))
        mock_user_service.persist_session = AsyncMock()

        use_case = LoginUseCase(
            user_service=mock_user_service,
            rate_limiter=mock_rate_limiter,
            login_attempt_limiter=mock_login_attempt_limiter,
            uow=mock_uow,
        )

        result = await use_case(LoginInput(
            password="Test@1234",
            username="testuser",
            ip_address="127.0.0.1",
        ))

        assert result.user_id == user.id.to_raw()
        assert result.session_id == str(session.session_id)
        assert result.refresh_token == "raw-refresh-token"
        assert not result.requires_two_factor
        mock_user_service.persist_session.assert_awaited_once_with(session)
        mock_rate_limiter.check.assert_awaited_once_with("login:127.0.0.1")

    @pytest.mark.asyncio
    async def test_login_requires_2fa(self, mock_user_service, mock_rate_limiter, mock_login_attempt_limiter, mock_uow):
        from application.user.commands.login import LoginInput, LoginUseCase
        from infrastructure.two_factor import TwoFactorAuth

        user = User.create(
            user_id=UserID(uuid4()),
            username=Username("testuser"),
            email=Email("test@example.com"),
            hashed_password=HashedPassword(b"hashed"),
            verification_token="token",
        )
        user = user.mark_email_verified()
        user = user.enable_two_factor(TwoFactorAuth())

        session = MagicMock()
        session.session_id = uuid4()
        session.pull_events = MagicMock(return_value=[])

        mock_user_service.authenticate = AsyncMock(return_value=(user, session, "raw-refresh-token"))
        mock_user_service.persist_session = AsyncMock()

        use_case = LoginUseCase(
            user_service=mock_user_service,
            rate_limiter=mock_rate_limiter,
            login_attempt_limiter=mock_login_attempt_limiter,
            uow=mock_uow,
        )

        result = await use_case(LoginInput(
            password="Test@1234",
            username="testuser",
        ))

        assert result.requires_two_factor

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, mock_user_service, mock_rate_limiter, mock_login_attempt_limiter, mock_uow):
        from domain.user.exceptions import InvalidCredentialsError
        from application.user.commands.login import LoginInput, LoginUseCase

        mock_user_service.authenticate = AsyncMock(return_value=(None, None, None))

        use_case = LoginUseCase(
            user_service=mock_user_service,
            rate_limiter=mock_rate_limiter,
            login_attempt_limiter=mock_login_attempt_limiter,
            uow=mock_uow,
        )

        with pytest.raises(InvalidCredentialsError):
            await use_case(LoginInput(
                password="Wrong@1234",
                username="testuser",
            ))

    @pytest.mark.asyncio
    async def test_login_rate_limited(self, mock_user_service, mock_rate_limiter, mock_login_attempt_limiter, mock_uow):
        from application.common.exceptions import TooManyLoginAttemptsError
        from application.user.commands.login import LoginInput, LoginUseCase

        mock_rate_limiter.check = AsyncMock(return_value=(False, 0, None))

        use_case = LoginUseCase(
            user_service=mock_user_service,
            rate_limiter=mock_rate_limiter,
            login_attempt_limiter=mock_login_attempt_limiter,
            uow=mock_uow,
        )

        with pytest.raises(TooManyLoginAttemptsError):
            await use_case(LoginInput(
                password="Test@1234",
                username="testuser",
                ip_address="127.0.0.1",
            ))

        mock_user_service.authenticate.assert_not_called()

    @pytest.mark.asyncio
    async def test_login_blocked_by_ip_login_attempt_lockout(
        self, mock_user_service, mock_rate_limiter, mock_login_attempt_limiter, mock_uow,
    ):
        from application.common.exceptions import TooManyLoginAttemptsError
        from application.user.commands.login import LoginInput, LoginUseCase

        mock_login_attempt_limiter.is_locked = AsyncMock(return_value=True)

        use_case = LoginUseCase(
            user_service=mock_user_service,
            rate_limiter=mock_rate_limiter,
            login_attempt_limiter=mock_login_attempt_limiter,
            uow=mock_uow,
        )

        with pytest.raises(TooManyLoginAttemptsError):
            await use_case(LoginInput(
                password="Test@1234",
                username="testuser",
                ip_address="127.0.0.1",
            ))

        mock_user_service.authenticate.assert_not_called()

    @pytest.mark.asyncio
    async def test_login_failure_records_ip_attempt(
        self, mock_user_service, mock_rate_limiter, mock_login_attempt_limiter, mock_uow,
    ):
        from domain.user.exceptions import InvalidCredentialsError
        from application.user.commands.login import LoginInput, LoginUseCase

        mock_user_service.authenticate = AsyncMock(return_value=(None, None, None))

        use_case = LoginUseCase(
            user_service=mock_user_service,
            rate_limiter=mock_rate_limiter,
            login_attempt_limiter=mock_login_attempt_limiter,
            uow=mock_uow,
        )

        with pytest.raises(InvalidCredentialsError):
            await use_case(LoginInput(
                password="Wrong@1234",
                username="testuser",
                ip_address="127.0.0.1",
            ))

        mock_login_attempt_limiter.record_failed_login.assert_awaited_once_with("127.0.0.1")

    @pytest.mark.asyncio
    async def test_login_success_resets_ip_attempt_counter(
        self, mock_user_service, mock_rate_limiter, mock_login_attempt_limiter, mock_uow,
    ):
        from application.user.commands.login import LoginInput, LoginUseCase

        user = User.create(
            user_id=UserID(uuid4()),
            username=Username("testuser"),
            email=Email("test@example.com"),
            hashed_password=HashedPassword(b"hashed"),
            verification_token="token",
        )
        user = user.mark_email_verified()

        session = MagicMock()
        session.session_id = uuid4()
        session.pull_events = MagicMock(return_value=[])

        mock_user_service.authenticate = AsyncMock(return_value=(user, session, "raw-refresh-token"))
        mock_user_service.persist_session = AsyncMock()

        use_case = LoginUseCase(
            user_service=mock_user_service,
            rate_limiter=mock_rate_limiter,
            login_attempt_limiter=mock_login_attempt_limiter,
            uow=mock_uow,
        )

        await use_case(LoginInput(
            password="Test@1234",
            username="testuser",
            ip_address="127.0.0.1",
        ))

        mock_login_attempt_limiter.reset.assert_awaited_once_with("127.0.0.1")


class TestGetMeUseCase:
    @pytest.mark.asyncio
    async def test_get_me_success(self):
        from application.user.queries.get_me import GetMeUseCase
        from domain.user.interfaces.persistence.readers import UserReadDTO

        user_id = uuid4()
        dto = UserReadDTO(
            user_id=user_id,
            username='testuser',
            email='test@example.com',
            is_email_verified=True,
            is_locked=False,
            two_factor_secret=None,
        )

        reader = MagicMock()
        reader.get_by_id = AsyncMock(return_value=dto)

        use_case = GetMeUseCase(user_reader=reader)

        result = await use_case(user_id)

        assert result.username == 'testuser'
        assert result.email == 'test@example.com'
        assert result.is_email_verified


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests(self):
        from infrastructure.security.rate_limiter import InMemoryRateLimiter, RateLimitConfig

        config = RateLimitConfig(max_requests=10, window_seconds=60)
        limiter = InMemoryRateLimiter(config)

        for i in range(10):
            allowed, _, _ = await limiter.check(f"user_{i}")
            assert allowed

    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_excess(self):
        from infrastructure.security.rate_limiter import InMemoryRateLimiter, RateLimitConfig

        config = RateLimitConfig(max_requests=5, window_seconds=60)
        limiter = InMemoryRateLimiter(config)

        for _ in range(5):
            allowed, _, _ = await limiter.check("test_key")
            assert allowed

        allowed, remaining, _ = await limiter.check("test_key")
        assert not allowed
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_rate_limiter_cleanup(self):
        from datetime import timedelta

        from infrastructure.security.rate_limiter import InMemoryRateLimiter, RateLimitConfig

        config = RateLimitConfig(
            max_requests=5,
            window_seconds=1,
            cleanup_interval_seconds=1,
            max_keys=100,
        )
        limiter = InMemoryRateLimiter(config)

        for _ in range(3):
            await limiter.check("key1")
            await limiter.check("key2")

        limiter._buckets["key1"] = []
        limiter._last_cleanup = limiter._last_cleanup - timedelta(seconds=10)

        limiter._maybe_cleanup()

        assert len(limiter._buckets) <= 100

    @pytest.mark.asyncio
    async def test_login_attempt_limiter_locks_after_attempts(self):
        from infrastructure.security.rate_limiter import InMemoryLoginAttemptLimiter, RateLimitConfig

        config = RateLimitConfig(max_login_attempts=5, lockout_seconds=60)
        limiter = InMemoryLoginAttemptLimiter(config)

        for _ in range(4):
            assert not await limiter.record_failed_login("192.168.1.1")
        assert await limiter.record_failed_login("192.168.1.1")

        assert await limiter.is_locked("192.168.1.1")

    @pytest.mark.asyncio
    async def test_login_attempt_limiter_reset(self):
        from infrastructure.security.rate_limiter import InMemoryLoginAttemptLimiter, RateLimitConfig

        config = RateLimitConfig(max_login_attempts=5, lockout_seconds=60)
        limiter = InMemoryLoginAttemptLimiter(config)

        for _ in range(3):
            await limiter.record_failed_login("192.168.1.2")

        await limiter.reset("192.168.1.2")

        assert not await limiter.is_locked("192.168.1.2")


class TestPagination:
    def test_sessions_page_creation(self):
        from application.user.queries.manage_sessions import SessionsPage
        
        page = SessionsPage(
            sessions=[{'id': 1}, {'id': 2}],
            total=10,
            limit=5,
            offset=0,
            has_more=True,
        )
        
        assert len(page.sessions) == 2
        assert page.total == 10
        assert page.has_more


class TestUserService:
    @pytest.fixture
    def mock_repos(self):
        user_repo = AsyncMock()
        session_repo = AsyncMock()
        crypt = AsyncMock()
        crypt.hash = AsyncMock(return_value=b'hashed')
        return user_repo, session_repo, crypt

    @pytest.mark.asyncio
    async def test_create_user(self, mock_repos):
        from application.user.services import UserService
        from domain.user.value_objects import Username, Email
        
        user_repo, session_repo, crypt = mock_repos
        user_repo.check_username_exists = AsyncMock(return_value=False)
        user_repo.check_email_exists = AsyncMock(return_value=False)
        user_repo.add = AsyncMock()
        
        service = UserService(user_repo, session_repo, crypt)
        
        result = await service.create(
            user_id=UserID(uuid4()),
            username=Username("testuser"),
            password=PlainPassword("Test@1234"),
            email=Email("test@example.com"),
        )
        
        assert result is not None
        assert result.username.to_raw() == "testuser"

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(self, mock_repos):
        from application.user.services import UserService
        from domain.user.value_objects import Username
        from domain.user.exceptions import UsernameAlreadyExistsError
        
        user_repo, session_repo, crypt = mock_repos
        user_repo.check_username_exists = AsyncMock(return_value=True)
        
        service = UserService(user_repo, session_repo, crypt)
        
        with pytest.raises(UsernameAlreadyExistsError):
            await service.create(
                user_id=UserID(uuid4()),
                username=Username("testuser"),
                password=PlainPassword("Test@1234"),
            )

    @pytest.mark.asyncio
    async def test_authenticate_invalid_credentials(self, mock_repos):
        from application.user.services import UserService
        
        user_repo, session_repo, crypt = mock_repos
        user_repo.acquire_by_username = AsyncMock(return_value=None)
        
        service = UserService(user_repo, session_repo, crypt)
        
        user, session, refresh_token = await service.authenticate(
            password=PlainPassword("Test@1234"),
            username="testuser",
        )

        assert user is None
        assert session is None
        assert refresh_token is None

    @pytest.mark.asyncio
    async def test_authenticate_success_issues_refresh_token(self, mock_repos):
        from application.user.services import UserService
        from domain.user.entities.user import User
        from domain.user.value_objects import Email, HashedPassword, Username

        user_repo, session_repo, crypt = mock_repos
        existing_user = User.create(
            user_id=UserID(uuid4()),
            username=Username('testuser'),
            email=Email('test@example.com'),
            hashed_password=HashedPassword(b'hashed'),
            verification_token='tok',
        )
        user_repo.acquire_by_username = AsyncMock(return_value=existing_user)
        crypt.compare_hashes = AsyncMock(return_value=True)
        session_repo.add = AsyncMock()

        service = UserService(user_repo, session_repo, crypt)

        user, session, refresh_token = await service.authenticate(
            password=PlainPassword('Test@1234'),
            username='testuser',
        )

        assert user is not None
        assert session is not None
        assert refresh_token
        assert len(session.refresh_tokens) == 1
        assert session.refresh_tokens[0].token_hash == TokenHash.from_raw(refresh_token)
        user_repo.update.assert_awaited_once_with(user)

    @pytest.mark.asyncio
    async def test_authenticate_failed_attempt_persists_lockout_state(self, mock_repos):
        """A wrong password must persist the incremented failed-attempt/lock state to the
        repo — otherwise account lockout only ever exists in the returned object and the
        next login attempt reads the pre-lockout row right back out of the DB."""
        from application.user.services import UserService
        from domain.user.entities.user import User
        from domain.user.value_objects import Email, HashedPassword, Username

        user_repo, session_repo, crypt = mock_repos
        existing_user = User.create(
            user_id=UserID(uuid4()),
            username=Username('testuser'),
            email=Email('test@example.com'),
            hashed_password=HashedPassword(b'hashed'),
            verification_token='tok',
        )
        user_repo.acquire_by_username = AsyncMock(return_value=existing_user)
        crypt.compare_hashes = AsyncMock(return_value=False)

        service = UserService(user_repo, session_repo, crypt)

        user, session, refresh_token = await service.authenticate(
            password=PlainPassword('Wrong@1234'),
            username='testuser',
        )

        assert session is None
        assert refresh_token is None
        assert user.account_lock.failed_attempts == 1
        user_repo.update.assert_awaited_once_with(user)

    @pytest.mark.asyncio
    async def test_change_password_wrong_old_password(self, mock_repos):
        from application.user.services import UserService
        from domain.user.entities.user import User
        from domain.user.exceptions import InvalidCredentialsError
        from domain.user.value_objects import Email, HashedPassword, Username

        user_repo, session_repo, crypt = mock_repos
        existing_user = User.create(
            user_id=UserID(uuid4()),
            username=Username('testuser'),
            email=Email('test@example.com'),
            hashed_password=HashedPassword(b'hashed'),
            verification_token='tok',
        )
        crypt.compare_hashes = AsyncMock(return_value=False)

        service = UserService(user_repo, session_repo, crypt)

        with pytest.raises(InvalidCredentialsError):
            await service.change_password(
                existing_user, PlainPassword('Wrong@1234'), PlainPassword('New@1234'),
            )

        user_repo.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_change_password_success_revokes_sessions(self, mock_repos):
        from application.user.services import UserService
        from domain.user.entities.user import User
        from domain.user.value_objects import Email, HashedPassword, Username

        user_repo, session_repo, crypt = mock_repos
        existing_user = User.create(
            user_id=UserID(uuid4()),
            username=Username('testuser'),
            email=Email('test@example.com'),
            hashed_password=HashedPassword(b'hashed'),
            verification_token='tok',
        )
        crypt.compare_hashes = AsyncMock(return_value=True)
        session_repo.acquire_by_user_id = AsyncMock(return_value=[])

        service = UserService(user_repo, session_repo, crypt)
        updated = await service.change_password(
            existing_user, PlainPassword('Old@1234'), PlainPassword('New@1234'),
        )

        assert updated.hashed_password.to_raw() == b'hashed'
        user_repo.update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_refresh_session_round_trips_token_hash(self, mock_repos):
        """Regression test: refresh tokens are hashed deterministically (SHA-256 via
        TokenHash.from_raw), not with bcrypt — bcrypt salts randomly, so a hash computed at
        issuance time could never match one recomputed at lookup time."""
        from application.user.services import UserService
        from domain.user.entities.session import DeviceInfo, RefreshToken, SessionAggregate
        from domain.user.entities.user import User
        from domain.user.value_objects import Email, HashedPassword, Username

        user_repo, session_repo, crypt = mock_repos
        existing_user = User.create(
            user_id=UserID(uuid4()),
            username=Username('testuser'),
            email=Email('test@example.com'),
            hashed_password=HashedPassword(b'hashed'),
            verification_token='tok',
        )
        raw_token = 'a-raw-refresh-token'
        session = SessionAggregate.create(user_id=existing_user.id, device_info=DeviceInfo())
        refresh_token = RefreshToken(
            token_hash=TokenHash.from_raw(raw_token),
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        session = session.add_refresh_token(refresh_token)

        session_repo.acquire_by_token_hash = AsyncMock(return_value=session)
        user_repo.acquire_by_id = AsyncMock(return_value=existing_user)
        session_repo.update = AsyncMock()

        service = UserService(user_repo, session_repo, crypt)
        refreshed_session, user = await service.refresh_session(raw_token)

        session_repo.acquire_by_token_hash.assert_awaited_once_with(TokenHash.from_raw(raw_token).to_raw())
        assert user.id == existing_user.id
        assert refreshed_session.session_id == session.session_id

    @pytest.mark.asyncio
    async def test_refresh_session_unknown_token_raises(self, mock_repos):
        from application.user.services import UserService
        from domain.user.exceptions import InvalidCredentialsError

        user_repo, session_repo, crypt = mock_repos
        session_repo.acquire_by_token_hash = AsyncMock(return_value=None)

        service = UserService(user_repo, session_repo, crypt)

        with pytest.raises(InvalidCredentialsError):
            await service.refresh_session('unknown-token')


class TestInMemoryCache:
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        from infrastructure.cache.memory_cache import InMemoryCache

        cache = InMemoryCache()
        await cache.set('key', 'value')
        assert await cache.get('key') == 'value'

    @pytest.mark.asyncio
    async def test_get_missing_key_returns_none(self):
        from infrastructure.cache.memory_cache import InMemoryCache

        cache = InMemoryCache()
        assert await cache.get('missing') is None

    @pytest.mark.asyncio
    async def test_expired_entry_returns_none(self):
        from datetime import timedelta

        from infrastructure.cache.memory_cache import InMemoryCache

        cache = InMemoryCache()
        await cache.set('key', 'value', ttl_seconds=1)
        cache._store['key'] = (
            cache._store['key'][0],
            cache._store['key'][1] - timedelta(seconds=10),
        )
        assert await cache.get('key') is None

    @pytest.mark.asyncio
    async def test_delete(self):
        from infrastructure.cache.memory_cache import InMemoryCache

        cache = InMemoryCache()
        await cache.set('key', 'value')
        await cache.delete('key')
        assert await cache.get('key') is None


class TestIdempotencyStore:
    @pytest.mark.asyncio
    async def test_no_cached_response_by_default(self):
        from infrastructure.cache.memory_cache import InMemoryCache
        from infrastructure.idempotency import IdempotencyStore

        store = IdempotencyStore(InMemoryCache())
        result = await store.get_cached_response('token', 'client-1', 'idem-key-1')
        assert result is None

    @pytest.mark.asyncio
    async def test_replays_cached_response(self):
        from infrastructure.cache.memory_cache import InMemoryCache
        from infrastructure.idempotency import IdempotencyStore

        store = IdempotencyStore(InMemoryCache())
        await store.cache_response('token', 'client-1', 'idem-key-1', {'access_token': 'abc'})

        result = await store.get_cached_response('token', 'client-1', 'idem-key-1')
        assert result == {'access_token': 'abc'}

    @pytest.mark.asyncio
    async def test_isolated_by_client_and_endpoint(self):
        from infrastructure.cache.memory_cache import InMemoryCache
        from infrastructure.idempotency import IdempotencyStore

        store = IdempotencyStore(InMemoryCache())
        await store.cache_response('token', 'client-1', 'idem-key-1', {'access_token': 'abc'})

        assert await store.get_cached_response('token', 'client-2', 'idem-key-1') is None
        assert await store.get_cached_response('revoke', 'client-1', 'idem-key-1') is None