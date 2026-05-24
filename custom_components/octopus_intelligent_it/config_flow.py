"""Config flow for the Octopus Intelligent (Italia) integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_ACCOUNT_NUMBER,
    CONF_GRAPHQL_URL,
    CONF_REFRESH_EXPIRES_AT,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL,
    DEFAULT_GRAPHQL_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .kraken_client import KrakenAuthError, KrakenClient, KrakenError
from .queries import GET_ACCOUNT_LIST

_LOGGER = logging.getLogger(__name__)

_STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required("email"): str,
        vol.Required("password"): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Optional("graphql_url", default=DEFAULT_GRAPHQL_URL): str,
    }
)


class OctopusIntelligentItConfigFlow(
    config_entries.ConfigFlow, domain=DOMAIN
):
    """Handle the config flow for Octopus Intelligent (Italia)."""

    VERSION = 1

    def __init__(self) -> None:
        self._long_lived_token: str = ""
        self._refresh_expires_at: int = 0
        self._graphql_url: str = DEFAULT_GRAPHQL_URL
        self._accounts: list[dict[str, str]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial user step (email + password)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            email: str = user_input["email"]
            password: str = user_input["password"]
            self._graphql_url = user_input.get("graphql_url", DEFAULT_GRAPHQL_URL)

            session = aiohttp_client.async_get_clientsession(self.hass)
            try:
                long_lived, expires_at = await KrakenClient.login_with_credentials(
                    session, self._graphql_url, email, password
                )
            except KrakenAuthError:
                errors["base"] = "invalid_auth"
            except KrakenError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Octopus IT login")
                errors["base"] = "unknown"
            else:
                self._long_lived_token = long_lived
                self._refresh_expires_at = expires_at

                # Fetch account list
                try:
                    client = KrakenClient(
                        session, self._graphql_url, long_lived, expires_at
                    )
                    data = await client.graphql(
                        GET_ACCOUNT_LIST, operation_name="GetAccountList"
                    )
                    accounts = data.get("viewer", {}).get("accounts", [])
                except KrakenAuthError:
                    errors["base"] = "invalid_auth"
                except KrakenError:
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected error fetching account list")
                    errors["base"] = "unknown"
                else:
                    if len(accounts) == 0:
                        errors["base"] = "no_accounts"
                    elif len(accounts) == 1:
                        account_number: str = accounts[0]["number"]
                        await self.async_set_unique_id(account_number)
                        self._abort_if_unique_id_configured()
                        return self.async_create_entry(
                            title=f"Octopus {account_number}",
                            data={
                                CONF_REFRESH_TOKEN: self._long_lived_token,
                                CONF_REFRESH_EXPIRES_AT: self._refresh_expires_at,
                                CONF_ACCOUNT_NUMBER: account_number,
                                CONF_GRAPHQL_URL: self._graphql_url,
                            },
                        )
                    else:
                        self._accounts = accounts
                        return await self.async_step_account()

        return self.async_show_form(
            step_id="user",
            data_schema=_STEP_USER_SCHEMA,
            errors=errors,
        )

    async def async_step_account(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the account selection step (when multiple accounts exist)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            account_number = user_input[CONF_ACCOUNT_NUMBER]
            await self.async_set_unique_id(account_number)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Octopus {account_number}",
                data={
                    CONF_REFRESH_TOKEN: self._long_lived_token,
                    CONF_REFRESH_EXPIRES_AT: self._refresh_expires_at,
                    CONF_ACCOUNT_NUMBER: account_number,
                    CONF_GRAPHQL_URL: self._graphql_url,
                },
            )

        account_options = {a["number"]: a["number"] for a in self._accounts}
        schema = vol.Schema(
            {vol.Required(CONF_ACCOUNT_NUMBER): vol.In(account_options)}
        )
        return self.async_show_form(
            step_id="account",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Handle re-authentication (e.g. expired refresh token)."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the re-auth confirmation step."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            email: str = user_input["email"]
            password: str = user_input["password"]
            graphql_url: str = reauth_entry.data.get(
                CONF_GRAPHQL_URL, DEFAULT_GRAPHQL_URL
            )

            session = aiohttp_client.async_get_clientsession(self.hass)
            try:
                long_lived, expires_at = await KrakenClient.login_with_credentials(
                    session, graphql_url, email, password
                )
            except KrakenAuthError:
                errors["base"] = "invalid_auth"
            except KrakenError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Octopus IT re-auth")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={
                        CONF_REFRESH_TOKEN: long_lived,
                        CONF_REFRESH_EXPIRES_AT: expires_at,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required("email"): str,
                vol.Required("password"): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
            }
        )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OctopusOptionsFlowHandler:
        """Return the options flow handler."""
        return OctopusOptionsFlowHandler()


class OctopusOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for the Octopus Intelligent (Italia) integration."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the options step."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        schema = vol.Schema(
            {
                vol.Optional(CONF_SCAN_INTERVAL, default=current_interval): vol.All(
                    int, vol.Range(min=60, max=3600)
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
