"""Async client for the Octopus Kraken Italia GraphQL API."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any

import jwt

from .queries import (
    LOGIN,
    OBTAIN_LONG_LIVED_REFRESH_TOKEN,
)

_LOGGER = logging.getLogger(__name__)

# Kraken error codes
_AUTH_ERROR_CODES = {"KT-CT-1135", "KT-CT-1134"}
_TOKEN_EXPIRED_CODE = "KT-CT-1124"


class KrakenError(Exception):
    """Base exception for Kraken API errors."""


class KrakenAuthError(KrakenError):
    """Raised when authentication fails (invalid or expired credentials)."""


class KrakenAPIError(KrakenError):
    """Raised when the API returns application-level errors."""

    def __init__(self, errors: list[dict[str, Any]]) -> None:
        self.errors = errors
        codes = [e.get("extensions", {}).get("errorCode", "") for e in errors]
        super().__init__(f"Kraken API errors: {errors} (codes: {codes})")


class KrakenClient:
    """Async GraphQL client for the Octopus Kraken Italia API.

    Manages short-lived access tokens transparently, refreshing them
    automatically using a long-lived refresh token (~6 months). Notifies
    the caller when the refresh token itself rotates so the new value can
    be persisted.
    """

    def __init__(
        self,
        session: Any,  # aiohttp.ClientSession
        graphql_url: str,
        refresh_token: str,
        refresh_expires_at: int | None = None,
        on_refresh_token_change: Callable[[str, int], None] | None = None,
    ) -> None:
        self._session = session
        self._graphql_url = graphql_url
        self._refresh_token = refresh_token
        self._refresh_exp = refresh_expires_at
        self._on_refresh_change = on_refresh_token_change

        self._access_token: str | None = None
        self._access_exp: int = 0
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _graphql_raw(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        operation_name: str | None = None,
        *,
        auth: bool = True,
    ) -> dict[str, Any]:
        """Execute a raw GraphQL request and return the full JSON response."""
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "ha-octopus-intelligent-it/0.1.0",
        }
        if auth and self._access_token:
            # Kraken uses the raw JWT without a "Bearer " prefix
            headers["Authorization"] = self._access_token

        payload: dict[str, Any] = {"query": query}
        if variables is not None:
            payload["variables"] = variables
        if operation_name is not None:
            payload["operationName"] = operation_name

        _LOGGER.debug(
            "[graphql_raw] op=%s url=%s auth=%s",
            operation_name,
            self._graphql_url,
            auth,
        )

        try:
            async with self._session.post(
                self._graphql_url,
                json=payload,
                headers=headers,
            ) as resp:
                _LOGGER.debug(
                    "[graphql_raw] op=%s HTTP status=%s", operation_name, resp.status
                )
                if resp.status == 401:
                    raise KrakenAuthError("HTTP 401 Unauthorized")
                resp.raise_for_status()
                body = await resp.json()
        except (KrakenAuthError, KrakenAPIError):
            raise
        except Exception as exc:
            _LOGGER.debug(
                "[graphql_raw] op=%s exception: %s: %s",
                operation_name,
                type(exc).__name__,
                exc,
            )
            raise

        if body.get("errors"):
            _LOGGER.debug(
                "[graphql_raw] op=%s GraphQL errors: %s", operation_name, body["errors"]
            )
        else:
            _LOGGER.debug(
                "[graphql_raw] op=%s success, data keys: %s",
                operation_name,
                list((body.get("data") or {}).keys()),
            )

        return body

    async def _refresh(self) -> None:
        """Obtain a new short-lived access token using the refresh token.

        If the API returns a rotated refresh token, the stored value is
        updated and the on_refresh_token_change callback is invoked.
        """
        _LOGGER.debug("[refresh] Refreshing access token using refresh token")
        try:
            response = await self._graphql_raw(
                LOGIN,
                variables={"input": {"refreshToken": self._refresh_token}},
                operation_name="Login",
                auth=False,
            )
        except KrakenAuthError:
            raise
        except Exception as exc:
            _LOGGER.debug("[refresh] Network error: %s: %s", type(exc).__name__, exc)
            raise KrakenError(f"Network error during token refresh: {exc}") from exc

        errors = response.get("errors", [])
        if errors:
            codes = {e.get("extensions", {}).get("errorCode", "") for e in errors}
            if codes & _AUTH_ERROR_CODES:
                raise KrakenAuthError(f"Auth error during refresh: {errors}")
            raise KrakenAPIError(errors)

        data = response.get("data", {}).get("obtainKrakenToken", {})
        new_access_token: str = data["token"]
        new_refresh_token: str | None = data.get("refreshToken")
        new_refresh_exp: int | None = data.get("refreshExpiresIn")

        # Decode access token expiry (no signature verification needed)
        try:
            claims = jwt.decode(
                new_access_token,
                options={"verify_signature": False},
                algorithms=["RS256"],
            )
            self._access_exp = int(claims.get("exp", 0))
            _LOGGER.debug("[refresh] Access token decoded, exp=%s", self._access_exp)
        except Exception as exc:
            _LOGGER.debug("Could not decode JWT expiry, using 1-hour fallback: %s", exc)
            self._access_exp = int(time.time()) + 3600

        self._access_token = new_access_token
        _LOGGER.debug("[refresh] Access token obtained successfully")

        # Persist rotated refresh token
        if new_refresh_token and new_refresh_token != self._refresh_token:
            _LOGGER.debug("[refresh] Refresh token rotated, persisting new value")
            self._refresh_token = new_refresh_token
            if new_refresh_exp is not None:
                self._refresh_exp = new_refresh_exp
            if self._on_refresh_change is not None:
                self._on_refresh_change(new_refresh_token, self._refresh_exp or 0)

    async def _ensure_token(self) -> None:
        """Ensure a valid access token is available, refreshing if needed."""
        now = int(time.time())
        if self._access_token is not None and self._access_exp - now >= 60:
            _LOGGER.debug(
                "[ensure_token] Token still valid for %ss", self._access_exp - now
            )
            return
        async with self._lock:
            # Re-check inside the lock (another coroutine may have refreshed)
            now = int(time.time())
            if self._access_token is not None and self._access_exp - now >= 60:
                return
            _LOGGER.debug("[ensure_token] Token missing or expiring, refreshing...")
            await self._refresh()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def graphql(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        operation_name: str | None = None,
    ) -> dict[str, Any]:
        """Execute an authenticated GraphQL request.

        Automatically refreshes the access token when needed. Retries once
        on token-expired errors (KT-CT-1124 / HTTP 401).

        Returns:
            The ``data`` field of the GraphQL response.

        Raises:
            KrakenAuthError: When credentials are invalid/expired.
            KrakenAPIError: When the API returns application errors.
            KrakenError: On network or unexpected failures.
        """
        _LOGGER.debug("[graphql] op=%s starting", operation_name)
        await self._ensure_token()

        for attempt in range(2):
            try:
                response = await self._graphql_raw(
                    query,
                    variables=variables,
                    operation_name=operation_name,
                    auth=True,
                )
            except KrakenAuthError:
                if attempt == 0:
                    _LOGGER.debug(
                        "[graphql] op=%s auth error on attempt 0, refreshing token",
                        operation_name,
                    )
                    self._access_token = None
                    await self._ensure_token()
                    continue
                raise

            errors = response.get("errors", [])
            if errors:
                codes = {e.get("extensions", {}).get("errorCode", "") for e in errors}
                if _TOKEN_EXPIRED_CODE in codes and attempt == 0:
                    _LOGGER.debug(
                        "[graphql] op=%s token expired (KT-CT-1124), refreshing",
                        operation_name,
                    )
                    self._access_token = None
                    await self._ensure_token()
                    continue
                if codes & _AUTH_ERROR_CODES:
                    raise KrakenAuthError(f"Auth error: {errors}")
                raise KrakenAPIError(errors)

            _LOGGER.debug("[graphql] op=%s completed successfully", operation_name)
            return response.get("data", {})

        raise KrakenError("Failed after retry")  # should not reach here

    # ------------------------------------------------------------------
    # Config-flow helper (class method — does not instantiate a client)
    # ------------------------------------------------------------------

    @classmethod
    async def login_with_credentials(
        cls,
        session: Any,
        graphql_url: str,
        email: str,
        password: str,
    ) -> tuple[str, int]:
        """Authenticate with email/password and return a long-lived refresh token.

        This method is intended for use in the config flow only. It:
        1. Obtains a short-lived access token via email/password login.
        2. Exchanges it for a long-lived refresh token (~6 months).

        Returns:
            A tuple of (long_lived_refresh_token, refresh_expires_at_unix_ts).

        Raises:
            KrakenAuthError: On invalid credentials.
            KrakenAPIError: On API errors.
            KrakenError: On network errors.
        """
        _LOGGER.debug(
            "[login] Step 1: email/password login → url=%s email=%s", graphql_url, email
        )

        # Step 1: email/password login → short-lived access token
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "ha-octopus-intelligent-it/0.1.0",
        }
        payload = {
            "query": LOGIN,
            "variables": {"input": {"email": email, "password": password}},
            "operationName": "Login",
        }
        try:
            async with session.post(graphql_url, json=payload, headers=headers) as resp:
                _LOGGER.debug("[login] Step 1 HTTP status=%s", resp.status)
                resp.raise_for_status()
                data = await resp.json()
        except (KrakenAuthError, KrakenAPIError):
            raise
        except Exception as exc:
            _LOGGER.debug(
                "[login] Step 1 network error: %s: %s", type(exc).__name__, exc
            )
            raise KrakenError(f"Network error during login: {exc}") from exc

        errors = data.get("errors", [])
        if errors:
            _LOGGER.debug("[login] Step 1 GraphQL errors: %s", errors)
            codes = {e.get("extensions", {}).get("errorCode", "") for e in errors}
            if codes & _AUTH_ERROR_CODES:
                raise KrakenAuthError(f"Invalid credentials: {errors}")
            raise KrakenAPIError(errors)

        access_token: str = data["data"]["obtainKrakenToken"]["token"]
        _LOGGER.debug("[login] Step 1 success, obtained short-lived access token")

        # Step 2: obtain long-lived refresh token
        _LOGGER.debug(
            "[login] Step 2: exchanging access token for long-lived refresh token"
        )
        payload2 = {
            "query": OBTAIN_LONG_LIVED_REFRESH_TOKEN,
            "variables": {"input": {"krakenToken": access_token}},
            "operationName": "generateLongLivedRefreshToken",
        }
        try:
            async with session.post(
                graphql_url, json=payload2, headers=headers
            ) as resp2:
                _LOGGER.debug("[login] Step 2 HTTP status=%s", resp2.status)
                resp2.raise_for_status()
                data2 = await resp2.json()
        except (KrakenAuthError, KrakenAPIError):
            raise
        except Exception as exc:
            _LOGGER.debug(
                "[login] Step 2 network error: %s: %s", type(exc).__name__, exc
            )
            raise KrakenError(
                f"Network error obtaining long-lived token: {exc}"
            ) from exc

        errors2 = data2.get("errors", [])
        if errors2:
            _LOGGER.debug("[login] Step 2 GraphQL errors: %s", errors2)
            raise KrakenAPIError(errors2)

        token_data = data2["data"]["obtainLongLivedRefreshToken"]
        long_lived_token: str = token_data["refreshToken"]
        expires_at: int = int(token_data["refreshExpiresIn"])

        _LOGGER.debug(
            "[login] Step 2 success, long-lived token obtained (expires_at=%s)",
            expires_at,
        )
        return long_lived_token, expires_at
